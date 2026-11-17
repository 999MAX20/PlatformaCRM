"""Meta onboarding calls; no connector is activated by this module."""

import json
from datetime import datetime, timezone as datetime_timezone
from urllib import parse, request as urllib_request
from urllib.error import URLError

from django.conf import settings
from django.utils import timezone

from apps.core.production_rules import is_safe_public_https_url


def graph_url(edge, params=None):
    base = str(settings.WHATSAPP_GRAPH_BASE_URL or "").strip().rstrip("/")
    if not is_safe_public_https_url(base):
        raise ValueError("WHATSAPP_GRAPH_BASE_URL must be a public HTTPS URL.")
    version = settings.WHATSAPP_GRAPH_API_VERSION.strip("/")
    return f"{base}/{version}/{edge}?{parse.urlencode(params or {})}"


def graph_call(edge, token, *, params=None, body=None):
    request = urllib_request.Request(
        graph_url(edge, params),
        data=json.dumps(body).encode() if body is not None else None,
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        method="POST" if body is not None else "GET",
    )
    try:
        with urllib_request.urlopen(request, timeout=15) as response:
            payload = json.loads(response.read().decode("utf-8"))
        if not isinstance(payload, dict) or payload.get("error"):
            raise ValueError("Invalid Meta response.")
        return payload
    except (URLError, OSError, ValueError, TypeError) as exc:
        raise ValueError("Meta onboarding could not be verified. Restart setup.") from exc


def validate_signup_assets(token, phone_id, waba_id):
    debug = graph_call("debug_token", f"{settings.META_APP_ID}|{settings.META_APP_SECRET}", params={"input_token": token}).get("data")
    required = {"whatsapp_business_management", "whatsapp_business_messaging"}
    if not isinstance(debug, dict) or debug.get("is_valid") is not True or str(debug.get("app_id")) != str(settings.META_APP_ID):
        raise ValueError("Meta token is not valid for this app.")
    scopes = debug.get("scopes")
    if not isinstance(scopes, list) or not all(isinstance(scope, str) for scope in scopes) or not required.issubset(set(scopes)):
        raise ValueError("Meta token lacks WhatsApp permissions.")
    expiries = []
    for field in ("expires_at", "data_access_expires_at"):
        value = debug.get(field, 0)
        if type(value) is not int or value < 0:
            raise ValueError("Invalid Meta token expiry.")
        if value:
            try:
                expiry = datetime.fromtimestamp(value, tz=datetime_timezone.utc)
            except (OverflowError, OSError, ValueError) as exc:
                raise ValueError("Invalid Meta token expiry.") from exc
            if expiry <= timezone.now():
                raise ValueError("Meta token has expired.")
            expiries.append(expiry)
    granular_scopes = debug.get("granular_scopes") or []
    if not isinstance(granular_scopes, list) or not all(isinstance(scope, dict) for scope in granular_scopes):
        raise ValueError("Invalid Meta permission metadata.")
    for scope in granular_scopes:
        if scope.get("scope") in required and "target_ids" in scope and (
            not isinstance(scope["target_ids"], list) or waba_id not in scope["target_ids"]
        ):
            raise ValueError("Meta token does not grant access to this WhatsApp account.")

    # Follow only Graph cursors, never a provider-supplied absolute next URL.
    cursor = None
    seen = set()
    for _ in range(100):
        params = {"fields": "id,display_phone_number,platform_type", "limit": 100}
        if cursor:
            params["after"] = cursor
        page = graph_call(f"{parse.quote(waba_id, safe='')}/phone_numbers", token, params=params)
        phones = page.get("data")
        if not isinstance(phones, list):
            break
        for phone in phones:
            if isinstance(phone, dict) and str(phone.get("id")) == phone_id and phone.get("display_phone_number"):
                if phone.get("platform_type") not in (None, "NOT_APPLICABLE", "CLOUD_API"):
                    raise ValueError("This number requires a separate migration flow.")
                return phone, min(expiries) if expiries else None
        paging = page.get("paging") or {}
        cursor = (paging.get("cursors") or {}).get("after") if paging.get("next") else None
        if not cursor or cursor in seen:
            break
        seen.add(cursor)
    raise ValueError("The selected number does not belong to the WhatsApp account.")


def activate_signup_number(token, phone_id, waba_id, pin):
    for edge, body in (
        (f"{parse.quote(waba_id, safe='')}/subscribed_apps", {}),
        (f"{parse.quote(phone_id, safe='')}/register", {"messaging_product": "whatsapp", "pin": pin}),
    ):
        if graph_call(edge, token, body=body).get("success") is not True:
            raise ValueError("Meta did not confirm WhatsApp activation.")
