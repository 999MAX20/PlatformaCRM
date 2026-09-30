from rest_framework import serializers
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from apps.accounts.auth_views import set_refresh_cookie
from apps.accounts.email_changes import confirm_email_change, request_email_change


class EmailChangeRequestSerializer(serializers.Serializer):
    new_email = serializers.EmailField(max_length=254)
    current_password = serializers.CharField(write_only=True, trim_whitespace=False)
    mfa_code = serializers.CharField(write_only=True, required=False, allow_blank=True)


class EmailChangeConfirmSerializer(serializers.Serializer):
    code = serializers.RegexField(r"^[0-9]{6}$", write_only=True)


class EmailChangeRequestView(APIView):
    permission_classes = [IsAuthenticated]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "auth_email_change"

    def post(self, request):
        serializer = EmailChangeRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return Response(request_email_change(request, **serializer.validated_data))


class EmailChangeConfirmView(APIView):
    permission_classes = [IsAuthenticated]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "auth_profile"

    def post(self, request):
        serializer = EmailChangeConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user, refresh = confirm_email_change(request, **serializer.validated_data)
        response = Response({"ok": True, "email": user.email, "access": str(refresh.access_token)})
        response["Cache-Control"] = "no-store"
        return set_refresh_cookie(response, str(refresh))
