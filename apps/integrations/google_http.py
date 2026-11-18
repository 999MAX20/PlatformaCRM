import json
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import HTTPRedirectHandler, Request, build_opener

from apps.core.domain_errors import TemporaryServiceFailure


class GoogleError(TemporaryServiceFailure):
    status_code = 503
    default_detail = "Google is unavailable. Retry or reconnect your account."
    default_code = "google_unavailable"

    def __init__(self, *, revoked=False, status=None):
        self.revoked = revoked
        self.remote_status = status
        super().__init__()


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def google_request(url, *, method="GET", token=None, payload=None, form=False):
    headers = {"Accept": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    data = None
    if payload is not None:
        data = (urlencode(payload) if form else json.dumps(payload)).encode("utf-8")
        headers["Content-Type"] = "application/x-www-form-urlencoded" if form else "application/json"
    try:
        with build_opener(NoRedirect).open(Request(url, data=data, headers=headers, method=method), timeout=20) as response:
            raw = response.read(8 * 1024 * 1024 + 1)
        if len(raw) > 8 * 1024 * 1024:
            raise GoogleError()
        result = json.loads(raw) if raw else {}
        if not isinstance(result, dict):
            raise GoogleError()
        return result
    except HTTPError as exc:
        try:
            body = json.loads(exc.read(4096))
        except (ValueError, OSError):
            body = {}
        if not isinstance(body, dict):
            body = {}
        raise GoogleError(revoked=exc.code == 401 or body.get("error") == "invalid_grant", status=exc.code) from None
    except (URLError, OSError, ValueError):
        raise GoogleError() from None
