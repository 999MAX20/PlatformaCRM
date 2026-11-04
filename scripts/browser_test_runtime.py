"""Prepare browser fixtures only inside the existing disposable gate runtime."""
import base64
import ipaddress
import json
import os
from pathlib import Path
import secrets
import socket
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.codex_verify import safe_environment


def browser_environment(environment):
    message = "Browser setup requires an explicit disposable isolated_runtime; no setup performed."
    url = environment.get("DATABASE_URL", "")
    if environment.get("ZANI_QUALITY_GATE") != "1" or not url.startswith("sqlite:///"):
        raise RuntimeError(message)
    raw = Path(url.removeprefix("sqlite:///"))
    database = raw.resolve()
    if (not raw.is_absolute() or raw != database or database.name != "gate.sqlite3"
            or not database.parent.name.startswith("zani-quality-gate-")
            or database.parent.parent != Path(tempfile.gettempdir()).resolve()
            or not database.parent.is_dir()):
        raise RuntimeError(message)
    ports = []
    for name in ("E2E_DJANGO_PORT", "E2E_FRONTEND_PORT"):
        value = environment.get(name, "")
        if not value.isdecimal() or not 1024 <= int(value) <= 65535 or int(value) in {8000, 5173}:
            raise RuntimeError(message)
        ports.append(int(value))
    if ports[0] == ports[1] or any(environment.get(key) != f"http://127.0.0.1:{port}" for key, port in
            zip(("E2E_API_BASE_URL", "E2E_BASE_URL"), ports)):
        raise RuntimeError(message)
    safe = safe_environment(database_path=database, python=sys.executable,
                            django_port=ports[0], frontend_port=ports[1], base=environment)
    for name in ("E2E_PASSWORD", "E2E_BUSINESS_SLUG", "E2E_BUSINESS_NAME", "E2E_BILLING_COMMERCE"):
        if name in environment:
            safe[name] = environment[name]
    key_path = database.parent / "browser-connector-key"
    try:
        with key_path.open("x", encoding="ascii") as stream:
            stream.write(base64.urlsafe_b64encode(secrets.token_bytes(32)).decode("ascii"))
    except FileExistsError:
        pass
    if key_path.resolve().parent != database.parent:
        raise RuntimeError(message)
    safe["CONNECTOR_CREDENTIAL_KEYS"] = json.dumps({"browser-test": key_path.read_text(encoding="ascii")})
    safe["CONNECTOR_CREDENTIAL_ACTIVE_KEY_ID"] = "browser-test"
    safe["DJANGO_SETTINGS_MODULE"] = "config.settings"
    return safe


def configure_browser_runtime():
    safe = browser_environment(dict(os.environ))
    os.environ.clear()
    os.environ.update(safe)
    import environ
    environ.Env.read_env = classmethod(lambda *args, **kwargs: None)
    original_connect = socket.socket.connect
    original_connect_ex = socket.socket.connect_ex

    def local_address(address):
        if isinstance(address, tuple):
            host = address[0]
            if host == "localhost":
                return
            try:
                if ipaddress.ip_address(host).is_loopback:
                    return
            except ValueError:
                pass
        raise RuntimeError("External network is disabled in the browser test runtime")

    def connect(sock, address):
        local_address(address)
        return original_connect(sock, address)

    def connect_ex(sock, address):
        local_address(address)
        return original_connect_ex(sock, address)

    socket.socket.connect = connect
    socket.socket.connect_ex = connect_ex


def prepare():
    configure_browser_runtime()
    import django
    django.setup()
    from django.core.management import call_command
    call_command("migrate", interactive=False)
    call_command("prepare_e2e_smoke_data", password=os.environ["E2E_PASSWORD"],
                 business_slug=os.environ["E2E_BUSINESS_SLUG"], business_name=os.environ["E2E_BUSINESS_NAME"])


if __name__ == "__main__":
    if sys.argv[1:] != ["prepare"]:
        raise SystemExit("Expected mode: prepare")
    prepare()
