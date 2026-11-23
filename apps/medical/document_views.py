from django.http import HttpResponse
from rest_framework import serializers, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.exceptions import NotFound, PermissionDenied

from .document_reads import document_workspace_access, list_document_revisions, list_patient_documents
from .document_previews import preview_document_template
from .document_services import read_document_for_treating_clinician, save_primary_document_draft
from .serializers import StrictSerializer
from .document_artifact_services import prepare_document_draft_pdf, read_document_draft_pdf
from .document_export_history import list_document_export_history
from .document_review_services import read_document_review, transition_document_review
from .file_audit import record_denied_file_access as record_denied_document_access


class DocumentScopeSerializer(StrictSerializer):
    business_id = serializers.IntegerField(min_value=1)
    patient_id = serializers.IntegerField(min_value=1)


class DocumentReadSerializer(DocumentScopeSerializer):
    appointment_id = serializers.IntegerField(min_value=1, required=False)
    participation_id = serializers.IntegerField(min_value=1, required=False)


class DocumentScopedReadSerializer(DocumentReadSerializer):
    head_branch_id = serializers.IntegerField(min_value=1, required=False)


class DocumentArtifactSerializer(DocumentScopedReadSerializer):
    correction_access_id = serializers.IntegerField(min_value=1, required=False)
    language = serializers.ChoiceField(choices=("ru", "kk", "en"))


class DocumentExportHistorySerializer(DocumentScopedReadSerializer):
    correction_access_id = serializers.IntegerField(min_value=1, required=False)
    before_id = serializers.IntegerField(min_value=1, required=False)
    limit = serializers.IntegerField(min_value=1, max_value=50, required=False, default=20)


class DocumentReviewTransitionSerializer(DocumentReadSerializer):
    expected_state_revision = serializers.IntegerField(min_value=1)
    target = serializers.ChoiceField(choices=("draft", "ready_for_review", "reviewed"))
    reason = serializers.CharField(max_length=2000, allow_blank=True, trim_whitespace=False, default="")


class DocumentListSerializer(DocumentScopedReadSerializer):
    encounter_id = serializers.IntegerField(min_value=1, required=False)
    before_id = serializers.IntegerField(min_value=1, required=False)
    limit = serializers.IntegerField(min_value=1, max_value=50, required=False, default=20)


class DocumentHistorySerializer(DocumentScopedReadSerializer):
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
                "workspace_access": DocumentAccessSerializer, "preview": DocumentPreviewSerializer,
                "prepare_pdf": DocumentArtifactSerializer, "pdf": DocumentArtifactSerializer,
                "export_pdf": DocumentArtifactSerializer, "print_pdf": DocumentArtifactSerializer,
                "export_history": DocumentExportHistorySerializer,
                "review_state": DocumentExportHistorySerializer,
                "review_transition": DocumentReviewTransitionSerializer}.get(
                    self.action, DocumentScopedReadSerializer)

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

    @action(detail=False, methods=["get"], url_path=r"versions/(?P<version_id>[0-9]+)/review")
    def review_state(self, request, version_id=None):
        serializer = self.get_serializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        try:
            return Response(read_document_review(actor=request.user, version_id=int(version_id), **serializer.validated_data))
        except (NotFound, PermissionDenied):
            record_denied_document_access(actor=request.user, business_id=serializer.validated_data["business_id"])
            raise

    @action(detail=False, methods=["post"], url_path=r"versions/(?P<version_id>[0-9]+)/review-transition")
    def review_transition(self, request, version_id=None):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            item, replayed = transition_document_review(actor=request.user, version_id=int(version_id),
                idempotency_key=request.headers.get("Idempotency-Key"), **serializer.validated_data)
        except (NotFound, PermissionDenied):
            record_denied_document_access(actor=request.user, business_id=serializer.validated_data["business_id"])
            raise
        return Response({"id": item.pk, "version_id": item.version_id, "state": item.state,
                         "state_revision": item.state_revision, "replayed": replayed})

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

    def _artifact(self, request, version_id, *, prepare, purpose="preview"):
        serializer = self.get_serializer(data=request.data if request.method == "POST" else request.query_params)
        serializer.is_valid(raise_exception=True)
        scope = serializer.validated_data
        try:
            if prepare:
                item, replayed = prepare_document_draft_pdf(actor=request.user, version_id=int(version_id), **scope)
                from .document_artifact_access import document_artifact_can_export
                can_export = document_artifact_can_export(actor=request.user, version_id=int(version_id),
                    **{key: value for key, value in scope.items() if key != "language"})
                return Response({"artifact_id": item.pk, "version_id": item.version_id, "language": item.language,
                    "scan_status": item.attachment.scan_status, "replayed": replayed,
                    "can_export": can_export}, status=200 if replayed else 201)
            content = read_document_draft_pdf(actor=request.user, version_id=int(version_id), purpose=purpose, **scope)
        except (NotFound, PermissionDenied):
            record_denied_document_access(actor=request.user, business_id=scope["business_id"])
            raise
        response = HttpResponse(content, content_type="application/pdf")
        disposition = "attachment" if purpose == "download" else "inline"
        response["Content-Disposition"] = f'{disposition}; filename="document.pdf"'
        response["X-Content-Type-Options"] = "nosniff"
        response["Content-Security-Policy"] = "default-src 'none'; sandbox"
        return response

    @action(detail=False, methods=["post"], url_path=r"versions/(?P<version_id>[0-9]+)/pdf-prepare")
    def prepare_pdf(self, request, version_id=None):
        return self._artifact(request, version_id, prepare=True)

    @action(detail=False, methods=["get"], url_path=r"versions/(?P<version_id>[0-9]+)/pdf")
    def pdf(self, request, version_id=None):
        return self._artifact(request, version_id, prepare=False)

    @action(detail=False, methods=["post"], url_path=r"versions/(?P<version_id>[0-9]+)/pdf-download")
    def export_pdf(self, request, version_id=None):
        return self._artifact(request, version_id, prepare=False, purpose="download")

    @action(detail=False, methods=["post"], url_path=r"versions/(?P<version_id>[0-9]+)/pdf-print")
    def print_pdf(self, request, version_id=None):
        return self._artifact(request, version_id, prepare=False, purpose="print")

    @action(detail=False, methods=["get"], url_path=r"versions/(?P<version_id>[0-9]+)/export-history")
    def export_history(self, request, version_id=None):
        serializer = self.get_serializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        try:
            return Response(list_document_export_history(actor=request.user, version_id=int(version_id),
                **serializer.validated_data))
        except (NotFound, PermissionDenied):
            record_denied_document_access(actor=request.user, business_id=serializer.validated_data["business_id"])
            raise
