"""Bounded server-only API client. Disabled unless explicitly configured."""
import json
from urllib import request, error, parse

from django.conf import settings


class YCloudError(Exception):
    def __init__(self, code="provider_unavailable", *, retryable=False, ambiguous=False, retry_after=0):
        self.code = code
        self.retryable = retryable
        self.ambiguous = ambiguous
        self.retry_after = retry_after
        super().__init__(code)


def configured():
    return bool(settings.YCLOUD_ENABLED and settings.YCLOUD_API_KEY and settings.YCLOUD_WEBHOOK_SECRET)


class NoRedirect(request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def call(method, path, body=None):
    if not configured():
        raise YCloudError("setup_required")
    # Fixed origin: API keys must never follow redirects or merchant-provided URLs.
    req = request.Request(
        "https://api.ycloud.com/v2" + path,
        data=json.dumps(body).encode() if body is not None else None,
        headers={"X-API-Key": settings.YCLOUD_API_KEY, "Content-Type": "application/json"},
        method=method,
    )
    try:
        with request.build_opener(NoRedirect).open(req, timeout=15) as response:
            raw = response.read(1024 * 1024 + 1)
        if len(raw) > 1024 * 1024:
            raise ValueError("oversized response")
        result = json.loads(raw)
        if not isinstance(result, dict):
            raise ValueError("invalid response")
        return result
    except error.HTTPError as exc:
        retry_after = str(exc.headers.get("Retry-After", "0"))
        raise YCloudError(
            "rate_limited" if exc.code == 429 else "provider_rejected",
            retryable=exc.code == 429 or (method == "GET" and exc.code >= 500),
            ambiguous=method == "POST" and exc.code >= 500,
            retry_after=int(retry_after) if retry_after.isdigit() else 0,
        ) from None
    except (error.URLError, OSError, ValueError):
        raise YCloudError("provider_unavailable", retryable=method == "GET", ambiguous=method == "POST") from None


def create_link(customer_id):
    result = call("POST", "/partner/embeddedSignup/links", {
        "partnerCustomerId": str(customer_id), "onboardingType": "WHATSAPP_BUSINESS_PLATFORM", "locale": "ru_RU",
    })
    url = parse.urlsplit(str(result.get("onboardingUrl", "")))
    if url.scheme != "https" or url.netloc != "connect.ycloud.com" or url.path != "/open/whatsapp/onboard":
        raise YCloudError("invalid_provider_response")
    return result


def connected_number(waba_id):
    result = call("GET", "/whatsapp/phoneNumbers?" + parse.urlencode({"filter.wabaId": waba_id, "limit": 100}))
    # Stage one intentionally supports exactly one number per connection.
    items = result.get("items", [])
    if not isinstance(items, list) or len(items) != 1 or not isinstance(items[0], dict) or items[0].get("wabaId") != waba_id:
        raise YCloudError("number_selection_required")
    number = items[0]
    if number.get("status") != "CONNECTED" or not number.get("id") or not number.get("phoneNumber"):
        raise YCloudError("number_not_ready", retryable=True)
    return number
