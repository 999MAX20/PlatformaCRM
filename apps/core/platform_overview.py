"""Bounded operator queues. Counts use the same definitions as destination lists."""
from django.db.models import Case, Count, IntegerField, Q, Value, When
from django.utils import timezone

from apps.core.platform_reads import read_platform_source
from apps.core.platform_worklists import linked_counts
from apps.core.service_status import COMPONENTS, business_service_status_many, filter_service_businesses, service_businesses
from apps.support.access import active_platform_users, scoped_cases


PREVIEW_LIMIT = 6


def clinic_attention(now):
    clinics = service_businesses(now=now)
    counts = {state: filter_service_businesses(clinics, state).count()
              for state in ("degraded", "unknown")}
    rows = list(filter_service_businesses(clinics, "attention").annotate(
        attention_order=Case(When(degraded_count__gt=0, then=Value(0)), default=Value(1), output_field=IntegerField()),
    ).order_by("attention_order", "pk").values("id", "name", "fresh_count", "degraded_count")[:PREVIEW_LIMIT])
    observations = business_service_status_many([row["id"] for row in rows], now=now)
    episodes = [{"business_id": pk, **item} for pk, service in observations.items()
                for item in service["components"] if item["state"] != "healthy" and item["episode"]]
    links = read_platform_source(lambda: linked_counts(episodes)) if episodes else {}
    for pk, service in observations.items():
        for item in service["components"]:
            item["linked_cases"] = links.get((pk, item["component"], item["episode"]), 0) if links is not None else None
    return {**counts, "count": sum(counts.values()), "results": [
        {"id": row["id"], "name": row["name"],
         "status": "degraded" if row["degraded_count"] else "unknown",
         "degraded_components": row["degraded_count"],
         "unknown_components": len(COMPONENTS)-row["fresh_count"],
         "components": [item for item in observations[row["id"]]["components"] if item["state"] != "healthy"]} for row in rows
    ], "links_available": links is not None}


def support_attention(actor):
    cases = scoped_cases(actor, platform=True).exclude(status="resolved")
    counts = cases.aggregate(count=Count("pk"), unassigned=Count("pk", filter=Q(assigned_to__isnull=True)),
                             waiting_clinic=Count("pk", filter=Q(status="waiting_clinic")))
    rows = cases.select_related("business", "assigned_to").annotate(
        assignee_available=Case(When(assigned_to__in=active_platform_users(), then=Value(True)), default=Value(False)),
    ).order_by("-updated_at", "-pk")[:PREVIEW_LIMIT]
    return {**counts, "results": [
        {"id": row.pk, "subject": row.subject, "business_id": row.business_id,
         "business_name": row.business.name, "status": row.status, "updated_at": row.updated_at,
         "assignee": {"id": row.assigned_to_id,
                      "name": row.assigned_to.full_name or row.assigned_to.email,
                      "available": row.assignee_available} if row.assigned_to_id else None}
        for row in rows
    ]}


def overview_attention(actor):
    now = timezone.now()
    clinics = read_platform_source(lambda: clinic_attention(now))
    support = read_platform_source(lambda: support_attention(actor))
    return {"generated_at": now, "preview_limit": PREVIEW_LIMIT,
            "clinics": clinics, "support": support,
            "unavailable_sources": [key for key, value in (("clinics", clinics), ("support", support)) if value is None]}
