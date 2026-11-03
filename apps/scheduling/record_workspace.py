from django.db.models import Count
from django.utils import timezone
from rest_framework import serializers
from rest_framework.pagination import PageNumberPagination

from apps.core.client_projection import client_search_q, client_relation_q


PLANNED_STATUSES = ("created", "confirmed", "rescheduled")


class RecordWorkspaceQuery(serializers.Serializer):
    business = serializers.IntegerField(min_value=1)
    branch = serializers.IntegerField(min_value=1, required=False)
    resource = serializers.IntegerField(min_value=1, required=False)
    service = serializers.IntegerField(min_value=1, required=False)
    client = serializers.IntegerField(min_value=1, required=False)
    responsible_user = serializers.IntegerField(min_value=1, required=False)
    q = serializers.CharField(max_length=200, required=False, allow_blank=True)
    attention = serializers.ChoiceField(choices=("pending_result",), required=False)
    workflow = serializers.ChoiceField(choices=("planned", "completed", "cancelled", "no_show"), required=False)
    confirmed = serializers.BooleanField(required=False)
    ordering = serializers.ChoiceField(choices=("start_at", "-start_at"), default="start_at")
    start_from = serializers.DateField(required=False)
    start_to = serializers.DateField(required=False)
    page = serializers.IntegerField(min_value=1, required=False)
    page_size = serializers.IntegerField(min_value=1, max_value=100, required=False)

    def validate(self, attrs):
        if attrs.get("start_from") and attrs.get("start_to") and attrs["start_from"] >= attrs["start_to"]:
            raise serializers.ValidationError({"start_to": "End must be after start (exclusive)."})
        return attrs


class RecordWorkspacePagination(PageNumberPagination):
    page_size = 25
    page_size_query_param = "page_size"
    max_page_size = 100


def record_workspace(queryset, *, actor, filters):
    """Apply workspace filters to an already tenant/object/branch-scoped queryset."""
    if filters.get("q"):
        queryset = queryset.filter(client_search_q(actor, filters["q"]))
    if filters.get("client"):
        queryset = queryset.filter(client_relation_q(actor), client_id=filters["client"])
    if filters.get("attention") == "pending_result":
        queryset = queryset.filter(status__in=PLANNED_STATUSES, end_at__lte=timezone.now())
    if filters.get("responsible_user"):
        queryset = queryset.filter(responsible_user_id=filters["responsible_user"])
    if "confirmed" in filters:
        queryset = (queryset.filter(status="confirmed") if filters["confirmed"]
                    else queryset.exclude(status="confirmed"))
    counts = {row["status"]: row["count"] for row in queryset.order_by().values("status").annotate(count=Count("pk"))}
    summary = {"planned": sum(counts.get(status, 0) for status in PLANNED_STATUSES),
               **{status: counts.get(status, 0) for status in ("completed", "cancelled", "no_show")}}
    workflow = filters.get("workflow")
    if workflow:
        queryset = queryset.filter(status__in=PLANNED_STATUSES) if workflow == "planned" else queryset.filter(status=workflow)
    ordering = filters["ordering"]
    return queryset.order_by(ordering, "-pk" if ordering.startswith("-") else "pk"), summary
