from datetime import timedelta

from django.utils import timezone
from rest_framework import serializers

from apps.notifications.models import Notification


class PersonalFeedFilters(serializers.Serializer):
    period = serializers.ChoiceField(choices=("all", "7d", "30d"), default="all")
    order = serializers.ChoiceField(choices=("newest", "oldest"), default="newest")
    awaiting_ack = serializers.BooleanField(default=False)


def filter_personal_feed(queryset, params):
    filters = PersonalFeedFilters(data=params)
    filters.is_valid(raise_exception=True)
    values = filters.validated_data
    if values["awaiting_ack"]:
        queryset = queryset.filter(
            kind=Notification.Kinds.ANNOUNCEMENT,
            personal_acknowledged_at__isnull=True,
        )
    if values["period"] != "all":
        days = 7 if values["period"] == "7d" else 30
        queryset = queryset.filter(send_at__gte=timezone.now() - timedelta(days=days))
    order = ("-send_at", "-pk") if values["order"] == "newest" else ("send_at", "pk")
    return queryset.order_by(*order)
