"""Bounded administrative correction of existing business details (ADMIN-01)."""
import hashlib
import json

from django.contrib.auth import get_user_model
from django.db import transaction
from django.shortcuts import get_object_or_404
from rest_framework import serializers

from apps.accounts.mfa import validate_step_up_token
from apps.businesses.models import Business
from apps.core.audit import write_audit_log
from apps.core.models import AuditLog
from apps.core.domain_errors import DomainAPIException
from apps.support.access import assert_platform_actor
from apps.support.models import SupportCase


DETAIL_FIELDS = ("name", "legal_name", "tax_id", "city", "address", "phone",
                 "whatsapp", "telegram", "instagram", "invoice_email")


class StrictFieldsMixin:
    def to_internal_value(self, data):
        if isinstance(data, dict):
            unknown = set(data) - set(self.fields)
            if unknown:
                raise serializers.ValidationError({key: "Unknown field." for key in sorted(unknown)})
        return super().to_internal_value(data)


class DetailsChangesSerializer(StrictFieldsMixin, serializers.ModelSerializer):
    class Meta:
        model = Business
        fields = DETAIL_FIELDS
        extra_kwargs = {field: {"required": False} for field in DETAIL_FIELDS}

    def validate(self, attrs):
        if not attrs:
            raise serializers.ValidationError("Provide at least one detail to correct.")
        return attrs


class DetailsUpdateSerializer(StrictFieldsMixin, serializers.Serializer):
    changes = DetailsChangesSerializer()
    expected_revision = serializers.CharField(min_length=64, max_length=64)
    support_case_id = serializers.IntegerField(min_value=1, max_value=9223372036854775807)
    reason = serializers.CharField(max_length=2000)


class DetailsConflict(DomainAPIException):
    status_code = 409
    default_detail = "Business details changed. Reload them before saving again."
    error_code = "request_conflict"
    default_code = error_code
    category = "conflict"


def details_projection(business):
    details = {field: getattr(business, field) for field in DETAIL_FIELDS}
    # Includes merchant and other Business saves, not just this platform action.
    snapshot = {**details, "updated_at": business.updated_at.isoformat()}
    revision = hashlib.sha256(json.dumps(snapshot, sort_keys=True).encode()).hexdigest()
    return {"business_id": business.pk, "details": details, "revision": revision,
            "actions": {"update": True, "requires_mfa": True}}


@transaction.atomic
def correct_business_details(request, business_id, payload):
    # Reload identity: the authenticated instance can predate role/epoch revocation.
    actor = get_object_or_404(get_user_model(), pk=request.user.pk)
    assert_platform_actor(actor)
    validate_step_up_token(actor, request.headers.get("X-Zani-MFA-Step-Up", ""))
    serializer = DetailsUpdateSerializer(data=payload)
    serializer.is_valid(raise_exception=True)
    data = serializer.validated_data
    business = get_object_or_404(Business.objects.select_for_update(), pk=business_id)
    get_object_or_404(SupportCase, pk=data["support_case_id"], business=business)
    if details_projection(business)["revision"] != data["expected_revision"]:
        raise DetailsConflict()
    changes = {key: value for key, value in data["changes"].items() if getattr(business, key) != value}
    if not changes:
        raise serializers.ValidationError({"changes": "No details have changed."})
    for key, value in changes.items():
        setattr(business, key, value)
    business.save(update_fields=[*changes, "updated_at"])
    write_audit_log(request, AuditLog.Actions.UPDATE, business, business=business, metadata={
        "kind": "platform_business_details", "support_case_id": data["support_case_id"],
        "changed_fields": sorted(changes), "reason": data["reason"], "result": "updated",
        "category": AuditLog.Categories.DATA, "risk_level": AuditLog.RiskLevels.HIGH,
    })
    return details_projection(business)
