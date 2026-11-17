import hashlib
import json

from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied, ValidationError

from apps.integrations.models import WhatsAppCoexistenceEvent, WhatsAppCoexistenceSync
from apps.integrations.whatsapp.coexistence_messages import import_message, phone_digits, prepare_message


FIELDS = {"history", "smb_app_state_sync", "smb_message_echoes"}


def prepare_event(channel, portion, auth_context):
    if auth_context.mode != "meta":
        raise PermissionDenied("Business App events require a Meta signature.")
    entry = portion["entry"][0]
    change = entry["changes"][0]
    config = channel.config_json or {}
    if config.get("onboarding_mode") != "coexistence" or str(entry.get("id")) != str(config.get("business_account_id")):
        raise PermissionDenied("Business App event does not match this connection.")
    sync = WhatsAppCoexistenceSync.objects.filter(channel=channel, setup_revision=config.get("setup_revision")).first()
    if sync is None:
        raise ValidationError("Business App synchronization is not initialized.")
    return sync, change["field"], change["value"]


def enqueue_event(sync, field, value):
    from apps.integrations.tasks import process_whatsapp_coexistence_event

    digest = hashlib.sha256(json.dumps([field, value], sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    event, _ = WhatsAppCoexistenceEvent.objects.get_or_create(sync=sync, digest=digest, defaults={"field": field, "payload": value})
    if event.status != "processed":
        transaction.on_commit(lambda: process_whatsapp_coexistence_event.delay(event.pk))
    return event


def _list(value, key):
    result = value.get(key, [])
    if not isinstance(result, list) or any(not isinstance(item, dict) for item in result):
        raise ValidationError(f"Invalid Business App {key}.")
    return result


@transaction.atomic
def process_event(event_id):
    from apps.integrations.channel_boundary import lock_channel_for_setup

    event = WhatsAppCoexistenceEvent.objects.select_related("sync__channel__bot").get(pk=event_id)
    channel = lock_channel_for_setup(event.sync.channel)
    event = WhatsAppCoexistenceEvent.objects.select_for_update().get(pk=event_id)
    if event.status == "processed":
        return
    sync = WhatsAppCoexistenceSync.objects.select_for_update().get(pk=event.sync_id)
    config = channel.config_json or {}
    if config.get("setup_revision") != sync.setup_revision or config.get("onboarding_mode") != "coexistence" or channel.status != "active":
        event.status, event.error_code = "obsolete", "connection_changed"
        event.save(update_fields=["status", "error_code"])
        return
    business_phone = phone_digits(config.get("display_phone_number"))
    value = event.payload
    waiting_for_history = False
    if event.field == "smb_message_echoes":
        items = [prepare_message(item, business_phone=business_phone) for item in _list(value, "message_echoes")]
        for item in items:
            import_message(channel, item)
    elif event.field == "history":
        for part in _list(value, "history"):
            if any(error.get("code") == 2593109 for error in _list(part, "errors")):
                sync.state = "declined"
                continue
            metadata = part.get("metadata", {})
            progress = metadata.get("progress", 0) if isinstance(metadata, dict) else None
            if type(progress) is not int or not 0 <= progress <= 100:
                raise ValidationError("Invalid Business App synchronization progress.")
            for thread in _list(part, "threads"):
                for data in _list(thread, "messages"):
                    import_message(channel, prepare_message(data, business_phone=business_phone, recipient=thread.get("id"), history=True))
            sync.progress = max(sync.progress, progress)
            sync.state = "importing"
        # Media metadata is delivered separately under history, never as a new inbound.
        for data in _list(value, "messages"):
            from apps.bots.models import BotMessage
            existing = BotMessage.objects.filter(conversation__business_id=channel.bot.business_id,
                conversation__bot_id=channel.bot_id, conversation__channel="whatsapp",
                external_message_id=data.get("id"), payload_json__source="whatsapp_history").select_related("conversation").first()
            if existing:
                import_message(channel, prepare_message(data, business_phone=business_phone,
                    recipient=existing.conversation.external_user_id, history=True))
            else:
                waiting_for_history = True
        sync.save(update_fields=["progress", "state"])
        if value.get("history"):
            from apps.integrations.tasks import process_whatsapp_coexistence_event
            for pending_id in sync.events.filter(status="awaiting_history").values_list("pk", flat=True):
                transaction.on_commit(lambda pk=pending_id: process_whatsapp_coexistence_event.delay(pk))
    elif event.field == "smb_app_state_sync":
        from apps.bots.models import BotConversation
        for item in _list(value, "state_sync"):
            contact = item.get("contact")
            if item.get("type") != "contact" or not isinstance(contact, dict):
                raise ValidationError("Invalid Business App contact.")
            recipient = phone_digits(contact.get("phone_number"))
            if not recipient:
                raise ValidationError("Business App contact has no supported phone identity.")
            # Address book names only; never delete CRM clients or create sales leads.
            conversation, _ = BotConversation.objects.get_or_create(business_id=channel.bot.business_id,
                bot_id=channel.bot_id, channel="whatsapp", external_user_id=recipient, defaults={"bot_enabled": False})
            metadata = dict(conversation.metadata_json or {})
            if item.get("action") == "remove":
                metadata.pop("whatsapp_contact_name", None)
            elif item.get("action") == "add" and isinstance(contact.get("full_name", ""), str):
                metadata["whatsapp_contact_name"] = contact.get("full_name", "")[:255]
            else:
                raise ValidationError("Invalid Business App contact action.")
            conversation.metadata_json = metadata
            conversation.save(update_fields=["metadata_json"])
    event.status, event.error_code, event.processed_at = ("awaiting_history", "", None) if waiting_for_history else ("processed", "", timezone.now())
    event.save(update_fields=["status", "error_code", "processed_at"])
