from rest_framework import serializers, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import NotFound, PermissionDenied
from rest_framework.response import Response

from .assistant_documents import preview_assistant_document_template, read_assistant_document_draft
from .assistant_invitations import invite_appointment_assistant, accept_appointment_assistant, revoke_appointment_assistant
from .assistant_selectors import list_assistant_candidates, list_appointment_assistants, list_my_assistant_invitations
from .assistant_workspace import read_assistant_workspace, list_assistant_drafts, list_assistant_templates
from .document_services import save_primary_document_draft
from .document_views import DocumentDraftSerializer
from .file_audit import record_denied_file_access as record_denied_document_access
from .serializers import StrictSerializer


class AssistantInviteSerializer(StrictSerializer):
    business_id = serializers.IntegerField(min_value=1)
    patient_id = serializers.IntegerField(min_value=1)
    appointment_id = serializers.IntegerField(min_value=1)
    target_member_id = serializers.IntegerField(min_value=1)
    expected_updated_at = serializers.DateTimeField()


class AssistantCommandSerializer(StrictSerializer):
    business_id = serializers.IntegerField(min_value=1)
    expected_revision = serializers.IntegerField(min_value=1)


class AssistantBusinessSerializer(StrictSerializer):
    business_id = serializers.IntegerField(min_value=1)


class AssistantListSerializer(AssistantBusinessSerializer):
    before_id = serializers.IntegerField(min_value=1, required=False)
    limit = serializers.IntegerField(min_value=1, max_value=50, required=False, default=20)


class AssistantManagedSerializer(AssistantListSerializer):
    patient_id = serializers.IntegerField(min_value=1)
    appointment_id = serializers.IntegerField(min_value=1)


class AssistantCandidatesSerializer(AssistantManagedSerializer):
    query = serializers.CharField(max_length=100, required=False, allow_blank=True)


class AssistantDocumentScopeSerializer(StrictSerializer):
    business_id = serializers.IntegerField(min_value=1)
    patient_id = serializers.IntegerField(min_value=1)
    encounter_id = serializers.IntegerField(min_value=1)


class AssistantDocumentReadSerializer(AssistantDocumentScopeSerializer):
    document_id = serializers.IntegerField(min_value=1)


class AssistantDocumentPreviewSerializer(AssistantDocumentScopeSerializer):
    template_version_id = serializers.IntegerField(min_value=1)
    document_id = serializers.IntegerField(min_value=1, required=False)


class AssistantDocumentSaveSerializer(DocumentDraftSerializer):
    participation_id = None
    document_id = serializers.IntegerField(min_value=1, required=False)
    expected_document_revision = serializers.IntegerField(min_value=1, required=False)


class AppointmentAssistantViewSet(viewsets.GenericViewSet):
    permission_classes = [IsAuthenticated]
    lookup_value_regex = r"[0-9]+"
    http_method_names = ["get", "post", "head", "options"]
    serializer_class = AssistantCommandSerializer

    def get_serializer_class(self):
        return {"create": AssistantInviteSerializer, "document": AssistantDocumentReadSerializer,
                "preview": AssistantDocumentPreviewSerializer, "save_document": AssistantDocumentSaveSerializer,
                "mine": AssistantListSerializer, "managed": AssistantManagedSerializer,
                "candidates": AssistantCandidatesSerializer, "workspace": AssistantBusinessSerializer,
                "drafts": AssistantListSerializer, "templates": AssistantListSerializer}.get(
                    self.action, AssistantCommandSerializer)

    def finalize_response(self, request, response, *args, **kwargs):
        response = super().finalize_response(request, response, *args, **kwargs)
        response["Cache-Control"] = "no-store, private"
        response["Pragma"] = "no-cache"
        return response

    def _command(self, request, service, **identity):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        item, replayed = service(actor=request.user, **identity, **serializer.validated_data,
            idempotency_key=request.headers.get("Idempotency-Key"))
        return Response({"id": item.pk, "state": item.state, "revision": item.revision, "replayed": replayed},
                        status=201 if self.action == "create" and not replayed else 200)

    def create(self, request):
        return self._command(request, invite_appointment_assistant)

    @action(detail=True, methods=["post"])
    def accept(self, request, pk=None):
        return self._command(request, accept_appointment_assistant, invitation_id=int(pk))

    @action(detail=True, methods=["post"])
    def revoke(self, request, pk=None):
        return self._command(request, revoke_appointment_assistant, invitation_id=int(pk))

    def _read(self, request, pk, service):
        serializer = self.get_serializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        try:
            identity = {"invitation_id": int(pk)} if pk is not None else {}
            return Response(service(actor=request.user, **identity, **serializer.validated_data))
        except (NotFound, PermissionDenied):
            record_denied_document_access(actor=request.user, business_id=serializer.validated_data["business_id"])
            raise

    @action(detail=False, methods=["get"])
    def mine(self, request):
        return self._read(request, None, list_my_assistant_invitations)

    @action(detail=False, methods=["get"])
    def candidates(self, request):
        return self._read(request, None, list_assistant_candidates)

    @action(detail=False, methods=["get"])
    def managed(self, request):
        return self._read(request, None, list_appointment_assistants)

    @action(detail=True, methods=["get"])
    def workspace(self, request, pk=None):
        return self._read(request, pk, read_assistant_workspace)

    @action(detail=True, methods=["get"])
    def drafts(self, request, pk=None):
        return self._read(request, pk, list_assistant_drafts)

    @action(detail=True, methods=["get"])
    def templates(self, request, pk=None):
        return self._read(request, pk, list_assistant_templates)

    @action(detail=True, methods=["get"])
    def document(self, request, pk=None):
        return self._read(request, pk, read_assistant_document_draft)

    @action(detail=True, methods=["get"])
    def preview(self, request, pk=None):
        return self._read(request, pk, preview_assistant_document_template)

    @action(detail=True, methods=["post"], url_path="save-document")
    def save_document(self, request, pk=None):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        version, replayed = save_primary_document_draft(actor=request.user, assistant_invitation_id=int(pk),
            **serializer.validated_data, idempotency_key=request.headers.get("Idempotency-Key"))
        return Response({"id": version.document_id, "version_id": version.pk, "revision": version.revision,
                         "replayed": replayed}, status=201 if "document_id" not in serializer.validated_data and not replayed else 200)
