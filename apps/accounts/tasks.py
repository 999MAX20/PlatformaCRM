from celery import shared_task
from django.core.management import call_command


@shared_task(name="accounts.flush_expired_tokens", queue="default")
def flush_expired_tokens():
    call_command("flushexpiredtokens")
    from apps.accounts.google_auth import prune_google_flows
    prune_google_flows()
