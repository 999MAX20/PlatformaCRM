"""Bounded ClamD INSTREAM adapter. No file paths or third-party SaaS uploads."""
from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import re
import socket
import struct
import time

from django.conf import settings


class ScanUnavailable(Exception):
    def __init__(self, code="scanner_unavailable"):
        self.code = code
        super().__init__(code)


@dataclass(frozen=True)
class ScanResult:
    clean: bool
    sha256: str
    size: int
    engine: str


def _timeout(sock, deadline):
    remaining = deadline - time.monotonic()
    if remaining <= 0:
        raise ScanUnavailable("scan_timeout")
    sock.settimeout(remaining)


def _reply(sock, deadline):
    data = bytearray()
    while len(data) <= 4096:
        _timeout(sock, deadline)
        chunk = sock.recv(1024)
        if not chunk:
            raise ScanUnavailable("invalid_scanner_response")
        data.extend(chunk)
        if len(data) > 4096:
            raise ScanUnavailable("invalid_scanner_response")
        if b"\0" in data:
            if not data.endswith(b"\0") or data.count(b"\0") != 1:
                raise ScanUnavailable("invalid_scanner_response")
            return data[:-1].decode("ascii", errors="strict")
    raise ScanUnavailable("invalid_scanner_response")


def _connect(deadline):
    # Host is operator configuration only, never an upload/request argument.
    return socket.create_connection(
        (settings.CLAMD_HOST, settings.CLAMD_PORT),
        timeout=max(.1, deadline - time.monotonic()),
    )


def scanner_health():
    """Loaded database age, not merely a TCP/PING success. Run daemon with TZ=UTC."""
    deadline = time.monotonic() + settings.FILE_SCAN_TIMEOUT_SECONDS
    try:
        with _connect(deadline) as sock:
            _timeout(sock, deadline)
            sock.sendall(b"zVERSION\0")
            version = _reply(sock, deadline)
        match = re.fullmatch(r"ClamAV ([0-9.]+)/([0-9]+)/(.+)", version)
        if not match:
            raise ScanUnavailable("invalid_scanner_version")
        stamp = datetime.strptime(match[3], "%a %b %d %H:%M:%S %Y").replace(tzinfo=timezone.utc)
        age = (datetime.now(timezone.utc) - stamp).total_seconds()
        if age < -3600 or age > settings.FILE_SCAN_SIGNATURE_MAX_AGE_HOURS * 3600:
            raise ScanUnavailable("scanner_signatures_stale")
        return f"ClamAV {match[1]}/{match[2]}"
    except ScanUnavailable:
        raise
    except (OSError, ValueError, UnicodeError):
        raise ScanUnavailable() from None


def scan_stream(stream):
    engine = scanner_health()
    deadline = time.monotonic() + settings.FILE_SCAN_TIMEOUT_SECONDS
    digest = hashlib.sha256()
    size = 0
    try:
        with _connect(deadline) as sock:
            _timeout(sock, deadline)
            sock.sendall(b"zINSTREAM\0")
            while chunk := stream.read(64 * 1024):
                size += len(chunk)
                if size > settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024:
                    raise ScanUnavailable("scan_size_limit")
                digest.update(chunk)
                _timeout(sock, deadline)
                sock.sendall(struct.pack("!I", len(chunk)) + chunk)
            if not size:
                raise ScanUnavailable("scan_empty_file")
            _timeout(sock, deadline)
            sock.sendall(struct.pack("!I", 0))
            verdict = _reply(sock, deadline)
        if verdict == "stream: OK":
            return ScanResult(True, digest.hexdigest(), size, engine)
        if re.fullmatch(r"stream: [^\r\n\x00]+ FOUND", verdict):
            # Do not expose arbitrary scanner text or signature names in merchant logs.
            return ScanResult(False, digest.hexdigest(), size, engine)
        raise ScanUnavailable("scan_incomplete")
    except ScanUnavailable:
        raise
    except (OSError, ValueError, UnicodeError):
        raise ScanUnavailable() from None
