"""Bounded operator reads; recorded failures are not current service incidents."""
from datetime import datetime, time, timedelta, timezone as dt_timezone

from django.db.models import Count, Q
from django.utils import timezone
from rest_framework import serializers
from rest_framework.decorators import api_view, permission_classes
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response

from apps.automations.models import AutomationRun
from apps.core.models import ServiceComponentState
from apps.core.permissions import IsPlatformUser
from apps.core.platform_reads import read_platform_source
from apps.core.platform_connector_status import CONNECTOR_ATTENTION
from apps.core.service_status import COMPONENTS, OBSERVATION_MAX_AGE_SECONDS
from apps.integrations.models import BusinessConnector, IntegrationEventLog, WebhookDeliveryLog
from apps.support.models import IncidentLink


HISTORY = ("automations", "integrations", "webhooks")


class WorklistFilters(serializers.Serializer):
    source = serializers.ChoiceField(choices=("incidents", "connectors", *HISTORY), default="incidents")
    business = serializers.IntegerField(min_value=1, required=False)
    search = serializers.CharField(max_length=200, allow_blank=True, default="")
    component = serializers.ChoiceField(choices=COMPONENTS, required=False)
    freshness = serializers.ChoiceField(choices=("fresh", "unknown"), required=False)
    date_from = serializers.DateField(required=False)
    date_to = serializers.DateField(required=False)
    page = serializers.IntegerField(min_value=1, default=1)
    page_size = serializers.IntegerField(min_value=1, max_value=100, default=20)

    def validate(self, attrs):
        if attrs["source"] != "incidents" and any(key in attrs for key in ("component", "freshness")):
            raise serializers.ValidationError("Observation filters require incidents.")
        if attrs["source"] not in HISTORY and any(key in attrs for key in ("date_from", "date_to")):
            raise serializers.ValidationError("Date filters require recorded failures.")
        if attrs["source"] in HISTORY:
            today = timezone.now().astimezone(dt_timezone.utc).date()
            attrs.setdefault("date_to", today)
            attrs.setdefault("date_from", attrs["date_to"] - timedelta(days=29))
            if attrs["date_to"] > today or not 0 <= (attrs["date_to"] - attrs["date_from"]).days <= 365:
                raise serializers.ValidationError("Select an ordered period of at most 366 days.")
        return attrs


def worklist_queryset(params, now):
    source = params["source"]
    if source == "incidents":
        fresh = Q(observed_at__gte=now-timedelta(seconds=OBSERVATION_MAX_AGE_SECONDS), observed_at__lte=now)
        # Only the latest episode is observable. A stale healthy observation is
        # unknown too; it must not silently disappear as confirmed recovery.
        rows = ServiceComponentState.objects.filter(episode__gt=0, started_at__isnull=False).filter(Q(state="degraded") | ~fresh)
        if params.get("component"):
            rows = rows.filter(component=params["component"])
        if params.get("freshness"):
            rows = rows.filter(fresh if params["freshness"] == "fresh" else ~fresh)
        order = ("started_at", "pk")
    elif source == "connectors":
        rows = BusinessConnector.objects.filter(status__in=CONNECTOR_ATTENTION)
        order = ("-updated_at", "-pk")
    else:
        model = {"automations": AutomationRun, "integrations": IntegrationEventLog, "webhooks": WebhookDeliveryLog}[source]
        start = datetime.combine(params["date_from"], time.min, tzinfo=dt_timezone.utc)
        end = datetime.combine(params["date_to"] + timedelta(days=1), time.min, tzinfo=dt_timezone.utc)
        rows = model.objects.filter(status="failed", created_at__gte=start, created_at__lt=end)
        order = ("-created_at", "-pk")
    if params.get("business"):
        rows = rows.filter(business_id=params["business"])
    if params["search"]:
        search = Q(business__name__icontains=params["search"])
        if params["search"].isascii() and params["search"].isdigit() and len(params["search"]) < 19:
            search |= Q(business_id=int(params["search"]))
        rows = rows.filter(search)
    return rows.select_related("business").order_by(*order)


def project_row(row, source, now):
    item = {"id": row.pk, "business_id": row.business_id,
            "business_name": row.business.name if row.business_id else None, "status": row.state if source == "incidents" else row.status}
    if source == "incidents":
        fresh = now-timedelta(seconds=OBSERVATION_MAX_AGE_SECONDS) <= row.observed_at <= now
        item.update(component=row.component, episode=row.episode, started_at=row.started_at,
                    observed_at=row.observed_at, affected_count=row.affected_count,
                    status=row.state if fresh else "unknown", fresh=fresh)
    elif source == "connectors":
        item.update(provider=row.provider, occurred_at=row.updated_at)
    elif source == "automations":
        item.update(kind=row.trigger_type, attempts=row.attempts, max_attempts=row.max_attempts, occurred_at=row.created_at)
    elif source == "integrations":
        item.update(provider=row.provider, kind=row.direction, occurred_at=row.created_at)
    else:
        item.update(kind=row.event_type, attempts=row.attempts, occurred_at=row.created_at)
    return item


def linked_counts(rows):
    matches = Q(pk__in=[])
    for row in rows:
        matches |= Q(case__business_id=row["business_id"], component=row["component"], episode=row["episode"])
    return {(item["case__business_id"], item["component"], item["episode"]): item["total"]
            for item in IncidentLink.objects.filter(matches).values("case__business_id", "component", "episode").annotate(total=Count("pk"))}


@api_view(["GET"])
@permission_classes([IsPlatformUser])
def platform_worklist(request):
    serializer = WorklistFilters(data=request.query_params)
    serializer.is_valid(raise_exception=True)
    params = serializer.validated_data
    now = timezone.now()
    paginator = PageNumberPagination()
    paginator.page_size = params["page_size"]

    def read():
        rows = paginator.paginate_queryset(worklist_queryset(params, now), request)
        return paginator.get_paginated_response([project_row(row, params["source"], now) for row in rows]).data

    data = read_platform_source(read)
    unavailable = []
    if data is None:
        unavailable.append(params["source"])
        data = {"count": None, "next": None, "previous": None, "results": []}
    elif params["source"] == "incidents" and data["results"]:
        counts = read_platform_source(lambda: linked_counts(data["results"]))
        if counts is None:
            unavailable.append("incident_links")
        for row in data["results"]:
            row["linked_cases"] = counts.get((row["business_id"], row["component"], row["episode"]), 0) if counts is not None else None
    return Response({**data, "source": params["source"], "generated_at": now,
                     "unavailable_sources": unavailable,
                     "period": {"from": params["date_from"], "to": params["date_to"], "timezone": "UTC"} if params["source"] in HISTORY else None})
