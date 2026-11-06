"""Run JWT maintenance only against this checkout's existing local SQLite DB."""
import os
from pathlib import Path
import sys
from datetime import datetime, timezone


ROOT = Path(__file__).resolve().parents[1]


def check_local_database(database, environment):
    if environment not in {"local", "development"}:
        raise RuntimeError("Token maintenance requires a local/development environment")
    if database["ENGINE"] != "django.db.backends.sqlite3":
        raise RuntimeError("Local token maintenance requires SQLite")
    path = Path(database["NAME"])
    if not path.is_absolute():
        path = ROOT / path
    if path.resolve() != (ROOT / "db.sqlite3").resolve() or not path.is_file():
        raise RuntimeError("Local token maintenance requires the existing checkout db.sqlite3")


def main():
    os.chdir(ROOT)
    sys.path.insert(0, str(ROOT))
    os.environ["DJANGO_SETTINGS_MODULE"] = "config.settings"
    from django.conf import settings

    check_local_database(settings.DATABASES["default"], settings.ENVIRONMENT)
    import django
    django.setup()
    from apps.accounts.tasks import flush_expired_tokens

    flush_expired_tokens()


if __name__ == "__main__":
    log = ROOT / "output" / "local-db-maintenance" / "tokens.log"
    log.parent.mkdir(parents=True, exist_ok=True)
    try:
        main()
    except Exception as exc:
        with log.open("a", encoding="utf-8") as stream:
            stream.write(f"{datetime.now(timezone.utc).isoformat()} FAILED {type(exc).__name__}\n")
        raise
    else:
        with log.open("a", encoding="utf-8") as stream:
            stream.write(f"{datetime.now(timezone.utc).isoformat()} OK expired-token cleanup\n")
