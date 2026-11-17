from urllib.parse import quote

from django.db import transaction
from django.utils import timezone

from apps.integrations.models import WhatsAppCoexistenceSync
from apps.integrations.whatsapp.signup_graph import graph_call
from apps.integrations.whatsapp_credentials import get_whatsapp_access_token


def start_sync(sync_id):
    for kind, request_field in (("smb_app_state_sync", "contacts_request_id"), ("history", "history_request_id")):
        with transaction.atomic():
            from apps.integrations.channel_boundary import lock_channel_for_setup
            original = WhatsAppCoexistenceSync.objects.select_related("channel__bot").get(pk=sync_id)
            channel = lock_channel_for_setup(original.channel)
            sync = WhatsAppCoexistenceSync.objects.select_for_update().get(pk=sync_id)
            if channel.status != "active" or (channel.config_json or {}).get("setup_revision") != sync.setup_revision:
                sync.state = "obsolete"
                sync.save(update_fields=["state"])
                return
            if getattr(sync, request_field):
                continue
            if sync.requesting:
                # An interrupted request may have reached Meta. Never replay a once-only operation.
                return
            if timezone.now() > sync.created_at + timezone.timedelta(hours=24):
                sync.state, sync.error_code = "expired", "onboarding_window_expired"
                sync.save(update_fields=["state", "error_code"])
                return
            sync.requesting, sync.state = kind, "requesting"
            sync.save(update_fields=["requesting", "state"])
            token = get_whatsapp_access_token(channel)
        try:
            response = graph_call(f"{quote(sync.phone_number_id, safe='')}/smb_app_data", token,
                                  body={"messaging_product": "whatsapp", "sync_type": kind})
            request_id = response.get("request_id")
            if not isinstance(request_id, str) or not 0 < len(request_id) <= 255:
                raise ValueError("Meta did not confirm synchronization acceptance.")
        except (ValueError, OSError):
            WhatsAppCoexistenceSync.objects.filter(pk=sync.pk).update(state="request_unknown", error_code="request_outcome_unknown")
            return
        with transaction.atomic():
            current = WhatsAppCoexistenceSync.objects.select_for_update().get(pk=sync.pk)
            setattr(current, request_field, request_id)
            current.requesting = ""
            if current.state == "requesting":
                current.state = "awaiting_history"
            current.save(update_fields=[request_field, "requesting", "state"])


def sync_status(channel):
    sync = WhatsAppCoexistenceSync.objects.filter(channel=channel, setup_revision=(channel.config_json or {}).get("setup_revision")).first()
    if sync is None:
        return None
    pending = sync.events.filter(status__in=["received", "failed", "awaiting_history"]).count()
    failed = sync.events.filter(status="failed").exists()
    state = sync.state
    if sync.progress == 100 and not pending and state == "importing":
        state = "complete"
    return {"state": state, "progress": sync.progress, "pending_batches": pending,
            "error_code": sync.error_code or ("batch_processing_failed" if failed else "")}
