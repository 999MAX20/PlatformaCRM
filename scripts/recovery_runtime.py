"""Owned, disposable PostgreSQL/Redis processes for the S04 recovery drill."""
from contextlib import contextmanager
import base64
import json
import os
from pathlib import Path
import secrets
import shutil
import socket
import subprocess
import sys
import time

from scripts.codex_verify import ROOT, isolated_runtime

HIDDEN = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0


def free_port():
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def stop_process(process):
    if process is None or process.poll() is not None:
        return
    if os.name == "nt":
        # The venv launcher can own a child Python process on Windows. Stop
        # exactly this Popen tree, never discover/terminate unrelated workers.
        subprocess.run(["taskkill", "/PID", str(process.pid), "/T", "/F"],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, creationflags=HIDDEN, check=False)
    else:
        process.terminate()
    try:
        process.wait(timeout=10)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=10)


class RecoveryRuntime:
    def __init__(self, directory, environment, pg_bin, redis_server, logs):
        self.directory = directory
        self.env = environment
        self.pg_bin = pg_bin
        self.redis_server = redis_server
        self.logs = logs
        self.pg_port = free_port()
        self.redis_port = free_port()
        self.redis = None
        self.pg_started = False
        self.env.update({
            "DATABASE_URL": f"postgresql://codex_s04@127.0.0.1:{self.pg_port}/s04_source",
            "REDIS_URL": f"redis://127.0.0.1:{self.redis_port}/0",
            "CELERY_TASK_ALWAYS_EAGER": "False", "AUTOMATIONS_RUN_INLINE": "False",
            "OUTBOUND_MESSAGES_RUN_INLINE": "False", "AI_ENABLED": "False",
            "CONNECTOR_CREDENTIAL_KEYS": json.dumps({"s04": base64.urlsafe_b64encode(secrets.token_bytes(32)).decode()}),
            "CONNECTOR_CREDENTIAL_ACTIVE_KEY_ID": "s04",
            "DJANGO_SETTINGS_MODULE": "config.settings", "S04_DIRECTORY": str(directory),
            "ALLOWED_HOSTS": "localhost,127.0.0.1,testserver", "LOG_LEVEL": "WARNING",
            "EXPORT_SYNC_MAX_ROWS": "1", "PYTHONUNBUFFERED": "1", "TZ": "UTC",
            "PYTHONIOENCODING": "utf-8", "LC_ALL": "C",
        })

    def pg(self, name):
        return str(self.pg_bin / (name + (".exe" if os.name == "nt" else "")))

    def run(self, args, *, env=None, timeout=120):
        process = subprocess.Popen(args, cwd=ROOT, env=env or self.env, stdout=self.logs,
                                   stderr=subprocess.STDOUT, creationflags=HIDDEN)
        try:
            code = process.wait(timeout=timeout)
        except BaseException:
            stop_process(process)
            raise
        if code:
            raise subprocess.CalledProcessError(code, args)

    def start(self):
        (self.directory / "s04-runtime.json").write_text(json.dumps({
            "pg_port": self.pg_port, "redis_port": self.redis_port,
        }), encoding="utf-8")
        self.run([self.pg("initdb"), "-D", str(self.directory / "pg"), "-U", "codex_s04",
                  "-A", "trust", "--encoding=UTF8", "--locale=C"])
        self.run([self.pg("pg_ctl"), "-D", str(self.directory / "pg"), "-l", str(self.directory / "pg.log"),
                  "-o", f"-h 127.0.0.1 -p {self.pg_port}", "-w", "start"])
        self.pg_started = True
        for database in ("s04_source", "s04_restored"):
            self.run([self.pg("createdb"), "-h", "127.0.0.1", "-p", str(self.pg_port), "-U", "codex_s04", database])
        self.start_redis()
        self.run([sys.executable, "manage.py", "migrate", "--noinput", "--verbosity", "0"])

    def start_redis(self):
        self.redis = subprocess.Popen([
            str(self.redis_server), "--bind", "127.0.0.1", "--port", str(self.redis_port),
            "--protected-mode", "yes", "--save", "", "--appendonly", "no",
            "--dir", str(self.directory),
        ], cwd=self.redis_server.parent, env=self.env, stdout=self.logs, stderr=subprocess.STDOUT, creationflags=HIDDEN)
        import redis
        self.broker = redis.Redis(host="127.0.0.1", port=self.redis_port, socket_timeout=1)
        deadline = time.monotonic() + 20
        while True:
            try:
                if self.broker.ping():
                    break
            except redis.ConnectionError:
                pass
            if self.redis.poll() is not None or time.monotonic() >= deadline:
                raise RuntimeError("Owned Redis did not become ready")
            time.sleep(.2)

    def lose_broker_queue(self):
        # Deliberate loss of this isolated Redis queue; durable DB work must
        # recover through the existing beat/due-processing path.
        self.broker.shutdown(nosave=True)
        self.redis.wait(timeout=10)
        self.start_redis()

    def restore_backup(self):
        backup = self.directory / "backup"
        backup.mkdir()
        self.run([self.pg("pg_dump"), "-h", "127.0.0.1", "-p", str(self.pg_port), "-U", "codex_s04",
                  "--format=custom", "--no-owner", "-f", str(backup / "database.dump"), "s04_source"])
        for name in ("media", "private"):
            source = self.directory / name
            source.mkdir(exist_ok=True)
            shutil.copytree(source, backup / name)
            shutil.copytree(backup / name, self.directory / f"restored-{name}")
        # Synthetic key only; no working keyring or provider secrets are read.
        (backup / "keys.json").write_text(self.env["CONNECTOR_CREDENTIAL_KEYS"], encoding="utf-8")
        self.run([self.pg("pg_restore"), "-h", "127.0.0.1", "-p", str(self.pg_port), "-U", "codex_s04",
                  "--exit-on-error", "--no-owner", "-d", "s04_restored", str(backup / "database.dump")])
        restored_env = {**self.env,
            "DATABASE_URL": f"postgresql://codex_s04@127.0.0.1:{self.pg_port}/s04_restored",
            "MEDIA_ROOT": str(self.directory / "restored-media"),
            "PRIVATE_MEDIA_ROOT": str(self.directory / "restored-private"),
            "CONNECTOR_CREDENTIAL_KEYS": (backup / "keys.json").read_text(encoding="utf-8"),
        }
        self.run([sys.executable, "scripts/verify_recovery_s04.py", "--restored"], env=restored_env)

    def close(self):
        if self.redis is not None and self.redis.poll() is None:
            try:
                self.broker.shutdown(nosave=True)
                self.redis.wait(timeout=10)
            except Exception:
                stop_process(self.redis)
        if self.pg_started:
            self.run([self.pg("pg_ctl"), "-D", str(self.directory / "pg"), "-m", "fast", "-w", "stop"])


@contextmanager
def recovery_runtime(*, pg_bin, redis_server, logs):
    # No database URL input: callers cannot accidentally select a working DB.
    with isolated_runtime(python=sys.executable) as isolated:
        runtime = RecoveryRuntime(isolated.database_path.parent, dict(isolated.environment), pg_bin, redis_server, logs)
        try:
            runtime.start()
            yield runtime
        finally:
            runtime.close()
