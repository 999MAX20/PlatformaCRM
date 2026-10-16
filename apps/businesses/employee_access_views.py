from django.db import DatabaseError
from django.utils import timezone
from django.views.decorators.cache import never_cache
from rest_framework import serializers
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.businesses.employee_access import CONSENT_ACTIONS, prepare, operate, owner_decide
from apps.businesses.employee_access_selectors import diagnostics, projection, repair_rows
from apps.businesses.ownership import active_actor
from apps.core.permissions import IsPlatformUser
from apps.core.platform_details import StrictFieldsMixin
from apps.core.platform_crm_views import audited_response


class Filters(StrictFieldsMixin, serializers.Serializer):
    search = serializers.CharField(max_length=200, allow_blank=True, default="")
    page = serializers.IntegerField(min_value=1, default=1)
    page_size = serializers.IntegerField(min_value=1, max_value=50, default=20)


class Prepare(StrictFieldsMixin, serializers.Serializer):
    request_id = serializers.UUIDField()
    action = serializers.ChoiceField(choices=["disable", "restore", "role", "reissue", "revoke"])
    target_id = serializers.IntegerField(min_value=1, max_value=9223372036854775807)
    target_role_id = serializers.IntegerField(min_value=1, max_value=9223372036854775807, allow_null=True, default=None)
    support_case_id = serializers.IntegerField(min_value=1, max_value=9223372036854775807)
    expected_revision = serializers.CharField(min_length=64, max_length=64)
    reason = serializers.CharField(max_length=2000)


class Action(StrictFieldsMixin, serializers.Serializer):
    action = serializers.ChoiceField(choices=["execute", "cancel"])


class Decision(StrictFieldsMixin, serializers.Serializer):
    decision = serializers.ChoiceField(choices=["confirm", "decline"])


def mutate(request, serializer_type, callback):
    serializer = serializer_type(data=request.data)
    serializer.is_valid(raise_exception=True)
    try:
        item = callback(**serializer.validated_data)
        payload = projection(item)
    except DatabaseError:
        return Response({"detail": "Employee access repair is temporarily unavailable.",
            "code": "temporary_service_failure", "category": "temporary"}, status=503)
    return Response(payload)


@never_cache
@api_view(["GET", "POST"])
@permission_classes([IsPlatformUser])
def platform_employee_access(request, business_id):
    if request.method == "GET":
        active_actor(request)
        filters = Filters(data=request.query_params)
        filters.is_valid(raise_exception=True)
        return audited_response(request, business_id, "employee_access", lambda business: diagnostics(business, **filters.validated_data))
    return mutate(request, Prepare, lambda **data: prepare(request, business_id, **data))


@never_cache
@api_view(["POST"])
@permission_classes([IsPlatformUser])
def platform_employee_access_action(request, business_id, repair_id):
    return mutate(request, Action, lambda **data: operate(request, business_id, repair_id, **data))


@never_cache
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def employee_access_confirmations(request):
    actor = active_actor(request)
    rows = repair_rows().filter(owner=actor, business__owner=actor, action__in=CONSENT_ACTIONS,
        status="pending", owner_confirmed_at__isnull=True, expires_at__gt=timezone.now())[:50]
    return Response({"results": [projection(row) for row in rows]})


@never_cache
@api_view(["POST"])
@permission_classes([IsAuthenticated])
def employee_access_decision(request, repair_id):
    return mutate(request, Decision, lambda **data: owner_decide(request, repair_id, **data))
