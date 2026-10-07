"""Read-only operational totals and bounded, deterministic attention ordering."""

from datetime import datetime, time, timedelta

from django.db.models import Count, Q
from django.utils import timezone

from apps.bots.models import BotConversation
from apps.scheduling.availability import business_zone
from apps.scheduling.models import Appointment


def operational_summary(*, business, appointment_scope, conversation_scope, open_deals,
                        sla_deals, no_action_deals, now):
    zone = business_zone(business)
    day = timezone.localtime(now, zone).date()
    start = datetime.combine(day, time.min, tzinfo=zone)
    end = datetime.combine(day + timedelta(days=1), time.min, tzinfo=zone)
    today = appointment_scope.filter(start_at__gte=start, start_at__lt=end).exclude(
        status__in=[Appointment.Statuses.CANCELLED, Appointment.Statuses.RESCHEDULED],
    )
    counts = today.aggregate(
        today_appointments=Count("pk", distinct=True),
        today_confirmations=Count("pk", filter=Q(status=Appointment.Statuses.CREATED), distinct=True),
    )
    waiting = conversation_scope.filter(status=BotConversation.Statuses.OPEN).filter(
        Q(unread_count__gt=0) | Q(handoff_required=True),
    )
    counts["waiting_conversations"] = waiting.distinct().count()
    counts["attention_deals"] = open_deals.filter(
        Q(pk__in=sla_deals.values("pk")) | Q(pk__in=no_action_deals.values("pk")),
    ).distinct().count()
    return {"summary": counts, "day": day.isoformat(), "timezone": str(zone), "waiting": waiting}


def attention_preview(items, *, limit):
    # Waiting customers first, then overdue tasks, confirmations, stalled deals,
    # and stale leads. Within a category: oldest timestamp, stable entity ID.
    ranks = {"conversation": 0, "task": 1, "appointment": 2, "deal": 3, "lead": 4}
    for item in items:
        kind = item["type"]
        item["attention_reason"] = {
            "task": "overdue_task", "lead": "stale_lead", "appointment": "confirmation",
        }.get(kind, item.get("reason"))
        item["attention_at"] = (
            item.get("last_inbound_at") or item.get("last_message_at") if kind == "conversation"
            else item.get("due_at") if kind == "task"
            else item.get("start_at") if kind == "appointment"
            else item.get("attention_at")
        )
    ordered = sorted(items, key=lambda item: (
        ranks[item["type"]], item.get("attention_at") or "", item["id"],
    ))
    unique = {}
    for item in ordered:
        unique.setdefault((item["type"], item["id"]), item)
    return list(unique.values())[:limit]
