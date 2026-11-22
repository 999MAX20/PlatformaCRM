from rest_framework import serializers, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .document_reads import document_workspace_access, list_document_revisions, list_patient_documents
from .document_previews import preview_document_template
from .document_services import read_document_for_treating_clinician, save_primary_document_draft
from .serializers import StrictSerializer


class DocumentScopeSerializer(StrictSerializer):
    business_id = serializers.IntegerField(min_value=1)
    patient_id = serializers.IntegerField(min_value=1)


class DocumentReadSerializer(DocumentScopeSerializer):
    appointment_id = serializers.IntegerField(min_value=1, required=False)
    participation_id = serializers.IntegerField(min_value=1, required=False)


class DocumentListSerializer(DocumentReadSerializer):
    encounter_id = serializers.IntegerField(min_value=1, required=False)
    before_id = serializers.IntegerField(min_value=1, required=False)
    limit = serializers.IntegerField(min_value=1, max_value=50, required=False, default=20)


class DocumentHistorySerializer(DocumentReadSerializer):
    before_revision = serializers.IntegerField(min_value=1, required=False)
    limit = serializers.IntegerField(min_value=1, max_value=50, required=False, default=20)


class DocumentAccessSerializer(DocumentReadSerializer):
    encounter_id = serializers.IntegerField(min_value=1)


class DocumentPreviewSerializer(DocumentAccessSerializer):
    template_version_id = serializers.IntegerField(min_value=1)
    document_id = serializers.IntegerField(min_value=1, required=False)


class DocumentDraftSerializer(DocumentScopeSerializer):
    encounter_id = serializers.IntegerField(min_value=1)
    expected_encounter_revision = serializers.IntegerField(min_value=1)
    expected_patient_revision = serializers.IntegerField(min_value=1)
    template_version_id = serializers.IntegerField(min_value=1)
    document_text = serializers.CharField(max_length=131072, allow_blank=True, trim_whitespace=False)
    reason = serializers.CharField(max_length=2000, allow_blank=True, required=False, trim_whitespace=False)
    participation_id = serializers.IntegerField(min_value=1, required=False)
    expected_source_digest = serializers.RegexField(r"\A[a-f0-9]{64}\Z", required=False, trim_whitespace=False)


class DocumentUpdateSerializer(DocumentDraftSerializer):
    expected_document_revision = serializers.IntegerField(min_value=1)


class MedicalDocumentViewSet(viewsets.GenericViewSet):
    permission_classes = [IsAuthenticated]
    lookup_value_regex = r"[0-9]+"
    serializer_class = DocumentReadSerializer
    http_method_names = ["get", "post", "head", "options"]

    def get_serializer_class(self):
        return {"create": DocumentDraftSerializer, "draft": DocumentUpdateSerializer,
                "list": DocumentListSerializer, "revisions": DocumentHistorySerializer,
                "workspace_access": DocumentAccessSerializer, "preview": DocumentPreviewSerializer}.get(
                    self.action, DocumentReadSerializer)

    def finalize_response(self, request, response, *args, **kwargs):
        response = super().finalize_response(request, response, *args, **kwargs)
        response["Cache-Control"] = "no-store, private"
        response["Pragma"] = "no-cache"
        return response

    def _read(self, request, service, **identity):
        serializer = self.get_serializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        return Response(service(actor=request.user, **identity, **serializer.validated_data))

    def _command(self, request, document_id=None):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        version, replayed = save_primary_document_draft(actor=request.user, document_id=document_id,
            **serializer.validated_data, idempotency_key=request.headers.get("Idempotency-Key"))
        return Response({"id": version.document_id, "version_id": version.pk,
                         "revision": version.revision, "replayed": replayed},
                        status=201 if document_id is None and not replayed else 200)

    def create(self, request):
        return self._command(request)

    def list(self, request):
        return self._read(request, list_patient_documents)

    @action(detail=False, methods=["get"], url_path="workspace-access")
    def workspace_access(self, request):
        return self._read(request, document_workspace_access)

    @action(detail=False, methods=["get"])
    def preview(self, request):
        return self._read(request, preview_document_template)

    @action(detail=True, methods=["post"])
    def draft(self, request, pk=None):
        return self._command(request, document_id=int(pk))

    @action(detail=True, methods=["get"])
    def revisions(self, request, pk=None):
        return self._read(request, list_document_revisions, document_id=int(pk))

    @action(detail=False, methods=["get"], url_path=r"versions/(?P<version_id>[0-9]+)")
    def version(self, request, version_id=None):
        return self._read(request, read_document_for_treating_clinician, version_id=int(version_id))
