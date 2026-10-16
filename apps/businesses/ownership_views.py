from django.db import DatabaseError
from django.views.decorators.cache import never_cache
from rest_framework import serializers
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.businesses.ownership import active_actor, finish_transfer, participant_decision, prepare_transfer
from apps.businesses.ownership_selectors import own_transfers, platform_ownership, transfer_projection
from apps.core.permissions import IsPlatformUser
from apps.core.platform_crm_views import audited_response
from apps.core.platform_details import StrictFieldsMixin


class PrepareSerializer(StrictFieldsMixin, serializers.Serializer):
    new_owner_id = serializers.IntegerField(min_value=1, max_value=9223372036854775807)
    expected_owner_id = serializers.IntegerField(min_value=1, max_value=9223372036854775807)
    previous_owner_business_role_id = serializers.IntegerField(min_value=1, max_value=9223372036854775807, allow_null=True)
    support_case_id = serializers.IntegerField(min_value=1, max_value=9223372036854775807)
    reason = serializers.CharField(max_length=2000)


class ActionSerializer(StrictFieldsMixin, serializers.Serializer):
    action = serializers.ChoiceField(choices=["execute", "cancel"])


class DecisionSerializer(StrictFieldsMixin, serializers.Serializer):
    decision = serializers.ChoiceField(choices=["confirm", "decline"])


def mutate(request, serializer_type, operation):
    serializer = serializer_type(data=request.data)
    serializer.is_valid(raise_exception=True)
    try:
        transfer = operation(**serializer.validated_data)
    except DatabaseError:
        return Response({"detail": "Ownership transfer is temporarily unavailable.",
            "code": "temporary_service_failure", "category": "temporary"}, status=503)
    return Response(transfer_projection(transfer, active_actor(request)))


@never_cache
@api_view(["GET", "POST"])
@permission_classes([IsPlatformUser])
def platform_business_ownership(request, business_id):
    if request.method == "GET":
        return audited_response(request, business_id, "ownership", lambda business: platform_ownership(business, request.user))
    return mutate(request, PrepareSerializer, lambda **data: prepare_transfer(request, business_id, **data))


@never_cache
@api_view(["POST"])
@permission_classes([IsPlatformUser])
def platform_ownership_action(request, business_id, transfer_id):
    return mutate(request, ActionSerializer, lambda **data: finish_transfer(request, business_id, transfer_id, **data))


@never_cache
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def account_ownership_transfers(request):
    return Response({"results": own_transfers(active_actor(request))})


@never_cache
@api_view(["POST"])
@permission_classes([IsAuthenticated])
def account_ownership_decision(request, transfer_id):
    return mutate(request, DecisionSerializer, lambda **data: participant_decision(request, transfer_id, **data))
