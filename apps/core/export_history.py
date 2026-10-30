"""Current-access projection of persisted background export jobs."""
from django.db.models import Q
from rest_framework import serializers
from rest_framework.pagination import PageNumberPagination

from apps.businesses.access import Actions, can
from apps.businesses.capabilities import resource_is_enabled
from apps.businesses.models import Business
from apps.core.export_jobs import export_resource
from apps.core.models import ExportJob
from apps.core.serializers import ExportJobSerializer


class ExportHistoryPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 100


class ExportHistoryQuery(serializers.Serializer):
    business = serializers.IntegerField(required=False, min_value=1)
    kind = serializers.ChoiceField(required=False, choices=ExportJob.Kinds.choices)
    status = serializers.ChoiceField(required=False, choices=ExportJob.Statuses.choices)


class ExportHistorySerializer(ExportJobSerializer):
    parameters_json = serializers.SerializerMethodField()

    def get_parameters_json(self, obj):
        # Permission fingerprints are internal download guards, not history data.
        return {key: value for key, value in (obj.parameters_json or {}).items()
                if key in {"start", "end", "expected_rows"}}


def readable_export_history(queryset, user):
    """Filter whole groups before pagination; never expose revoked-resource totals."""
    allowed = Q(pk__in=[])
    groups = queryset.order_by().values_list("business_id", "export_key").distinct()
    groups = list(groups)
    businesses = Business.objects.in_bulk({business_id for business_id, _ in groups})
    for business_id, export_key in groups:
        business = businesses[business_id]
        resource = export_resource(export_key)
        if resource and resource_is_enabled(business, resource) and can(user, business, resource, Actions.VIEW).allowed:
            allowed |= Q(business_id=business_id, export_key=export_key)
    return queryset.filter(allowed)
