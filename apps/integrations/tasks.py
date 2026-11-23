from celery import shared_task


@shared_task(name="integrations.cleanup_google_data", queue="integrations", soft_time_limit=240, time_limit=300)
def cleanup_google_data():
    from django.conf import settings
    from apps.integrations.google_retention import cleanup_google
    if not settings.GOOGLE_RETENTION_ENABLED:
        return {"enabled": False}
    return cleanup_google(apply=True)


@shared_task(name="integrations.process_google_calendars", queue="integrations")
def process_google_calendars():
    from apps.integrations.google_calendar_sync import process_due
    return process_due()


@shared_task(name="integrations.process_ycloud_events")
def process_ycloud_events():
    from apps.integrations.ycloud.events import process_due
    return process_due()


@shared_task(name="integrations.process_whatsapp_coexistence_event", queue="integrations",
             autoretry_for=(Exception,), retry_backoff=True, max_retries=5,
             acks_late=True, reject_on_worker_lost=True)
def process_whatsapp_coexistence_event(event_id):
    from apps.integrations.whatsapp.coexistence_events import process_event
    from apps.integrations.models import WhatsAppCoexistenceEvent
    try:
        process_event(event_id)
    except Exception:
        WhatsAppCoexistenceEvent.objects.filter(pk=event_id).update(status="failed", error_code="processing_failed")
        raise


@shared_task(name="integrations.start_whatsapp_coexistence_sync", queue="integrations", acks_late=True, reject_on_worker_lost=True,
             autoretry_for=(Exception,), retry_backoff=True, max_retries=5)
def start_whatsapp_coexistence_sync(sync_id):
    from apps.integrations.whatsapp.coexistence_sync import start_sync
    start_sync(sync_id)
