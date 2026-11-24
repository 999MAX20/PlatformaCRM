from rest_framework import serializers, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .role_reads import (read_medical_role_workspace, read_medical_role_definitions,
                         read_medical_role_members, read_medical_role_member_context,
                         read_medical_role_member_branches, read_medical_role_history)
from .serializers import StrictSerializer
from .models import MedicalRoleAssignment
from .role_services import create_medical_role, assign_medical_role, revoke_medical_role


class MedicalRoleScopeSerializer(StrictSerializer):
    business_id = serializers.IntegerField(min_value=1)


class MedicalRolePageSerializer(MedicalRoleScopeSerializer):
    after_id = serializers.IntegerField(min_value=1, required=False)
    limit = serializers.IntegerField(min_value=1, max_value=50, default=20)
    query = serializers.CharField(max_length=100, required=False, allow_blank=True)


class MedicalRoleMemberSerializer(MedicalRoleScopeSerializer):
    member_id = serializers.IntegerField(min_value=1)


class MedicalRoleBranchSerializer(MedicalRolePageSerializer):
    member_id = serializers.IntegerField(min_value=1)


class MedicalRoleHistorySerializer(MedicalRoleMemberSerializer):
    after_id = serializers.IntegerField(min_value=1, required=False)
    limit = serializers.IntegerField(min_value=1, max_value=50, default=20)


class MedicalRolePermissionSerializer(StrictSerializer):
    resource = serializers.CharField(max_length=64)
    action = serializers.CharField(max_length=32)
    scope = serializers.ChoiceField(choices=["own", "team", "business"])


class MedicalRoleDefinitionSerializer(MedicalRoleScopeSerializer):
    name = serializers.CharField(max_length=128)
    kind = serializers.ChoiceField(choices=MedicalRoleAssignment.Kinds.values)
    permissions = MedicalRolePermissionSerializer(many=True, allow_empty=False, max_length=64)


class MedicalRoleRevokeSerializer(MedicalRoleMemberSerializer):
    expected_revision = serializers.IntegerField(min_value=1)
    reason = serializers.CharField(max_length=2000, trim_whitespace=False)


class MedicalRoleAssignSerializer(MedicalRoleRevokeSerializer):
    expected_revision = serializers.IntegerField(min_value=0)
    role_id = serializers.IntegerField(min_value=1)
    branch_ids = serializers.ListField(child=serializers.IntegerField(min_value=1))
    all_branches = serializers.BooleanField()


class ReceptionDutyReadSerializer(MedicalRoleScopeSerializer):
    branch_id = serializers.IntegerField(min_value=1, required=False)
    after_id = serializers.IntegerField(min_value=0, default=0)
    search = serializers.CharField(max_length=100, required=False, allow_blank=True)
    kind = serializers.ChoiceField(choices=("branches", "members"), default="branches")


class ReceptionDutyWriteSerializer(MedicalRoleScopeSerializer):
    branch_id = serializers.IntegerField(min_value=1)
    lead_id = serializers.IntegerField(min_value=1)
    deputy_id = serializers.IntegerField(min_value=1, allow_null=True)
    lead_available = serializers.BooleanField()
    starts_at = serializers.DateTimeField()
    ends_at = serializers.DateTimeField()
    expected_revision = serializers.IntegerField(min_value=0)
    reason = serializers.CharField(max_length=1000)


class MedicalRoleManagementViewSet(viewsets.GenericViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = MedicalRoleScopeSerializer

    @action(detail=False, methods=["get", "post"], url_path="reception-duty")
    def reception_duty(self, request):
        from .reception_duties import read_reception_duty, save_reception_duty
        if request.method == "GET":
            return self._read(request, ReceptionDutyReadSerializer, read_reception_duty)
        serializer = ReceptionDutyWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return Response(save_reception_duty(actor=request.user, **serializer.validated_data,
            idempotency_key=request.headers.get("Idempotency-Key")))

    def get_serializer_class(self):
        if self.action == "roles" and self.request.method == "POST":
            return MedicalRoleDefinitionSerializer
        return {"roles": MedicalRolePageSerializer, "members": MedicalRolePageSerializer,
                "member_context": MedicalRoleMemberSerializer, "branches": MedicalRoleBranchSerializer,
                "history": MedicalRoleHistorySerializer, "assign": MedicalRoleAssignSerializer,
                "revoke": MedicalRoleRevokeSerializer}.get(
                    self.action, self.serializer_class)

    def finalize_response(self, request, response, *args, **kwargs):
        response = super().finalize_response(request, response, *args, **kwargs)
        response["Cache-Control"] = "no-store, private"
        response["Pragma"] = "no-cache"
        return response

    def _read(self, request, serializer_class, service):
        serializer = serializer_class(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        return Response(service(actor=request.user, **serializer.validated_data))

    @action(detail=False, methods=["get"])
    def workspace(self, request):
        return self._read(request, MedicalRoleScopeSerializer, read_medical_role_workspace)

    @action(detail=False, methods=["get", "post"])
    def roles(self, request):
        if request.method == "POST":
            serializer = MedicalRoleDefinitionSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            role, replayed = create_medical_role(actor=request.user, **serializer.validated_data,
                idempotency_key=request.headers.get("Idempotency-Key"))
            return Response({"id": role.pk, "replayed": replayed}, status=200 if replayed else 201)
        return self._read(request, MedicalRolePageSerializer, read_medical_role_definitions)

    @action(detail=False, methods=["get"])
    def members(self, request):
        return self._read(request, MedicalRolePageSerializer, read_medical_role_members)

    @action(detail=False, methods=["get"], url_path="member-context")
    def member_context(self, request):
        return self._read(request, MedicalRoleMemberSerializer, read_medical_role_member_context)

    @action(detail=False, methods=["get"])
    def branches(self, request):
        return self._read(request, MedicalRoleBranchSerializer, read_medical_role_member_branches)

    @action(detail=False, methods=["get"])
    def history(self, request):
        return self._read(request, MedicalRoleHistorySerializer, read_medical_role_history)

    def _command(self, request, serializer_class, service):
        serializer = serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        assignment, replayed = service(actor=request.user, **serializer.validated_data,
            idempotency_key=request.headers.get("Idempotency-Key"))
        return Response({"id": assignment.pk, "revision": assignment.revision,
                         "revoked_at": assignment.revoked_at, "replayed": replayed})

    @action(detail=False, methods=["post"])
    def assign(self, request):
        return self._command(request, MedicalRoleAssignSerializer, assign_medical_role)

    @action(detail=False, methods=["post"])
    def revoke(self, request):
        return self._command(request, MedicalRoleRevokeSerializer, revoke_medical_role)
