"""Run authenticated CRM HTTP load on disposable local PostgreSQL copies."""
import argparse
import ctypes
import hashlib
import json
import os
from pathlib import Path
import statistics
import subprocess
import sys
import threading
import time
from urllib.parse import quote
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.codex_verify import isolated_runtime, find_available_port
from scripts.local_postgres import profile, STATE


class Memory(ctypes.Structure):
    _fields_ = [("length", ctypes.c_ulong), ("load", ctypes.c_ulong)] + [(name, ctypes.c_ulonglong) for name in
        ("total", "available", "total_page", "available_page", "total_virtual", "available_virtual", "extended")]


class Resources:
    def __init__(self):
        self.rows = []
        self.done = threading.Event()

    def sample(self):
        last = None
        while not self.done.is_set():
            mem = Memory(); mem.length = ctypes.sizeof(mem)
            ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(mem))
            idle, kernel, user = (ctypes.c_ulonglong() for _ in range(3))
            ctypes.windll.kernel32.GetSystemTimes(ctypes.byref(idle), ctypes.byref(kernel), ctypes.byref(user))
            current = (idle.value, kernel.value + user.value)
            cpu = None if last is None else 100 * (1 - (current[0] - last[0]) / max(1, current[1] - last[1]))
            self.rows.append({"available_mb": mem.available / 1048576, "cpu_percent": cpu})
            last = current
            self.done.wait(1)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dump", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--dataset", choices=["small", "large"], required=True)
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--diagnostic", action="store_true", help="Profile read APIs in-process instead of HTTP load")
    args = parser.parse_args()
    identity = profile()
    secrets = json.loads((STATE / "credentials.json").read_text())
    out = args.output.resolve(); out.mkdir(parents=True, exist_ok=True)
    database = "crm_bench_" + args.dataset
    import psycopg
    from psycopg import sql
    admin = dict(host="127.0.0.1", port=identity["port"], user="crm_local_admin", password=secrets["admin_password"], dbname="postgres")
    app = dict(host="127.0.0.1", port=identity["port"], user="crm_app", password=secrets["app_password"], dbname=database)
    hidden = subprocess.CREATE_NO_WINDOW
    processes = []
    handles = []
    created = False
    with isolated_runtime(python=sys.executable) as runtime:
        environment = runtime.environment
        redis_port = find_available_port((6379, 8000, 5173, identity["port"]))
        environment.update(DATABASE_URL=f"postgresql://crm_app:{quote(secrets['app_password'], safe='')}@127.0.0.1:{identity['port']}/{database}",
            CRM_LOAD_DISPOSABLE="1", DB_CONN_MAX_AGE="0", AI_ENABLED="False", LOG_LEVEL="WARNING",
            DJANGO_SETTINGS_MODULE="config.settings", PYTHONIOENCODING="utf-8", PYTHONUNBUFFERED="1",
            REDIS_URL=f"redis://127.0.0.1:{redis_port}/0", DJANGO_CACHE_URL=f"redis://127.0.0.1:{redis_port}/1",
            CELERY_TASK_ALWAYS_EAGER="False", AUTOMATIONS_RUN_INLINE="False", OUTBOUND_MESSAGES_RUN_INLINE="False")
        try:
            with psycopg.connect(**admin, autocommit=True) as connection:
                connection.execute(sql.SQL("CREATE DATABASE {} OWNER crm_app TEMPLATE template0").format(sql.Identifier(database)))
                created = True
            pg_env = {**environment, "PGPASSWORD": secrets["app_password"]}
            with (out / "prepare.log").open("wb") as log:
                subprocess.run([str(Path(identity["bin"]) / "pg_restore.exe"), "-h", "127.0.0.1", "-p", str(identity["port"]),
                    "-U", "crm_app", "-d", database, "--no-owner", "--exit-on-error", str(args.dump.resolve())],
                    env=pg_env, stdout=log, stderr=subprocess.STDOUT, creationflags=hidden, check=True)
            def launch(command, name, cwd=ROOT):
                log = (out / name).open("ab"); handles.append(log)
                process = subprocess.Popen(command, cwd=cwd, env=environment, stdout=log, stderr=subprocess.STDOUT, creationflags=hidden)
                processes.append(process)
                return process
            redis_bin = ROOT / "output/crm-s04-20261014/deps/redis/Redis-7.4.9-Windows-x64-msys2/redis-server.exe"
            launch([str(redis_bin), "--bind", "127.0.0.1", "--port", str(redis_port), "--save", "", "--appendonly", "no", "--dir", str(runtime.database_path.parent)], "redis.log", redis_bin.parent)
            import redis
            broker = redis.Redis(host="127.0.0.1", port=redis_port, socket_timeout=2)
            for _ in range(30):
                try:
                    if broker.ping(): break
                except redis.RedisError: time.sleep(1)
            else: raise RuntimeError("Dedicated Redis not ready")
            with (out / "fixture.log").open("wb") as log:
                subprocess.run([sys.executable, "scripts/crm_load_fixture.py", "25" if args.dataset == "small" else "10000", str(out / "subjects.json")],
                    env=environment, stdout=log, stderr=subprocess.STDOUT, check=True)
            config = json.loads((out / "subjects.json").read_text())
            config["base"] = f"http://127.0.0.1:{runtime.django_port}"
            (out / "subjects.json").write_text(json.dumps(config), encoding="utf-8")
            if args.diagnostic:
                with (out / "diagnostic.log").open("wb") as log:
                    subprocess.run([sys.executable, "scripts/crm_profile.py", str(out / "subjects.json"), str(out)],
                                   env=environment, stdout=log, stderr=subprocess.STDOUT, check=True)
                return
            launch([sys.executable, "-m", "celery", "-A", "config", "worker", "--pool=solo", "--concurrency=1",
                "--queues=default,notifications,automations", "--hostname=crm-load@%h", "--without-gossip", "--without-mingle", "--loglevel=WARNING"], "worker.log")
            server = launch([sys.executable, "-m", "uvicorn", "config.asgi:application", "--host", "127.0.0.1", "--port", str(runtime.django_port),
                "--workers", str(args.workers), "--no-access-log", "--log-level", "warning"], "api.log")
            for _ in range(90):
                if server.poll() is not None: raise RuntimeError("Benchmark API exited")
                try:
                    if urlopen(config["base"] + "/health/", timeout=2).status == 200: break
                except Exception: time.sleep(1)
            else: raise RuntimeError("Benchmark API not ready")
            source_paths = sorted([*ROOT.glob("apps/**/*.py"), *ROOT.glob("config/**/*.py"),
                                   ROOT / "scripts/benchmark_crm.py", ROOT / "scripts/crm_load.mjs",
                                   ROOT / "scripts/crm_load_fixture.py"])
            source_hashes = {path.relative_to(ROOT).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
                             for path in source_paths}
            (out / "source-hashes.json").write_text(json.dumps(source_hashes, indent=2), encoding="utf-8")
            results = []
            def stage(users, duration, think, label):
                monitor = Resources(); thread = threading.Thread(target=monitor.sample, daemon=True); thread.start()
                path = out / f"{label}.json"
                with psycopg.connect(**app, autocommit=True) as db:
                    before = db.execute("SELECT count(*) FROM tasks_task").fetchone()[0]
                try:
                    subprocess.run(["node", "scripts/crm_load.mjs", str(out / "subjects.json"), str(users), str(duration), str(think), str(path)],
                        stdout=subprocess.DEVNULL, env=environment, check=True, timeout=duration + 90)
                finally:
                    monitor.done.set(); thread.join(3)
                result = json.loads(path.read_text())
                with psycopg.connect(**app, autocommit=True) as db:
                    after = db.execute("SELECT count(*) FROM tasks_task").fetchone()[0]
                writes = result["endpoints"].get("task-create", {}).get("statuses", {}).get("201", 0)
                result.update(label=label, committed_tasks=after-before, successful_task_requests=writes,
                    write_count_matches=after-before == writes,
                    available_memory_min_mb=min(r["available_mb"] for r in monitor.rows),
                    cpu_mean_percent=statistics.mean(r["cpu_percent"] for r in monitor.rows if r["cpu_percent"] is not None),
                    queue_lengths={name: broker.llen(name) for name in ("default", "notifications", "automations")})
                path.write_text(json.dumps(result, indent=2), encoding="utf-8")
                (out / f"{label}-resources.json").write_text(json.dumps(monitor.rows), encoding="utf-8")
                print(json.dumps({k: result[k] for k in ("label", "users", "rps", "p95", "errorPercent", "pass", "write_count_matches", "available_memory_min_mb")}), flush=True)
                results.append(result)
                return result
            warmup = stage(2, 15, 0, "warmup")
            if warmup["errors"]: raise RuntimeError("Warmup API errors; inspect per-endpoint status before measuring")
            failures = 0; passed_users = []
            for users in (1, 5, 10, 20, 40, 80, 160):
                result = stage(users, 60, 1, f"users-{users}")
                if result["pass"]: passed_users.append(users); failures = 0
                else: failures += 1
                if failures >= 2: break
            sustained_users = None
            for users in reversed(passed_users):
                if stage(users, 180, 1, f"sustained-{users}")["pass"]:
                    sustained_users = users
                    break
            failures = 0; passed_inflight = []
            for users in (1, 4, 8, 16, 32):
                result = stage(users, 60, 0, f"inflight-{users}")
                if result["pass"]: passed_inflight.append(users)
                failures = 0 if result["pass"] else failures + 1
                if failures >= 2: break
            sustained_inflight = None
            for users in reversed(passed_inflight):
                if stage(users, 180, 0, f"sustained-inflight-{users}")["pass"]:
                    sustained_inflight = users
                    break
            summary = {"dataset": args.dataset, "counts": config["counts"], "api_workers": args.workers, "db_conn_max_age": 0,
                "postgres_max_connections": 100, "results": results,
                "sustained_users": sustained_users, "sustained_inflight": sustained_inflight,
                "source_drift": [name for name, sha in source_hashes.items()
                                 if not (ROOT / name).is_file() or hashlib.sha256((ROOT / name).read_bytes()).hexdigest() != sha]}
            (out / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
        finally:
            for process in reversed(processes):
                if process.poll() is None:
                    subprocess.run(["taskkill", "/PID", str(process.pid), "/T", "/F"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, creationflags=hidden)
                    process.wait(timeout=20)
            for log in handles: log.close()
            if created:
                with psycopg.connect(**admin, autocommit=True) as connection:
                    connection.execute("SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname=%s AND pid<>pg_backend_pid()", (database,))
                    connection.execute(sql.SQL("DROP DATABASE {}").format(sql.Identifier(database)))


if __name__ == "__main__":
    main()
