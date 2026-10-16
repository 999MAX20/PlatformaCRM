from django.conf import settings
from django.core.validators import validate_email
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import DatabaseError
from django.views.decorators.cache import never_cache
from rest_framework import serializers
from rest_framework.decorators import api_view, authentication_classes, permission_classes, throttle_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle

from apps.accounts.models import AccountRecovery
from apps.accounts.recovery import complete, operate, owner_decide, prepare
from apps.accounts.recovery_selectors import platform_snapshot, projection
from apps.businesses.ownership import active_actor
from apps.core.permissions import IsPlatformUser
from apps.core.platform_details import StrictFieldsMixin
from apps.core.platform_crm_views import audited_response


class PrepareSerializer(StrictFieldsMixin, serializers.Serializer):
    user_id = serializers.IntegerField(min_value=1)
    support_case_id = serializers.IntegerField(min_value=1)
    new_email = serializers.EmailField(max_length=254)
    expected_revision = serializers.CharField(min_length=64, max_length=64)
    reason = serializers.CharField(max_length=2000)
    verified_reference = serializers.CharField(max_length=500, allow_blank=True, default="")


class ActionSerializer(StrictFieldsMixin, serializers.Serializer):
    action = serializers.ChoiceField(choices=["send", "cancel"])


class DecisionSerializer(StrictFieldsMixin, serializers.Serializer):
    decision = serializers.ChoiceField(choices=["confirm", "decline"])


class CompleteSerializer(StrictFieldsMixin, serializers.Serializer):
    recovery_id = serializers.UUIDField()
    token = serializers.CharField(min_length=40, max_length=100, write_only=True)
    password = serializers.CharField(min_length=8, max_length=128, trim_whitespace=False, write_only=True)


class RecoveryThrottle(AnonRateThrottle):
    scope = "auth_mfa"


def mutate(request, serializer_type, callback, *, platform=False):
    serializer = serializer_type(data=request.data)
    serializer.is_valid(raise_exception=True)
    try:
        item = callback(**serializer.validated_data)
    except DatabaseError:
        return Response({"detail": "Account recovery is temporarily unavailable.", "code": "temporary_service_failure", "category": "temporary"}, status=503)
    return Response(projection(item, platform=platform))


@never_cache
@api_view(["GET", "POST"])
@permission_classes([IsPlatformUser])
def platform_recovery(request, business_id):
    if request.method == "GET":
        active_actor(request)
        return audited_response(request, business_id, "account_recovery", platform_snapshot)
    return mutate(request, PrepareSerializer, lambda **data: prepare(request, business_id, **data), platform=True)


@never_cache
@api_view(["POST"])
@permission_classes([IsPlatformUser])
def platform_recovery_action(request, business_id, recovery_id):
    return mutate(request, ActionSerializer, lambda **data: operate(request, business_id, recovery_id, **data), platform=True)


@never_cache
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def recovery_confirmations(request):
    actor = active_actor(request)
    rows = AccountRecovery.objects.filter(owner=actor, owner_required=True, status="pending", owner_confirmed_at__isnull=True,
        business__owner=actor).select_related("business", "user").order_by("-created_at")[:50]
    return Response({"results": [projection(item) for item in rows]})


@never_cache
@api_view(["POST"])
@permission_classes([IsAuthenticated])
def recovery_decision(request, recovery_id):
    return mutate(request, DecisionSerializer, lambda **data: owner_decide(request, recovery_id, **data))


@never_cache
@api_view(["GET", "POST"])
@authentication_classes([])
@permission_classes([AllowAny])
@throttle_classes([RecoveryThrottle])
def public_recovery(request):
    if request.method == "GET":
        email = getattr(settings, "ACCOUNT_RECOVERY_SUPPORT_EMAIL", "").strip()
        try:
            validate_email(email)
        except DjangoValidationError:
            email = ""
        return Response({"support_email": email or None})
    serializer = CompleteSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    try:
        complete(request, **serializer.validated_data)
    except DatabaseError:
        return Response({"detail": "Account recovery is temporarily unavailable.", "code": "temporary_service_failure", "category": "temporary"}, status=503)
    return Response({"ok": True})
