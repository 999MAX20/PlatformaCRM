"""Focused YCloud checks; never loads the working DB or provider credentials."""
import subprocess
import sys
import argparse
import os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts.codex_verify import isolated_runtime, find_available_port


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--postgres-bin", type=Path)
    parser.add_argument("labels", nargs="*")
    options = parser.parse_args()
    labels = options.labels or ["apps.integrations.tests_ycloud", "apps.integrations.tests_ycloud_dispatch"]
    with isolated_runtime(python=sys.executable) as runtime:
        pg_started = False
        pg_data = runtime.database_path.parent / "postgres"
        hidden = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
        def pg(name, *args):
            executable = options.postgres_bin / (name + (".exe" if os.name == "nt" else ""))
            subprocess.run([str(executable), *args], env=runtime.environment, check=True, creationflags=hidden)
        try:
            if options.postgres_bin:
                port = str(find_available_port((5432, 8000, 5173)))
                pg("initdb", "-D", str(pg_data), "-U", "codex_ycloud", "-A", "trust", "--encoding=UTF8", "--locale=C")
                pg("pg_ctl", "-D", str(pg_data), "-l", str(pg_data.parent / "postgres.log"), "-o", f"-h 127.0.0.1 -p {port}", "-w", "start")
                pg_started = True
                pg("createdb", "-h", "127.0.0.1", "-p", port, "-U", "codex_ycloud", "ycloud")
                runtime.environment["DATABASE_URL"] = f"postgresql://codex_ycloud@127.0.0.1:{port}/ycloud"
            for args in [("check",), ("makemigrations", "--check", "--dry-run"), ("test", *labels, "-v", "1")]:
                subprocess.run([sys.executable, "manage.py", *args], env=runtime.environment, check=True)
        finally:
            if pg_started:
                pg("pg_ctl", "-D", str(pg_data), "-m", "fast", "-w", "stop")


if __name__ == "__main__":
    main()
