from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from rest_framework import status
from rest_framework.viewsets import ReadOnlyModelViewSet
from django.conf import settings
from django.http import FileResponse

from apps.businesses.access import Actions, Resources, assert_can, can_view_sensitive_field
from apps.clients.export_privacy import private_notes_redacted_csv
from apps.businesses.capabilities import assert_resource_enabled
from apps.core.audit import write_audit_log
from apps.core.import_export import (
    build_import_preview,
    confirm_import,
    create_manual_catalog_item,
    create_manual_sale,
    import_template_response,
    mark_excel_csv_import_failed,
    import_resource,
)
from apps.core.file_validation import validate_file_upload
from apps.core.export_jobs import request_entity_export
from apps.core.export_access import assert_export_download_access
from apps.core.models import AuditLog, ExportJob, ImportJob
from apps.core.permissions import accessible_businesses
from apps.core.sanitization import sanitize_error_text
from apps.core.serializers import ExportJobSerializer, ImportJobSerializer
from apps.core.viewsets import TenantModelViewSet
from apps.integrations.serializers import BusinessEventSerializer


class ImportErrorPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 100


class ImportJobViewSet(TenantModelViewSet):
    http_method_names = ["get", "post", "head", "options"]
    serializer_class = ImportJobSerializer
    queryset = ImportJob.objects.select_related("business", "actor")
    access_resource = Resources.CLIENTS

    def get_queryset(self):
        queryset = super().get_queryset()
        business_id = self.request.query_params.get("business")
        if business_id:
            queryset = queryset.filter(business_id=business_id)
        return queryset.filter(actor=self.request.user) if not self.request.user.is_platform_user else queryset

    def perform_create(self, serializer):
        business = serializer.validated_data["business"]
        entity_type = serializer.validated_data.get("entity_type", ImportJob.EntityTypes.CLIENTS)
        resource = _resource_for_entity(entity_type)
        assert_can(self.request.user, business, resource, Actions.CREATE)
        assert_resource_enabled(business, resource)
        upload = serializer.validated_data["source_file"]
        _validate_import_file(upload)
        job = serializer.save(actor=self.request.user, original_filename=getattr(upload, "name", ""))
        try:
            serializer.instance = build_import_preview(job, request=self.request)
        except Exception as exc:
            job.status = ImportJob.Statuses.FAILED
            job.error = sanitize_error_text(exc)
            job.save(update_fields=["status", "error", "updated_at"])
            mark_excel_csv_import_failed(job, exc)
            raise
        write_audit_log(
            self.request,
            AuditLog.Actions.CREATE,
            job,
            business=business,
            metadata={"kind": "import_uploaded", "entity_type": entity_type, "filename": job.original_filename},
        )

    @action(detail=True, methods=["post"])
    def preview(self, request, pk=None):
        job = self.get_object()
        if not isinstance(request.data, dict) or set(request.data) - {"mapping"}:
            raise ValidationError({"mapping": "Only column mapping can be changed through preview."})
        job = build_import_preview(job, mapping=request.data.get("mapping"), request=request)
        return Response(self.get_serializer(job).data)

    @action(detail=True, methods=["post"])
    def confirm(self, request, pk=None):
        job = self.get_object()
        job = confirm_import(job, request)
        return Response(self.get_serializer(job).data)

    @action(detail=True, methods=["get"])
    def errors(self, request, pk=None):
        job = self.get_object()
        paginator = ImportErrorPagination()
        rows = (job.errors_json or {}).get("rows") or []
        page = paginator.paginate_queryset(rows, request, view=self)
        return paginator.get_paginated_response(page)


class ExportJobViewSet(ReadOnlyModelViewSet):
    serializer_class = ExportJobSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = ExportJob.objects.select_related("business", "actor").filter(
            business__in=accessible_businesses(self.request.user)
        )
        if not self.request.user.is_platform_user:
            queryset = queryset.filter(actor=self.request.user)
        business_id = self.request.query_params.get("business")
        return queryset.filter(business_id=business_id) if business_id else queryset

    @action(detail=True, methods=["get"])
    def download(self, request, pk=None):
        job = self.get_object()
        if job.status != ExportJob.Statuses.SUCCEEDED or not job.result_file:
            raise ValidationError({"export": "Export file is not ready."})
        assert_can(request.user, job.business, _resource_for_export_key(job.export_key), Actions.VIEW)
        assert_export_download_access(job, request.user)
        write_audit_log(
            request,
            AuditLog.Actions.CREATE,
            job,
            business=job.business,
            metadata={"kind": "file_download", "entity_type": "export_job", "export_key": job.export_key},
        )
        if job.kind == ExportJob.Kinds.ENTITY and job.export_key == "clients" and not can_view_sensitive_field(
            job.actor, job.business, Resources.CLIENTS, "notes"
        ):
            return private_notes_redacted_csv(job.result_file)
        return FileResponse(job.result_file.open("rb"), as_attachment=True, filename=f"{job.export_key}.csv")

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def export_entity(request, entity_type):
    business_id = request.query_params.get("business")
    business = accessible_businesses(request.user).filter(id=business_id).first() if business_id else accessible_businesses(request.user).first()
    if business is None:
        raise PermissionDenied("Business is required.")
    resource = _resource_for_entity(entity_type)
    assert_can(request.user, business, resource, Actions.VIEW)
    response, job = request_entity_export(business=business, actor=request.user, export_key=entity_type)
    audit_target = job or business
    write_audit_log(
        request,
        AuditLog.Actions.CREATE,
        audit_target,
        business=business,
        metadata={"kind": "export", "entity_type": entity_type, "queued": bool(job)},
    )
    if job:
        return Response(ExportJobSerializer(job, context={"request": request}).data, status=status.HTTP_202_ACCEPTED)
    return response


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def import_template(request, entity_type):
    return import_template_response(entity_type)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def manual_sale(request):
    business = _resolve_business_for_write(request)
    assert_can(request.user, business, Resources.INTEGRATIONS, Actions.MANAGE)
    event = create_manual_sale(business, request.data, request)
    return Response(BusinessEventSerializer(event).data, status=201)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def manual_catalog_item(request):
    business = _resolve_business_for_write(request)
    assert_can(request.user, business, Resources.INTEGRATIONS, Actions.MANAGE)
    event = create_manual_catalog_item(business, request.data, request)
    return Response(BusinessEventSerializer(event).data, status=201)


def _resolve_business_for_write(request):
    business_id = request.data.get("business") or request.query_params.get("business")
    business = accessible_businesses(request.user).filter(id=business_id).first() if business_id else accessible_businesses(request.user).first()
    if business is None:
        raise PermissionDenied("Business is required.")
    return business


def _resource_for_entity(entity_type):
    return import_resource(entity_type)


def _resource_for_export_key(export_key):
    from apps.analytics.workspace_export import WORKSPACE_REPORTS

    if export_key in WORKSPACE_REPORTS:
        return Resources.ANALYTICS
    if export_key in {"source_roi", "manager_performance", "funnel_velocity", "retention_ltv"}:
        return Resources.ANALYTICS
    return _resource_for_entity(export_key)


def _validate_import_file(upload):
    validate_file_upload(
        upload,
        allowed_extensions=["csv", "xlsx"],
        allowed_content_types=[
            "text/csv",
            "application/csv",
            "application/vnd.ms-excel",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        ],
        max_size_mb=settings.MAX_UPLOAD_SIZE_MB,
    )
