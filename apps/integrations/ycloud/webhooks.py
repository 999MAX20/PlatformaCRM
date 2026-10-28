"""Authenticated durable intake. Provider data never chooses a CRM Business directly."""
import hashlib
import hmac
import json
import re
from uuid import UUID

from django.conf import settings
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied, ValidationError

from apps.core.domain_errors import TemporaryServiceFailure
from apps.integrations.ycloud import client
from apps.integrations.ycloud.models import YCloudConnection, YCloudEvent


KINDS = {
    "whatsapp.business_account.updated": "whatsappBusinessAccount",
    "whatsapp.inbound_message.received": "whatsappInboundMessage",
    "whatsapp.message.updated": "whatsappMessage",
}


class MessageRouteNotReady(TemporaryServiceFailure):
    default_detail = "Message route is not ready. Retry delivery later."
    error_code = "message_route_not_ready"
    default_code = error_code
    retry_after_seconds = 30


def authenticate(body, header):
    if not client.configured() or len(body) > 1024 * 1024:
        raise PermissionDenied("Webhook unavailable.")
    fields = [part.strip().split("=", 1) for part in str(header).split(",")]
    timestamps = [value for pair in fields if len(pair) == 2 for key, value in [pair] if key == "t"]
    signatures = [value for pair in fields if len(pair) == 2 for key, value in [pair] if key == "s"]
    if len(timestamps) != 1 or not re.fullmatch(r"[0-9]{1,12}", timestamps[0]):
        raise PermissionDenied("Invalid signature.")
    timestamp = timestamps[0]
    if abs(timezone.now().timestamp() - int(timestamp)) > 300:
        raise PermissionDenied("Expired signature.")
    expected = hmac.new(settings.YCLOUD_WEBHOOK_SECRET.encode(), timestamp.encode() + b"." + body, hashlib.sha256).hexdigest()
    if not any(re.fullmatch(r"[a-fA-F0-9]{64}", value) and hmac.compare_digest(expected, value.lower()) for value in signatures):
        raise PermissionDenied("Invalid signature.")


def accept(body, header):
    authenticate(body, header)
    try:
        payload = json.loads(body)
    except (ValueError, UnicodeError):
        raise ValidationError("Invalid event.") from None
    if not isinstance(payload, dict):
        raise ValidationError("Invalid event.")
    event_id, kind = payload.get("id"), payload.get("type")
    if not isinstance(event_id, str) or not 0 < len(event_id) <= 255 or not isinstance(kind, str) or len(kind) > 80:
        raise ValidationError("Invalid event identity.")
    key = KINDS.get(kind)
    if key is None:
        return None
    data = payload.get(key)
    if not isinstance(data, dict):
        raise ValidationError("Invalid event object.")
    if kind == "whatsapp.business_account.updated":
        try:
            customer_id = UUID(str(data.get("partnerCustomerId", "")))
        except ValueError:
            return None  # Another partner customer, not a route into this CRM.
        connection = YCloudConnection.objects.filter(customer_id=customer_id).first()
    else:
        number = data.get("to") if kind == "whatsapp.inbound_message.received" else data.get("from")
        if not isinstance(number, str) or not number or not isinstance(data.get("wabaId"), str) or not data["wabaId"]:
            raise ValidationError("Invalid message route.")
        connection = YCloudConnection.objects.filter(waba_id=data["wabaId"], phone_number=number, status="connected").first()
    if connection is None:
        if kind != "whatsapp.business_account.updated":
            # Binding and message callbacks can arrive out of order. A 2xx here
            # would permanently discard a legitimate message before setup commits.
            raise MessageRouteNotReady()
        return None
    fields = ({"id", "partnerCustomerId", "updateEvent", "paymentMethodAttached"}
        if kind == "whatsapp.business_account.updated" else
        {"id", "wamid", "wabaId", "from", "to", "type", "text", "customerProfile", "sendTime",
         "status", "updateTime", "deliverTime", "readTime", "externalId", "errorCode"})
    from apps.integrations.sanitization import sanitize_config
    data = sanitize_config({name: value for name, value in data.items() if name in fields})
    # Whitelist the provider object: do not retain arbitrary top-level secrets/headers.
    event, _ = YCloudEvent.objects.get_or_create(external_id=event_id, defaults={
        "connection": connection, "kind": kind, "payload": {key: data}, "next_attempt_at": timezone.now(),
    })
    if event.connection_id != connection.pk or event.kind != kind:
        raise ValidationError("Event identity conflict.")
    return event
