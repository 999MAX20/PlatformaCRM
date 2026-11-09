"""Start and validate the dedicated local CRM PostgreSQL cluster."""
import json
import os
from pathlib import Path
import subprocess


ROOT = Path(__file__).resolve().parents[1]
STATE = ROOT / "output" / "local-postgres"


def profile():
    try:
        value = json.loads((STATE / "identity.json").read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise RuntimeError("Dedicated local PostgreSQL profile is missing or invalid") from exc
    if value.get("database") != "platformacrm" or value.get("user") != "crm_app":
        raise RuntimeError("Unexpected local PostgreSQL identity")
    if not isinstance(value.get("port"), int) or not 1024 <= value["port"] <= 65535:
        raise RuntimeError("Invalid local PostgreSQL port")
    return value


def validate_database(database):
    identity = profile()
    expected = ("django.db.backends.postgresql", "127.0.0.1", str(identity["port"]), "platformacrm", "crm_app")
    actual = tuple(str(database.get(k, "")) for k in ("ENGINE", "HOST", "PORT", "NAME", "USER"))
    if actual != expected:
        raise RuntimeError("Database does not match the dedicated local PostgreSQL profile")
    return identity


def ensure_running(database):
    identity = validate_database(database)
    data = STATE / "data"
    if not (data / "PG_VERSION").is_file():
        raise RuntimeError("Local PostgreSQL data directory is missing; initialization is explicit")
    executable = Path(identity["bin"]) / "pg_ctl.exe"
    flags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
    args = [str(executable), "-D", str(data)]
    status = subprocess.run(args + ["status"], capture_output=True, creationflags=flags, timeout=15)
    if status.returncode == 0:
        lines = (data / "postmaster.pid").read_text().splitlines()
        if Path(lines[1]).resolve() != data.resolve() or int(lines[3]) != identity["port"]:
            raise RuntimeError("Running PostgreSQL does not match its local profile")
        return
    if status.returncode != 3:
        raise RuntimeError("Cannot inspect the dedicated PostgreSQL cluster")
    with (STATE / "startup.log").open("ab") as log:
        result = subprocess.run(args + ["-l", str(STATE / "postgres.log"), "-w", "-t", "45", "start"],
                                stdout=log, stderr=subprocess.STDOUT, creationflags=flags, timeout=55)
    if result.returncode:
        raise RuntimeError("Local PostgreSQL startup failed; see output/local-postgres/startup.log")


if __name__ == "__main__":
    import sys
    sys.path.insert(0, str(ROOT))
    os.chdir(ROOT)
    os.environ["DJANGO_SETTINGS_MODULE"] = "config.settings"
    from django.conf import settings
    if settings.ENVIRONMENT not in {"local", "development"}:
        raise RuntimeError("Local PostgreSQL startup requires local/development")
    ensure_running(settings.DATABASES["default"])
