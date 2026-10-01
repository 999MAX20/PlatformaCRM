"""Permission-scoped read fields for the lead workspace."""
from django.db.models import F, OuterRef, Subquery

from apps.businesses.access import Resources
from apps.core.crm_read_scope import readable_across_businesses
from apps.tasks.models import Task


def annotate_lead_next_task(queryset, *, actor):
    next_task = readable_across_businesses(
        Task.objects.filter(is_archived=False), actor=actor, resource=Resources.TASKS,
    ).filter(
        business_id=OuterRef("business_id"), lead_id=OuterRef("pk"),
    ).exclude(
        status__in=[Task.Statuses.DONE, Task.Statuses.CANCELLED],
    ).order_by(F("due_at").asc(nulls_last=True), "created_at", "pk")
    return queryset.annotate(
        next_task_id=Subquery(next_task.values("pk")[:1]),
        next_task_title=Subquery(next_task.values("title")[:1]),
        next_task_due_at=Subquery(next_task.values("due_at")[:1]),
    )
