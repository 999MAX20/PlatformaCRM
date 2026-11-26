from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny
from rest_framework.throttling import ScopedRateThrottle

from apps.businesses.access import Actions, Resources, assert_can
from apps.bots.models import BotChannel
from apps.core.permissions import accessible_businesses
from apps.integrations.ycloud import client, onboarding
from apps.integrations.ycloud.models import YCloudConnection


class YCloudSetupView(APIView):
    permission_classes = [IsAuthenticated]

    def channel(self, request, pk, action):
        channel = get_object_or_404(BotChannel.objects.select_related("bot__business").filter(
            bot__business__in=accessible_businesses(request.user), channel="whatsapp",
        ).exclude(bot__settings_json__has_key="_deleted_at"), pk=pk)
        assert_can(request.user, channel.bot.business, Resources.INTEGRATIONS, action)
        return channel

    def get(self, request, pk):
        channel = self.channel(request, pk, Actions.VIEW)
        connection = YCloudConnection.objects.filter(channel=channel).first()
        state = connection.status if connection else "not_connected"
        if state == "disconnected":
            state = "not_connected"
        if connection and state == "pending" and connection.expires_at <= timezone.now():
            state = "expired"
        from apps.integrations.ycloud.history import history_status
        return Response({"available": client.configured(), "status": state,
            "history": history_status(connection),
            "channel_status": channel.status,
            "onboarding_type": connection.onboarding_type if connection else YCloudConnection.OnboardingTypes.PLATFORM,
            "expected_phone_number": connection.expected_phone_number if connection else "",
            "failed_events": connection.events.filter(status="failed").count() if connection else 0,
            "phone_number": connection.phone_number if connection else "",
            "expires_at": connection.expires_at if connection else None,
            "error_code": connection.last_error if connection else ""})

    def post(self, request, pk):
        channel = self.channel(request, pk, Actions.MANAGE)
        try:
            action = request.data.get("action", "start")
            if action == "start":
                result = onboarding.start(channel, request.user,
                    onboarding_type=request.data.get("onboarding_type", YCloudConnection.OnboardingTypes.PLATFORM),
                    expected_phone_number=request.data.get("expected_phone_number", ""))
            else:
                onboarding.recover(channel, request.user, action)
                result = {"ok": True}
        except client.YCloudError as exc:
            return Response({"code": exc.code}, status=503)
        response = Response(result)
        response["Cache-Control"] = "no-store"
        return response


class YCloudWebhookView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "integration_webhook"

    def post(self, request):
        from apps.integrations.ycloud.webhooks import accept
        accept(request.body, request.META.get("HTTP_YCLOUD_SIGNATURE", ""))
        return Response(status=204)
