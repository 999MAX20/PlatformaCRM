from django.http import FileResponse
from rest_framework import serializers, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import NotFound, PermissionDenied
from rest_framework.parsers import JSONParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .file_reads import list_medical_files, list_medical_file_history, read_medical_file_version, medical_file_workspace_access
from .file_audit import record_denied_file_access
from .audit import MedicalAuditUnavailable
from .file_services import update_medical_file_metadata, upload_medical_file
from .file_upload_handler import MedicalMemoryUploadHandler
from .serializers import StrictSerializer


class MedicalFileScopeSerializer(StrictSerializer):
    business_id = serializers.IntegerField(min_value=1)
    patient_id = serializers.IntegerField(min_value=1)
    appointment_id = serializers.IntegerField(min_value=1, required=False)
    participation_id = serializers.IntegerField(min_value=1, required=False)
    correction_access_id = serializers.IntegerField(min_value=1, required=False)
    head_branch_id = serializers.IntegerField(min_value=1, required=False)


class MedicalFileListSerializer(MedicalFileScopeSerializer):
    before_id = serializers.IntegerField(min_value=1, required=False)
    limit = serializers.IntegerField(min_value=1, max_value=50, required=False, default=20)
    tooth = serializers.IntegerField(min_value=1, required=False)
    encounter_id = serializers.IntegerField(min_value=1, required=False)


class MedicalFileReadSerializer(MedicalFileScopeSerializer):
    version_id = serializers.IntegerField(min_value=1, required=False)


class MedicalFileWorkspaceSerializer(MedicalFileScopeSerializer):
    record_id = serializers.IntegerField(min_value=1, required=False)
    encounter_id = serializers.IntegerField(min_value=1, required=False)


class MedicalFileHistorySerializer(MedicalFileScopeSerializer):
    before_revision = serializers.IntegerField(min_value=1, required=False)
    limit = serializers.IntegerField(min_value=1, max_value=50, required=False, default=20)


class MedicalFileUploadSerializer(MedicalFileScopeSerializer):
    file = serializers.FileField()
    record_id = serializers.IntegerField(min_value=1)
    encounter_id = serializers.IntegerField(min_value=1, required=False)
    expected_patient_revision = serializers.IntegerField(min_value=1)
    description = serializers.CharField(max_length=4000, allow_blank=True, required=False, default="", trim_whitespace=False)
    teeth = serializers.ListField(child=serializers.IntegerField(min_value=1), max_length=52, required=False, default=list)
    reason = serializers.CharField(max_length=2000, allow_blank=True, required=False, default="", trim_whitespace=False)


class MedicalFileMetadataSerializer(MedicalFileScopeSerializer):
    expected_revision = serializers.IntegerField(min_value=1)
    description = serializers.CharField(max_length=4000, allow_blank=True, trim_whitespace=False)
    teeth = serializers.ListField(child=serializers.IntegerField(min_value=1), max_length=52)
    reason = serializers.CharField(max_length=2000, trim_whitespace=False)


class MedicalFileViewSet(viewsets.GenericViewSet):
    permission_classes = [IsAuthenticated]
    parser_classes = [JSONParser, MultiPartParser]
    lookup_value_regex = r"[0-9]+"
    http_method_names = ["get", "post", "head", "options"]

    def initialize_request(self, request, *args, **kwargs):
        request.upload_handlers = [MedicalMemoryUploadHandler(request)]
        return super().initialize_request(request, *args, **kwargs)

    def get_serializer_class(self):
        return {"list": MedicalFileListSerializer, "create": MedicalFileUploadSerializer,
                "workspace_access": MedicalFileWorkspaceSerializer,
                "revisions": MedicalFileHistorySerializer, "metadata": MedicalFileMetadataSerializer}.get(
                    self.action, MedicalFileReadSerializer)

    def finalize_response(self, request, response, *args, **kwargs):
        response = super().finalize_response(request, response, *args, **kwargs)
        response["Cache-Control"] = "no-store, private"
        response["Pragma"] = "no-cache"
        response["X-Content-Type-Options"] = "nosniff"
        response["Content-Security-Policy"] = "default-src 'none'; sandbox"
        return response

    def validated(self, request, *, write=False):
        serializer = self.get_serializer(data=request.data if write else request.query_params)
        serializer.is_valid(raise_exception=True)
        self.audit_business_id = serializer.validated_data["business_id"]
        return serializer.validated_data

    def handle_exception(self, exc):
        if isinstance(exc, (PermissionDenied, NotFound)) and getattr(self, "audit_business_id", None):
            try:
                record_denied_file_access(actor=self.request.user, business_id=self.audit_business_id)
            except MedicalAuditUnavailable as failure:
                exc = failure
        return super().handle_exception(exc)

    def list(self, request):
        return Response(list_medical_files(actor=request.user, **self.validated(request)))

    @action(detail=False, methods=["get"], url_path="workspace-access")
    def workspace_access(self, request):
        return Response(medical_file_workspace_access(actor=request.user, **self.validated(request)))

    def create(self, request):
        data = self.validated(request, write=True)
        version, replayed = upload_medical_file(actor=request.user, uploaded_file=data.pop("file"),
            **data, idempotency_key=request.headers.get("Idempotency-Key"))
        return self.command_response(version, replayed, created=True)

    @staticmethod
    def command_response(version, replayed, *, created=False):
        return Response({"id": version.medical_file_id, "version_id": version.pk,
                         "revision": version.revision, "replayed": replayed},
                        status=201 if created and not replayed else 200)

    def retrieve(self, request, pk=None):
        payload, _ = read_medical_file_version(actor=request.user, file_id=int(pk), **self.validated(request))
        return Response(payload)

    @action(detail=True, methods=["get"])
    def revisions(self, request, pk=None):
        return Response(list_medical_file_history(actor=request.user, file_id=int(pk), **self.validated(request)))

    @action(detail=True, methods=["post"])
    def metadata(self, request, pk=None):
        version, replayed = update_medical_file_metadata(actor=request.user, file_id=int(pk),
            **self.validated(request, write=True), idempotency_key=request.headers.get("Idempotency-Key"))
        return self.command_response(version, replayed)

    def file_response(self, request, pk, *, download):
        payload, source = read_medical_file_version(actor=request.user, file_id=int(pk), download=download,
            preview=not download, **self.validated(request))
        try:
            return FileResponse(source, as_attachment=download, filename=payload["name"],
                                content_type=payload["content_type"])
        except Exception:
            source.close()
            raise

    @action(detail=True, methods=["get"])
    def preview(self, request, pk=None):
        return self.file_response(request, pk, download=False)

    @action(detail=True, methods=["get"])
    def download(self, request, pk=None):
        return self.file_response(request, pk, download=True)
