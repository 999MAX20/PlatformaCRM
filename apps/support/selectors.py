from django.db.models import BigIntegerField, Count, F, OuterRef, Q, Subquery, Value
from django.db.models.functions import Coalesce

from apps.support.access import active_platform_users, scoped_cases
from apps.support.models import ReadState


def case_projection(actor, *, platform=False):
    read_cursor = ReadState.objects.filter(case_id=OuterRef("pk"), user=actor).values("last_read_message_id")[:1]
    return scoped_cases(actor, platform=platform).select_related(
        "business", "created_by", "requester", "assigned_to",
    ).annotate(
        read_through=Coalesce(Subquery(read_cursor), Value(0), output_field=BigIntegerField()),
    ).annotate(
        unread_count=Count("public_messages", filter=(
            Q(public_messages__id__gt=F("read_through")) & ~Q(public_messages__author=actor)
        )),
    )


def filtered_cases(actor, filters, *, platform=False):
    cases = case_projection(actor, platform=platform)
    if filters.get("business"):
        cases = cases.filter(business_id=filters["business"])
    status = filters.get("status")
    if status == "active":
        cases = cases.exclude(status="resolved")
    elif status:
        cases = cases.filter(status=status)
    assignee = filters.get("assignee")
    if assignee == "me":
        cases = cases.filter(assigned_to=actor)
    elif assignee == "unassigned":
        cases = cases.filter(assigned_to__isnull=True)
    elif assignee == "unavailable":
        cases = cases.filter(assigned_to__isnull=False).exclude(assigned_to__in=active_platform_users())
    elif assignee:
        cases = cases.filter(assigned_to_id=int(assignee))
    needle = filters.get("search", "")
    if needle:
        condition = Q(subject__icontains=needle)
        if needle.isascii() and needle.isdecimal() and len(needle) < 19:
            condition |= Q(pk=int(needle))
        cases = cases.filter(condition)
    if filters.get("unread"):
        cases = cases.filter(unread_count__gt=0)
    return cases.order_by("-updated_at", "-pk")
