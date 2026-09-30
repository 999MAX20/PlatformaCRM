from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from apps.accounts.device_sessions import device_session_list, revoke_device_session


class AccountSessionsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        response = Response(device_session_list(request.user, request.auth))
        response["Cache-Control"] = "private, no-store"
        return response


class RevokeAccountSessionView(APIView):
    permission_classes = [IsAuthenticated]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "auth_profile"

    def post(self, request, session_id):
        revoke_device_session(request, session_id, code=request.data.get("code", ""))
        return Response({"ok": True})
