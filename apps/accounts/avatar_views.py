import base64
from rest_framework import serializers

from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from .auth_views import record_security_event
from .avatars import save_avatar
from .models import UserAvatar


def avatar_payload(avatar):
    return {"image": "data:image/jpeg;base64," + base64.b64encode(bytes(avatar.image)).decode("ascii") if avatar else None}


class AvatarCropSerializer(serializers.Serializer):
    x = serializers.FloatField(min_value=0, max_value=1)
    y = serializers.FloatField(min_value=0, max_value=1)
    size = serializers.FloatField(min_value=0.01, max_value=1)


class CurrentUserAvatarView(APIView):
    permission_classes = [IsAuthenticated]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "auth_profile"

    def get_throttles(self):
        return [] if self.request.method in {"GET", "HEAD", "OPTIONS"} else super().get_throttles()

    def finalize_response(self, request, response, *args, **kwargs):
        response = super().finalize_response(request, response, *args, **kwargs)
        response["Cache-Control"] = "private, no-store"
        return response

    def get(self, request):
        return Response(avatar_payload(UserAvatar.objects.filter(user=request.user).first()))

    def post(self, request):
        crop = None
        if any(key in request.data for key in ("x", "y", "size")):
            serializer = AvatarCropSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            crop = tuple(serializer.validated_data[key] for key in ("x", "y", "size"))
        avatar = save_avatar(request.user, request.FILES.get("file"), crop=crop)
        record_security_event(request, user=request.user, event="avatar_updated", risk_level="low")
        return Response(avatar_payload(avatar))

    def delete(self, request):
        UserAvatar.objects.filter(user=request.user).delete()
        record_security_event(request, user=request.user, event="avatar_removed", risk_level="low")
        return Response({"image": None})
