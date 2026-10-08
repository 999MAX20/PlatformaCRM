from django.utils import timezone
from rest_framework.decorators import action
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import ReadOnlyModelViewSet, ViewSet

from apps.billing.models import Subscription, SubscriptionPlan
from apps.billing.serializers import PlanChangeSerializer, SubscriptionPlanSerializer, SubscriptionSerializer, SubscriptionSettingsSerializer
from apps.billing.services import update_subscription_metadata
from apps.billing.entitlements import entitlement_summary
from apps.billing.usage import usage_summary
from apps.businesses.access import Actions, Resources, assert_can
from apps.core.permissions import accessible_businesses


def selected_billing_business(request, action=Actions.VIEW):
    """Never silently choose a tenant when the account has several businesses."""
    query_id = request.query_params.get("business")
    body_id = request.data.get("business")
    if query_id is not None and body_id is not None and str(query_id) != str(body_id):
        raise ValidationError({"business": "Conflicting business selectors."})
    selected_id = query_id if query_id is not None else body_id
    queryset = accessible_businesses(request.user)
    if selected_id is not None:
        from rest_framework import serializers

        selected_id = serializers.IntegerField(min_value=1).run_validation(selected_id)
        business = queryset.filter(pk=selected_id).first()
        if business is None:
            raise NotFound()
    else:
        candidates = list(queryset[:2])
        if len(candidates) > 1:
            raise ValidationError({"business": "Select a business."})
        business = candidates[0] if candidates else None
    if business:
        assert_can(request.user, business, Resources.BILLING, action)
    return business


class SubscriptionPlanViewSet(ReadOnlyModelViewSet):
    serializer_class = SubscriptionPlanSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        return SubscriptionPlan.objects.filter(is_active=True)


class CurrentSubscriptionViewSet(ViewSet):
    permission_classes = [IsAuthenticated]

    def list(self, request):
        business = selected_billing_business(request)
        if not business:
            return Response(None)
        assert_can(request.user, business, Resources.BILLING, Actions.VIEW)

        subscription = (
            Subscription.objects.select_related("business", "plan")
            .filter(business=business)
            .first()
        )
        if not subscription:
            return Response(None)

        return Response(SubscriptionSerializer(subscription).data)

    def _business(self, request, action=Actions.VIEW):
        business = selected_billing_business(request, action)
        if not business:
            raise ValidationError("Business is required.")
        assert_can(request.user, business, Resources.BILLING, action)
        return business

    def _subscription(self, request, action=Actions.MANAGE):
        business = self._business(request, action=action)
        subscription = Subscription.objects.select_related("business", "plan", "requested_plan").filter(business=business).first()
        if not subscription:
            raise ValidationError("Subscription is required.")
        return subscription

    @action(detail=False, methods=["patch"], url_path="settings")
    def update_settings(self, request):
        subscription = self._subscription(request, action=Actions.MANAGE)
        serializer = SubscriptionSettingsSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        subscription = update_subscription_metadata(request=request, subscription=subscription, changes=serializer.validated_data)
        return Response(SubscriptionSerializer(subscription).data)

    @action(detail=False, methods=["post"], url_path="change-plan")
    def change_plan(self, request):
        subscription = self._subscription(request, action=Actions.MANAGE)
        serializer = PlanChangeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        subscription = update_subscription_metadata(request=request, subscription=subscription, changes={
            "requested_plan": serializer.validated_data["plan"], "plan_change_requested_at": timezone.now(),
        })
        return Response(SubscriptionSerializer(subscription).data)

    @action(detail=False, methods=["post"])
    def pause(self, request):
        subscription = self._subscription(request, action=Actions.MANAGE)
        subscription = update_subscription_metadata(request=request, subscription=subscription, changes={"status": Subscription.Statuses.PAUSED})
        return Response(SubscriptionSerializer(subscription).data)

    @action(detail=False, methods=["post"])
    def resume(self, request):
        subscription = self._subscription(request, action=Actions.MANAGE)
        subscription = update_subscription_metadata(request=request, subscription=subscription, changes={"status": Subscription.Statuses.ACTIVE, "cancelled_at": None})
        return Response(SubscriptionSerializer(subscription).data)

    @action(detail=False, methods=["post"])
    def cancel(self, request):
        subscription = self._subscription(request, action=Actions.MANAGE)
        subscription = update_subscription_metadata(request=request, subscription=subscription, changes={"status": Subscription.Statuses.CANCELLED, "cancelled_at": timezone.now()})
        return Response(SubscriptionSerializer(subscription).data)


class UsageSummaryViewSet(ViewSet):
    permission_classes = [IsAuthenticated]

    def list(self, request):
        business = selected_billing_business(request)
        if not business:
            return Response([])
        assert_can(request.user, business, Resources.BILLING, Actions.VIEW)
        return Response(usage_summary(business))


class EntitlementSummaryViewSet(ViewSet):
    permission_classes = [IsAuthenticated]

    def list(self, request):
        business = selected_billing_business(request)
        if not business:
            return Response([])
        assert_can(request.user, business, Resources.BILLING, Actions.VIEW)
        return Response(entitlement_summary(business))
