"""Paginated members of the historical appointment cohort shown by analytics."""
from rest_framework import serializers
from rest_framework.decorators import api_view, permission_classes
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated

from apps.analytics.crm_metrics import _scoped, _visible_performance_members
from apps.analytics.views import _resolve_business
from apps.analytics.workspace import workspace_period, _bounds, _during
from apps.businesses.access import Actions, Resources, assert_can
from apps.businesses.capabilities import assert_resource_enabled
from apps.core.client_projection import ClientProjectionMixin
from apps.scheduling.models import Appointment
from apps.scheduling.record_workspace import PLANNED_STATUSES


class WorkspaceRecordQuery(serializers.Serializer):
    metric = serializers.ChoiceField(choices=("total", "completed", "cancelled", "no_show", "planned"), default="total")
    source = serializers.ChoiceField(choices=Appointment.Sources.choices, required=False)
    service = serializers.IntegerField(min_value=1, max_value=9223372036854775807, required=False)
    responsible_user = serializers.IntegerField(min_value=1, max_value=9223372036854775807, required=False)
    page = serializers.IntegerField(min_value=1, required=False)
    page_size = serializers.IntegerField(min_value=1, max_value=100, required=False)


class WorkspaceRecordSerializer(ClientProjectionMixin, serializers.ModelSerializer):
    client_name = serializers.CharField(source="client.full_name", read_only=True)
    service_name = serializers.CharField(source="service.name", read_only=True)
    responsible_user_name = serializers.SerializerMethodField()

    class Meta:
        model = Appointment
        fields = ("id", "client", "client_name", "service", "service_name", "start_at", "end_at",
                  "status", "source", "responsible_user", "responsible_user_name", "is_archived")
        read_only_fields = fields

    def get_responsible_user_name(self, obj):
        user = obj.responsible_user
        return (user.full_name or user.email) if user else ""


class WorkspaceRecordPagination(PageNumberPagination):
    page_size = 25
    page_size_query_param = "page_size"
    max_page_size = 100


def workspace_records(business, *, user, start_date, end_date, filters):
    records = _scoped(Appointment.objects.filter(business=business), user, business, Resources.APPOINTMENTS)
    records = _during(records, "start_at", _bounds(business, start_date, end_date))
    metric = filters["metric"]
    if metric == "planned":
        records = records.filter(status__in=PLANNED_STATUSES)
    elif metric != "total":
        records = records.filter(status=metric)
    if "responsible_user" in filters:
        if not _visible_performance_members(business=business, user=user).filter(user_id=filters["responsible_user"]).exists():
            raise serializers.ValidationError({"responsible_user": "Member is not available in this report."})
        records = records.filter(responsible_user_id=filters["responsible_user"])
    if "service" in filters:
        records = records.filter(service_id=filters["service"])
    if "source" in filters:
        records = records.filter(source=filters["source"])
    return records.select_related("business", "client", "service", "responsible_user").distinct().order_by("start_at", "pk")


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def report_records(request):
    business = _resolve_business(request)
    for resource in (Resources.ANALYTICS, Resources.APPOINTMENTS):
        assert_resource_enabled(business, resource)
        assert_can(request.user, business, resource, Actions.VIEW)
    start, end = workspace_period(business, request.query_params)
    query = WorkspaceRecordQuery(data=request.query_params)
    query.is_valid(raise_exception=True)
    records = workspace_records(business, user=request.user, start_date=start, end_date=end,
                                filters=query.validated_data)
    paginator = WorkspaceRecordPagination()
    page = paginator.paginate_queryset(records, request)
    response = paginator.get_paginated_response(WorkspaceRecordSerializer(page, many=True, context={"request": request}).data)
    response.data["period"] = {"start": start.isoformat(), "end": end.isoformat(), "timezone": business.timezone}
    return response
