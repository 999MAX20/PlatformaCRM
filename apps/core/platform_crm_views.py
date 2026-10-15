"""Clinic-bound, audited platform reads. No merchant write permissions are changed."""
from django.db import DatabaseError, transaction
from django.shortcuts import get_object_or_404
from rest_framework.decorators import api_view, permission_classes
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response

from apps.core.audit import write_audit_log
from apps.core.models import AuditLog
from apps.core.permissions import IsPlatformUser
from apps.core.platform_crm_selectors import (
    ClinicReadFilters, clinic_access, clinic_queryset, clinic_records, clinic_user_ids, record_projection,
)
from apps.core.platform_crm_children import child_sections, child_records, child_projection


def audited_response(request, business_id, kind, read, *, record_id=None):
    business = clinic_access(request.user, business_id)
    try:
        with transaction.atomic():
            payload = read(business)
            write_audit_log(request, AuditLog.Actions.SUPPORT_ACCESS, business, business=business,
                            metadata={"kind": "platform_crm_read", "resource": kind, "record_id": record_id,
                                      "category": AuditLog.Categories.ACCESS})
    except DatabaseError:
        # A failed audit must not return private data, even when the SELECT worked.
        return Response({"detail": "Business records are temporarily unavailable.", "code": "temporary_service_failure", "category": "temporary"}, status=503, headers={"Cache-Control": "no-store"})
    return Response(payload, headers={"Cache-Control": "no-store"})


@api_view(["GET"])
@permission_classes([IsPlatformUser])
def platform_clinic_records(request, business_id, kind):
    serializer = ClinicReadFilters(data=request.query_params)
    serializer.is_valid(raise_exception=True)
    params = serializer.validated_data
    def read(business):
        paginator = PageNumberPagination()
        paginator.page_size = params["page_size"]
        rows = paginator.paginate_queryset(clinic_records(business, kind, params), request)
        users = clinic_user_ids(business)
        data = paginator.get_paginated_response([record_projection(row, kind, users) for row in rows]).data
        return {**data, "business": {"id": business.pk, "name": business.name, "timezone": business.timezone}, "kind": kind}
    return audited_response(request, business_id, kind, read)


@api_view(["GET"])
@permission_classes([IsPlatformUser])
def platform_clinic_record(request, business_id, kind, record_id):
    def read(business):
        row = get_object_or_404(clinic_queryset(business, kind), pk=record_id)
        return {**record_projection(row, kind, clinic_user_ids(business), detail=True),
                "sections": child_sections(kind),
                "business": {"id": business.pk, "name": business.name, "timezone": business.timezone}}
    return audited_response(request, business_id, kind, read, record_id=record_id)


@api_view(["GET"])
@permission_classes([IsPlatformUser])
def platform_clinic_record_section(request, business_id, kind, record_id, section):
    filters = ClinicReadFilters(data=request.query_params)
    filters.is_valid(raise_exception=True)
    def read(business):
        record = get_object_or_404(clinic_queryset(business, kind), pk=record_id)
        paginator = PageNumberPagination()
        paginator.page_size = filters.validated_data["page_size"]
        rows = paginator.paginate_queryset(child_records(business, kind, record, section), request)
        users = clinic_user_ids(business)
        return paginator.get_paginated_response([child_projection(row, section, users) for row in rows]).data
    return audited_response(request, business_id, f"{kind}/{section}", read, record_id=record_id)


@api_view(["GET"])
@permission_classes([IsPlatformUser])
def platform_clinic_access_log(request, business_id):
    filters = ClinicReadFilters(data=request.query_params)
    filters.is_valid(raise_exception=True)
    def read(business):
        paginator = PageNumberPagination()
        paginator.page_size = filters.validated_data["page_size"]
        rows = AuditLog.objects.filter(business=business, metadata__kind__in=["platform_crm_read", "platform_business_details"]).select_related("actor").order_by("-created_at", "-pk")
        page = paginator.paginate_queryset(rows, request)
        return paginator.get_paginated_response([
            {"id": row.pk, "created_at": row.created_at, "actor": (row.actor.full_name or row.actor.email) if row.actor else None,
             "resource": row.metadata.get("resource", "business_details"), "record_id": row.metadata.get("record_id"),
             **({"correction": {key: row.metadata.get(key) for key in ("support_case_id", "changed_fields", "reason")}}
                if row.metadata.get("kind") == "platform_business_details" else {})}
            for row in page
        ]).data
    return audited_response(request, business_id, "access_log", read)
