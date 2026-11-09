from datetime import datetime, time

from django.db.models import Count
from django.db.models.functions import TruncDate
from django.utils import timezone
from rest_framework import serializers

from apps.scheduling.models import Appointment


class CalendarSummaryQuery(serializers.Serializer):
    business = serializers.IntegerField(min_value=1)
    start_from = serializers.DateField()
    start_to = serializers.DateField()
    service = serializers.IntegerField(min_value=1, required=False)
    resource = serializers.IntegerField(min_value=1, required=False)
    branch = serializers.IntegerField(min_value=1, required=False)
    status = serializers.ChoiceField(choices=Appointment.Statuses.choices, required=False)

    def validate(self, attrs):
        days = (attrs["start_to"] - attrs["start_from"]).days
        if not 1 <= days <= 366:
            raise serializers.ValidationError({"start_to": "Select 1 to 366 days; end is exclusive."})
        return attrs


def calendar_summary(queryset, *, filters, zone):
    """Count accessible records by their local start day, never by overlap days."""
    start = timezone.make_aware(datetime.combine(filters["start_from"], time.min), zone)
    end = timezone.make_aware(datetime.combine(filters["start_to"], time.min), zone)
    rows = (
        queryset.filter(is_archived=False, start_at__gte=start, start_at__lt=end)
        .order_by().annotate(day=TruncDate("start_at", tzinfo=zone))
        .values("day").annotate(appointments=Count("pk", distinct=True)).order_by("day")
    )
    days = [{"date": row["day"].isoformat(), "appointments": row["appointments"]} for row in rows]
    return {
        "start_from": filters["start_from"].isoformat(),
        "start_to": filters["start_to"].isoformat(),
        "timezone": str(zone),
        "days": days,
        "total": sum(day["appointments"] for day in days),
    }
