from io import BytesIO
import ipaddress
import time
from urllib.parse import urlsplit

from PIL import Image


MAX_LOGO_BYTES = 2 * 1024 * 1024
LOGO_TIMEOUT = 8


class DocumentLogoUnavailable(Exception):
    pass


def normalize_document_logo(source):
    try:
        if not isinstance(source, bytes) or not 0 < len(source) <= MAX_LOGO_BYTES:
            raise ValueError
        with Image.open(BytesIO(source)) as image:
            if image.format not in {"PNG", "JPEG"} or image.width * image.height > 4_000_000:
                raise ValueError
            image.load()
            rgba = image.convert("RGBA")
            clean = Image.new("RGB", rgba.size, "white")
            clean.paste(rgba, mask=rgba.getchannel("A"))
            output = BytesIO()
            clean.save(output, format="PNG")
            result = output.getvalue()
            if len(result) > MAX_LOGO_BYTES:
                raise ValueError
            return result
    except Exception:
        raise DocumentLogoUnavailable() from None


def capture_document_logo(url):
    """Fetch only the saved clinic logo; never send medical data or follow redirects."""
    if url == "":
        return None
    connection = None
    try:
        if not isinstance(url, str) or len(url) > 2048 or any(ord(char) <= 32 or ord(char) == 127 for char in url):
            raise ValueError
        parsed = urlsplit(url)
        if parsed.scheme != "https" or parsed.port not in (None, 443):
            raise ValueError
        from apps.integrations.webhooks import _PinnedHTTPSConnection, _resolve_outbound_webhook_url

        deadline = time.monotonic() + LOGO_TIMEOUT
        _, parsed, addresses = _resolve_outbound_webhook_url(url, allow_mock=False)
        if any(not ipaddress.ip_address(address).is_global for address in addresses):
            raise ValueError
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise TimeoutError
        connection = _PinnedHTTPSConnection(parsed.hostname, 443, addresses[0], timeout=remaining)
        target = parsed.path or "/"
        if parsed.query:
            target += "?" + parsed.query
        connection.request("GET", target, headers={"Accept": "image/png, image/jpeg", "Accept-Encoding": "identity"})
        response = connection.getresponse()
        if response.status != 200 or response.getheader("Content-Encoding", "identity").lower() != "identity":
            raise ValueError
        if response.getheader("Content-Type", "").split(";", 1)[0].strip().lower() not in {"image/png", "image/jpeg"}:
            raise ValueError
        length = response.getheader("Content-Length")
        if length is not None and not 0 < int(length) <= MAX_LOGO_BYTES:
            raise ValueError
        output = BytesIO()
        while output.tell() <= MAX_LOGO_BYTES:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise TimeoutError
            if connection.sock is not None:
                connection.sock.settimeout(remaining)
            chunk = response.read1(min(65536, MAX_LOGO_BYTES + 1 - output.tell()))
            if not chunk:
                break
            output.write(chunk)
        source = output.getvalue()
        if length is not None and len(source) != int(length):
            raise ValueError
        return normalize_document_logo(source)
    except Exception:
        # Provider errors may contain signed URLs; the domain receives an opaque failure.
        raise DocumentLogoUnavailable() from None
    finally:
        if connection is not None:
            try:
                connection.close()
            except Exception:
                pass
