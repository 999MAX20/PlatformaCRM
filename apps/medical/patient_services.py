import json
from datetime import date
from zoneinfo import ZoneInfo

from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import NotFound, PermissionDenied, ValidationError

from apps.branches.models import Branch
from apps.businesses.access import Actions, Resources, assert_can
from apps.businesses.models import Business
from apps.clients.models import Client
from apps.core.domain_errors import InvalidTransition
from apps.core.idempotency import CRMCommandResult, run_idempotent_crm_command
from .audit import write_patient_audit
from .identity_crypto import encrypt_medical_value, iin_digest, medical_request_digest, normalize_iin
from .identity_history import retain_identity_revision
from .models import MedicalAuditEvent, PatientProfile
from .role_access import assert_medical_branch_permission


def _demographics(values, business):
    if not isinstance(values, dict) or set(values) - {"date_of_birth", "sex", "address"}:
        raise ValidationError({"demographics": "Provide only supported administrative fields."})
    result = {}
    for key, value in values.items():
        if value is None or value == "":
            continue
        if not isinstance(value, str) or len(value) > {"date_of_birth": 10, "sex": 32, "address": 2000}[key]:
            raise ValidationError({key: "Invalid administrative field."})
        if key == "date_of_birth":
            try:
                parsed = date.fromisoformat(value)
                if parsed.isoformat() != value or parsed > timezone.now().astimezone(ZoneInfo(business.timezone)).date():
                    raise ValueError
            except ValueError:
                raise ValidationError({key: "Provide a valid birth date."}) from None
        result[key] = value
    return result


@transaction.atomic
def create_patient_profile(*, actor, business_id, client_id, branch_id, demographics, iin=None, idempotency_key):
    if any(type(value) is not int or value <= 0 for value in (business_id, client_id, branch_id)):
        raise ValidationError({"patient": "Select a valid business, client and branch."})
    if not isinstance(idempotency_key, str) or not idempotency_key.strip() or len(idempotency_key) > 128:
        raise ValidationError({"idempotency_key": "Provide an idempotency key of at most 128 characters."})
    if not actor or not actor.is_authenticated:
        raise PermissionDenied()
    actor = get_user_model().objects.filter(pk=actor.pk, is_active=True).first()
    if actor is None:
        raise PermissionDenied()
    business = Business.objects.select_for_update().filter(pk=business_id).first()
    if business is None:
        raise NotFound()
    branch = Branch.objects.filter(pk=branch_id, business=business).first()
    assert_medical_branch_permission(actor, business, "medical_patients", "create", branch=branch)
    client = Client.objects.select_for_update().filter(pk=client_id, business=business, is_archived=False).first()
    if client is None:
        raise NotFound()
    assert_can(actor, business, Resources.CLIENTS, Actions.VIEW, obj=client)
    values = _demographics(demographics, business)
    normalized_iin = None if iin in (None, "") else normalize_iin(iin)
    digest = iin_digest(normalized_iin, business_id=business.pk) if normalized_iin else None
    fingerprint = medical_request_digest({"demographics": values, "iin": normalized_iin}, business_id=business.pk)
    private_command_key = medical_request_digest({"idempotency_key": idempotency_key}, business_id=business.pk)

    def operation():
        if PatientProfile.objects.filter(client=client).exists():
            raise InvalidTransition("This client already has a medical profile.")
        if digest and PatientProfile.objects.filter(business=business, iin_digest=digest, identity_status="verified").exists():
            raise InvalidTransition("Medical identity requires review before creating another profile.")
        patient = PatientProfile(business=business, client=client, created_by=actor, iin_digest=digest,
            demographics_encrypted=encrypt_medical_value(json.dumps(values, sort_keys=True, ensure_ascii=False),
                business_id=business.pk, subject_id=client.pk, purpose="demographics"))
        if normalized_iin:
            patient.iin_encrypted = encrypt_medical_value(normalized_iin, business_id=business.pk, subject_id=client.pk, purpose="iin")
        patient.full_clean()
        patient.save(force_insert=True)
        write_patient_audit(actor=actor, business=business, patient=patient, action=MedicalAuditEvent.Actions.PATIENT_CREATED)
        return CRMCommandResult(data={}, status_code=201, resource=patient)

    result = run_idempotent_crm_command(business=business, actor=actor, action="medical.patient.create",
        idempotency_key=private_command_key, payload={"client": client.pk, "branch": branch.pk, "fingerprint": fingerprint},
        operation=operation)
    patient = PatientProfile.objects.get(business=business, client=client, pk=result.resource_id if result.replayed else result.resource.pk)
    return patient, result.replayed


@transaction.atomic
def update_unverified_patient_profile(*, actor, business_id, patient_id, branch_id,
                                      expected_revision, demographics, iin, reason, idempotency_key):
    """Replace preliminary identity fields; verified identity uses a separate correction workflow."""
    if any(type(value) is not int or value <= 0 for value in (business_id, patient_id, branch_id, expected_revision)):
        raise ValidationError({"patient": "Select valid identifiers and revision."})
    if not isinstance(idempotency_key, str) or not idempotency_key.strip() or len(idempotency_key) > 128:
        raise ValidationError({"idempotency_key": "Provide an idempotency key of at most 128 characters."})
    if not isinstance(reason, str) or not reason.strip() or len(reason) > 2000:
        raise ValidationError({"reason": "Provide a correction reason of at most 2000 characters."})
    if not actor or not actor.is_authenticated:
        raise PermissionDenied()
    actor = get_user_model().objects.filter(pk=actor.pk, is_active=True).first()
    if actor is None:
        raise PermissionDenied()
    business = Business.objects.select_for_update().filter(pk=business_id).first()
    if business is None:
        raise NotFound()
    branch = Branch.objects.filter(pk=branch_id, business=business).first()
    assert_medical_branch_permission(actor, business, "medical_patients", "update", branch=branch)
    client_id = PatientProfile.objects.filter(pk=patient_id, business=business).values_list("client_id", flat=True).first()
    client = Client.objects.select_for_update().filter(pk=client_id, business=business, is_archived=False).first()
    if client is None:
        raise NotFound()
    assert_can(actor, business, Resources.CLIENTS, Actions.VIEW, obj=client)
    patient = PatientProfile.objects.select_for_update().get(pk=patient_id, business=business, client=client)
    values = _demographics(demographics, business)
    normalized_iin = None if iin in (None, "") else normalize_iin(iin)
    digest = iin_digest(normalized_iin, business_id=business.pk) if normalized_iin else None
    fingerprint = medical_request_digest({"demographics": values, "iin": normalized_iin, "reason": reason},
                                         business_id=business.pk)
    command_key = medical_request_digest({"idempotency_key": idempotency_key}, business_id=business.pk)

    def operation():
        if patient.revision != expected_revision:
            raise InvalidTransition("Patient identity changed; reload before correcting it.")
        if patient.identity_status != PatientProfile.IdentityStatus.UNVERIFIED:
            raise InvalidTransition("Verified identity requires the controlled correction workflow.")
        if digest and PatientProfile.objects.filter(business=business, iin_digest=digest,
                identity_status=PatientProfile.IdentityStatus.VERIFIED).exclude(pk=patient.pk).exists():
            raise InvalidTransition("Medical identity requires review before using this identifier.")
        retain_identity_revision(patient=patient, client=client, actor=actor, reason=reason)
        patient.demographics_encrypted = encrypt_medical_value(json.dumps(values, sort_keys=True, ensure_ascii=False),
            business_id=business.pk, subject_id=client.pk, purpose="demographics")
        patient.iin_encrypted = encrypt_medical_value(normalized_iin, business_id=business.pk,
            subject_id=client.pk, purpose="iin") if normalized_iin else ""
        patient.iin_digest = digest
        patient.revision += 1
        patient.full_clean()
        patient.save(update_fields=["demographics_encrypted", "iin_encrypted", "iin_digest", "revision", "updated_at"])
        write_patient_audit(actor=actor, business=business, patient=patient, action=MedicalAuditEvent.Actions.PATIENT_UPDATED)
        return CRMCommandResult(data={}, status_code=200, resource=patient)

    result = run_idempotent_crm_command(business=business, actor=actor, action="medical.patient.update_unverified",
        idempotency_key=command_key, payload={"patient": patient.pk, "branch": branch.pk,
            "expected_revision": expected_revision, "fingerprint": fingerprint}, operation=operation)
    patient.refresh_from_db()
    return patient, result.replayed
