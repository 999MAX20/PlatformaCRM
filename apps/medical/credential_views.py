from rest_framework import serializers, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .credential_services import (
    confirm_medical_credentials, credential_workspace_access, list_credential_members,
    list_credential_versions, read_medical_credentials,
)
from .serializers import StrictSerializer


class CredentialBusinessSerializer(StrictSerializer):
    business_id = serializers.IntegerField(min_value=1)


class CredentialScopeSerializer(CredentialBusinessSerializer):
    member_id = serializers.IntegerField(min_value=1, required=False, allow_null=True, default=None)


class CredentialReadSerializer(CredentialScopeSerializer):
    version_id = serializers.IntegerField(min_value=1, required=False)


class CredentialConfirmSerializer(CredentialScopeSerializer):
    content = serializers.DictField()
    reason = serializers.CharField(max_length=2000, allow_blank=True, required=False,
                                   default="", trim_whitespace=False)
    expected_revision = serializers.IntegerField(min_value=0)


class CredentialMembersSerializer(CredentialBusinessSerializer):
    before_id = serializers.IntegerField(min_value=1, required=False)
    limit = serializers.IntegerField(min_value=1, max_value=50, required=False, default=20)


class CredentialHistorySerializer(CredentialScopeSerializer):
    before_revision = serializers.IntegerField(min_value=1, required=False)
    limit = serializers.IntegerField(min_value=1, max_value=50, required=False, default=20)


class MedicalCredentialViewSet(viewsets.GenericViewSet):
    permission_classes = [IsAuthenticated]
    http_method_names = ["get", "post", "head", "options"]
    serializer_class = CredentialReadSerializer

    def get_serializer_class(self):
        return {"create": CredentialConfirmSerializer, "workspace_access": CredentialBusinessSerializer,
                "members": CredentialMembersSerializer, "revisions": CredentialHistorySerializer}.get(
                    self.action, CredentialReadSerializer)

    def finalize_response(self, request, response, *args, **kwargs):
        response = super().finalize_response(request, response, *args, **kwargs)
        response["Cache-Control"] = "no-store, private"
        response["Pragma"] = "no-cache"
        return response

    def _read(self, request, service):
        serializer = self.get_serializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        return Response(service(actor=request.user, **serializer.validated_data))

    def list(self, request):
        return self._read(request, read_medical_credentials)

    @action(detail=False, methods=["get"], url_path="workspace-access")
    def workspace_access(self, request):
        return self._read(request, credential_workspace_access)

    @action(detail=False, methods=["get"])
    def members(self, request):
        return self._read(request, list_credential_members)

    @action(detail=False, methods=["get"])
    def revisions(self, request):
        return self._read(request, list_credential_versions)

    def create(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        version, replayed = confirm_medical_credentials(actor=request.user,
            **serializer.validated_data, idempotency_key=request.headers.get("Idempotency-Key"))
        return Response({"version_id": version.pk, "revision": version.revision, "replayed": replayed},
                        status=200 if replayed else 201)
