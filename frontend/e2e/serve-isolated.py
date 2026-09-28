"""Disposable browser backend with an explicit fake ClamD, never a production mode."""
from datetime import datetime, timezone
import os
from pathlib import Path
import socketserver
import struct
import sys
import threading
import time
import tempfile

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
database = os.environ.get("DATABASE_URL", "")
assert os.environ.get("ZANI_QUALITY_GATE") == "1"
assert "zani-quality-gate-" in database and database.endswith("gate.sqlite3")
assert database.startswith("sqlite:///")
database_path = Path(database.removeprefix("sqlite:///")).resolve()
assert database_path.is_relative_to(Path(tempfile.gettempdir()).resolve())
assert database_path.parent.name.startswith("zani-quality-gate-")


def receive(sock, length):
    result = b""
    while len(result) < length:
        chunk = sock.recv(length - len(result))
        if not chunk:
            raise EOFError()
        result += chunk
    return result


class FakeClamd(socketserver.BaseRequestHandler):
    def handle(self):
        self.request.settimeout(10)
        command = b""
        while not command.endswith(b"\0"):
            command += receive(self.request, 1)
        if command == b"zVERSION\0":
            stamp = datetime.now(timezone.utc).strftime("%a %b %d %H:%M:%S %Y")
            self.request.sendall(f"ClamAV 1.5.4/1/{stamp}\0".encode("ascii"))
            return
        assert command == b"zINSTREAM\0"
        content = bytearray()
        while size := struct.unpack("!I", receive(self.request, 4))[0]:
            assert len(content) + size <= 10 * 1024 * 1024
            content.extend(receive(self.request, size))
        # Harmless markers exclusively in disposable E2E fixture data.
        if b"E2E_SCAN_DELAY" in content:
            time.sleep(3)
        if b"E2E_SCAN_ERROR" in content:
            reply = b"stream: fixture unavailable ERROR\0"
        elif b"E2E_SCAN_BLOCK" in content:
            reply = b"stream: Test.Fixture FOUND\0"
        else:
            reply = b"stream: OK\0"
        self.request.sendall(reply)


scanner = socketserver.ThreadingTCPServer(("127.0.0.1", 0), FakeClamd)
scanner.daemon_threads = True
os.environ["CLAMD_HOST"] = "127.0.0.1"
os.environ["CLAMD_PORT"] = str(scanner.server_address[1])
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
import django
django.setup()
from django.core.management import call_command
from django.db import close_old_connections, OperationalError
from apps.core.file_scanning import scan_due_attachments

stop = threading.Event()
def worker():
    while not stop.wait(1):
        close_old_connections()
        try:
            scan_due_attachments(10)
        except OperationalError:
            # SQLite write contention: the durable lease will be retried.
            pass
        finally:
            close_old_connections()

threading.Thread(target=scanner.serve_forever, daemon=True).start()
threading.Thread(target=worker, daemon=True).start()
try:
    call_command("runserver", f"127.0.0.1:{os.environ['E2E_DJANGO_PORT']}", use_reloader=False)
finally:
    stop.set()
    scanner.shutdown()
    scanner.server_close()
