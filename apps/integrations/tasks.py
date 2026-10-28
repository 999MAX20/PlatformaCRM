from celery import shared_task


@shared_task(name="integrations.process_ycloud_events")
def process_ycloud_events():
    from apps.integrations.ycloud.events import process_due
    return process_due()
