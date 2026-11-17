"""Preflight the complete authenticated envelope before processing its events."""
from copy import deepcopy

from django.db import transaction
from rest_framework.exceptions import ValidationError

from apps.integrations.whatsapp_routing import verified_whatsapp_routes
from apps.integrations.whatsapp.account_updates import prepare_account_update, record_account_updates


def _validate_envelope(payload):
    if not isinstance(payload, dict):
        raise ValidationError("WhatsApp payload must be an object.")
    if "entry" not in payload:
        return
    if not isinstance(payload["entry"], list) or not payload["entry"]:
        raise ValidationError("WhatsApp entries must be a nonempty list.")
    for entry in payload["entry"]:
        if not isinstance(entry, dict) or not isinstance(entry.get("changes"), list) or not entry["changes"]:
            raise ValidationError("WhatsApp changes must be a nonempty list.")
        for change in entry["changes"]:
            value = change.get("value") if isinstance(change, dict) else None
            if not isinstance(value, dict) or not isinstance(value.get("metadata", {}), dict):
                raise ValidationError("WhatsApp change value or metadata is invalid.")
            for name in ("messages", "statuses", "contacts"):
                items = value.get(name, [])
                if not isinstance(items, list) or any(not isinstance(item, dict) for item in items):
                    raise ValidationError(f"WhatsApp {name} must be a list of objects.")


@transaction.atomic
def process_whatsapp_webhook(payload, auth_context, headers=None):
    from apps.integrations.whatsapp import (
        _process_whatsapp_status_batch, _save_parsed_inbound_message, parse_inbound_message,
    )

    _validate_envelope(payload)
    account_updates = []
    message_payload = payload
    if payload.get("entry"):
        entries = []
        for entry in payload["entry"]:
            changes = []
            for change in entry["changes"]:
                if change.get("field") == "account_update":
                    if change["value"].get("messages") or change["value"].get("statuses"):
                        raise ValidationError("Account updates cannot contain message events.")
                    account_updates.append(prepare_account_update(entry, change["value"], auth_context))
                else:
                    changes.append(change)
            if changes:
                entries.append({**entry, "changes": changes})
        message_payload = {**payload, "entry": entries}
    routes = verified_whatsapp_routes(message_payload, auth_context) if not account_updates or message_payload.get("entry") else []
    incoming = []
    for channel, value, portion in routes:
        if not payload.get("entry"):
            incoming.append((channel, portion, parse_inbound_message(portion, headers)))
            continue
        for item in value.get("messages") or []:
            if not isinstance(item, dict) or not isinstance(item.get("id"), str) or not item["id"]:
                raise ValidationError("WhatsApp message id is missing.")
            single = deepcopy(portion)
            single_value = single["entry"][0]["changes"][0]["value"]
            single_value.pop("statuses", None)
            single_value["messages"] = [item]
            single_value["contacts"] = [contact for contact in value.get("contacts") or [] if contact.get("wa_id") == item.get("from")]
            try:
                parsed = parse_inbound_message(single, headers)
            except (AttributeError, TypeError):
                raise ValidationError("WhatsApp message content is invalid.")
            incoming.append((channel, single, parsed))

    result = {"processed": 0, "statuses": 0, "messages": []}
    for channel, value, portion in routes:
        statuses = value.get("statuses") or []
        if statuses:
            result["processed"] += _process_whatsapp_status_batch(channel, statuses, portion)
            result["statuses"] += len(statuses)
    for channel, single, parsed in incoming:
        conversation, message = _save_parsed_inbound_message(channel, single, parsed)
        result["messages"].append({"conversation_id": conversation.id, "message_id": message.id})
    if account_updates:
        record_account_updates(account_updates)
        result["account_updates"] = len(account_updates)
    if len(result["messages"]) == 1:
        result.update(result["messages"][0])
    return result
