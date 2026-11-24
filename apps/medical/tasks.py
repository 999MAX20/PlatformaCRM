import logging
from celery import shared_task
from django.utils import timezone

from .models import ReceptionBookingRequest
from .reception_notifications import escalate_reception_request


@shared_task(name="medical.escalate_reception")
def escalate_reception(*, limit=100, after_id=0):
    rows = list(ReceptionBookingRequest.objects.filter(pk__gt=after_id, state__in=["new", "pending"],
        assignee__isnull=True, acceptance_due_at__lte=timezone.now()).order_by("pk").values_list("pk", flat=True)[:limit + 1])
    for identifier in rows[:limit]:
        try: escalate_reception_request(identifier)
        except Exception:
            logging.getLogger(__name__).exception("reception.escalation_failed", extra={"request_pk": identifier})
    if len(rows) > limit:
        escalate_reception.apply_async(kwargs={"limit": limit, "after_id": rows[limit - 1]})
    return len(rows[:limit])
