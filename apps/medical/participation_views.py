from rest_framework import serializers, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response

from .participation_closure import end_participation_by_head, end_own_participation
from .participation_closure_reads import read_participation_closure
from .participation_candidates import read_proposal_candidates, read_responsible_candidates
from .participation_proposals import read_proposal_branches, read_outgoing_proposals
from .participation_notice_reads import read_participation_notification
from .participation_reads import (read_participation_invitations, read_managed_participations,
                                 read_own_participations, read_participation_workspace_access,
                                 read_participation_patient_context)
from .models import TreatmentParticipation
from .participation_services import propose_treatment_participation, respond_treatment_participation, withdraw_treatment_participation
from .serializers import StrictSerializer


class ParticipationScopeSerializer(StrictSerializer):
    business_id = serializers.IntegerField(min_value=1)
    patient_id = serializers.IntegerField(min_value=1)


class ParticipationProposalSerializer(ParticipationScopeSerializer):
    branch_id = serializers.IntegerField(min_value=1)
    target_member_id = serializers.IntegerField(min_value=1)
    expected_patient_revision = serializers.IntegerField(min_value=1)
    reason = serializers.CharField(required=False, allow_blank=True, max_length=2000, trim_whitespace=False)
    work_direction = serializers.CharField(required=False, allow_blank=True, max_length=2000, trim_whitespace=False)
    planned_work_date = serializers.DateField(required=False)
    source_appointment_id = serializers.IntegerField(required=False, min_value=1)
    source_participation_id = serializers.IntegerField(required=False, min_value=1)


class ParticipationCommandSerializer(ParticipationScopeSerializer):
    expected_revision = serializers.IntegerField(min_value=1)


class ParticipationClosureSerializer(ParticipationScopeSerializer):
    offset = serializers.IntegerField(min_value=0, default=0)
    limit = serializers.IntegerField(min_value=1, max_value=50, default=20)
    as_head = serializers.BooleanField(default=False)


class ParticipationResponseSerializer(ParticipationCommandSerializer):
    decision = serializers.ChoiceField(choices=("accept", "decline"))
    reason = serializers.CharField(required=False, allow_blank=True, max_length=2000, trim_whitespace=False)


class ParticipationHeadEndSerializer(ParticipationCommandSerializer):
    responsible_member_id = serializers.IntegerField(min_value=1)
    reason = serializers.CharField(max_length=2000, trim_whitespace=False)


class ParticipationListSerializer(StrictSerializer):
    business_id = serializers.IntegerField(min_value=1)
    before_id = serializers.IntegerField(min_value=1, required=False)
    limit = serializers.IntegerField(min_value=1, max_value=50, required=False, default=20)


class ParticipationAccessSerializer(StrictSerializer):
    business_id = serializers.IntegerField(min_value=1)


class ParticipationPatientContextSerializer(ParticipationAccessSerializer):
    client_id = serializers.IntegerField(min_value=1)
    branch_id = serializers.IntegerField(min_value=1)


class ParticipationNotificationSerializer(ParticipationAccessSerializer):
    notification_id = serializers.IntegerField(min_value=1)


class ParticipationManagedSerializer(ParticipationListSerializer):
    branch_id = serializers.IntegerField(min_value=1)
    patient_id = serializers.IntegerField(min_value=1, required=False)
    state = serializers.ChoiceField(choices=TreatmentParticipation.States.values, required=False)


class ParticipationCandidatesSerializer(ParticipationScopeSerializer):
    branch_id = serializers.IntegerField(min_value=1)
    source_appointment_id = serializers.IntegerField(required=False, min_value=1)
    source_participation_id = serializers.IntegerField(required=False, min_value=1)
    after_member_id = serializers.IntegerField(required=False, min_value=1)
    limit = serializers.IntegerField(min_value=1, max_value=50, required=False, default=20)
    query = serializers.CharField(required=False, allow_blank=True, max_length=100)


class ParticipationResponsibleSerializer(ParticipationScopeSerializer):
    after_member_id = serializers.IntegerField(required=False, min_value=1)
    limit = serializers.IntegerField(min_value=1, max_value=50, required=False, default=20)
    query = serializers.CharField(required=False, allow_blank=True, max_length=100)


class ParticipationSourceSerializer(ParticipationScopeSerializer):
    source_appointment_id = serializers.IntegerField(required=False, min_value=1)
    source_participation_id = serializers.IntegerField(required=False, min_value=1)
    limit = serializers.IntegerField(min_value=1, max_value=50, required=False, default=20)


class ParticipationBranchesSerializer(ParticipationSourceSerializer):
    after_branch_id = serializers.IntegerField(required=False, min_value=1)


class ParticipationOutgoingSerializer(ParticipationSourceSerializer):
    before_id = serializers.IntegerField(required=False, min_value=1)


class TreatmentParticipationViewSet(viewsets.GenericViewSet):
    permission_classes = [IsAuthenticated]
    lookup_value_regex = r"[0-9]+"
    http_method_names = ["get", "post", "options"]

    def get_serializer_class(self):
        return {"create": ParticipationProposalSerializer, "respond": ParticipationResponseSerializer,
                "withdraw": ParticipationCommandSerializer, "end_by_head": ParticipationHeadEndSerializer,
                "end_own": ParticipationCommandSerializer,
                "closure": ParticipationClosureSerializer,
                "invitations": ParticipationListSerializer, "managed": ParticipationManagedSerializer,
                "mine": ParticipationListSerializer, "workspace_access": ParticipationAccessSerializer,
                "patient_context": ParticipationPatientContextSerializer,
                "notification_context": ParticipationNotificationSerializer,
                "proposal_branches": ParticipationBranchesSerializer,
                "outgoing": ParticipationOutgoingSerializer,
                "candidates": ParticipationCandidatesSerializer,
                "responsible_candidates": ParticipationResponsibleSerializer}.get(
                    self.action, ParticipationScopeSerializer)

    def finalize_response(self, request, response, *args, **kwargs):
        response = super().finalize_response(request, response, *args, **kwargs)
        response["Cache-Control"] = "no-store, private"
        response["Pragma"] = "no-cache"
        return response

    def _command(self, request, service, *, pk=None, created=False):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        identity = {"participation_id": int(pk)} if pk is not None else {}
        try:
            item, replayed = service(actor=request.user, **serializer.validated_data, **identity,
                idempotency_key=request.headers.get("Idempotency-Key"))
        except PermissionDenied:
            if self.action == "end_own":
                from .file_audit import record_denied_file_access
                record_denied_file_access(actor=request.user, business_id=serializer.validated_data["business_id"])
            raise
        return Response({"id": item.pk, "state": item.state, "revision": item.revision, "replayed": replayed},
            status=201 if created and not replayed else 200)

    def create(self, request):
        return self._command(request, propose_treatment_participation, created=True)

    @action(detail=False, methods=["get"])
    def candidates(self, request):
        serializer = self.get_serializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        return Response(read_proposal_candidates(actor=request.user, **serializer.validated_data))

    @action(detail=False, methods=["get"], url_path="proposal-branches")
    def proposal_branches(self, request):
        serializer = self.get_serializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        return Response(read_proposal_branches(actor=request.user, **serializer.validated_data))

    @action(detail=False, methods=["get"])
    def outgoing(self, request):
        serializer = self.get_serializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        return Response(read_outgoing_proposals(actor=request.user, **serializer.validated_data))

    @action(detail=True, methods=["get"], url_path="responsible-candidates")
    def responsible_candidates(self, request, pk=None):
        serializer = self.get_serializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        return Response(read_responsible_candidates(actor=request.user, participation_id=int(pk),
                                                   **serializer.validated_data))

    @action(detail=False, methods=["get"])
    def invitations(self, request):
        serializer = self.get_serializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        return Response(read_participation_invitations(actor=request.user, **serializer.validated_data))

    @action(detail=False, methods=["get"], url_path="workspace-access")
    def workspace_access(self, request):
        serializer = self.get_serializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        return Response(read_participation_workspace_access(actor=request.user, **serializer.validated_data))

    @action(detail=False, methods=["get"], url_path="patient-context")
    def patient_context(self, request):
        serializer = self.get_serializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        return Response(read_participation_patient_context(actor=request.user, **serializer.validated_data))

    @action(detail=False, methods=["get"], url_path="notification-context")
    def notification_context(self, request):
        serializer = self.get_serializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        return Response(read_participation_notification(actor=request.user, **serializer.validated_data))

    @action(detail=False, methods=["get"])
    def mine(self, request):
        serializer = self.get_serializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        return Response(read_own_participations(actor=request.user, **serializer.validated_data))

    @action(detail=False, methods=["get"])
    def managed(self, request):
        serializer = self.get_serializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        return Response(read_managed_participations(actor=request.user, **serializer.validated_data))

    @action(detail=True, methods=["post"])
    def respond(self, request, pk=None):
        return self._command(request, respond_treatment_participation, pk=pk)

    @action(detail=True, methods=["post"])
    def withdraw(self, request, pk=None):
        return self._command(request, withdraw_treatment_participation, pk=pk)

    @action(detail=True, methods=["post"], url_path="end-by-head")
    def end_by_head(self, request, pk=None):
        return self._command(request, end_participation_by_head, pk=pk)

    @action(detail=True, methods=["get"], url_path="closure")
    def closure(self, request, pk=None):
        serializer = self.get_serializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        try:
            return Response(read_participation_closure(actor=request.user, participation_id=int(pk), **serializer.validated_data))
        except PermissionDenied:
            from .file_audit import record_denied_file_access
            record_denied_file_access(actor=request.user, business_id=serializer.validated_data["business_id"])
            raise

    @action(detail=True, methods=["post"], url_path="end-own")
    def end_own(self, request, pk=None):
        return self._command(request, end_own_participation, pk=pk)
