import hmac
import json
from datetime import datetime

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
from .identity_crypto import MedicalDataUnavailable, decrypt_medical_value, encrypt_medical_value, iin_digest, medical_request_digest
from .identity_history import retain_identity_revision
from .identity_policy import verification_evidence
from .models import MedicalAuditEvent, MedicalRoleAssignment, PatientProfile
from .patient_services import _demographics
from .role_access import assert_medical_branch_permission


def _verification_context(*, actor, business_id, patient_id, branch_id, expected_revision,
                          expected_client_updated_at, protocol_reference, method, fields, idempotency_key):
    if any(type(value) is not int or value <= 0 for value in (business_id, patient_id, branch_id, expected_revision)):
        raise ValidationError({"patient": "Select valid identifiers and revision."})
    if not isinstance(idempotency_key, str) or not idempotency_key.strip() or len(idempotency_key) > 128:
        raise ValidationError({"idempotency_key": "Provide an idempotency key of at most 128 characters."})
    if not isinstance(expected_client_updated_at, datetime) or not timezone.is_aware(expected_client_updated_at):
        raise ValidationError({"expected_client_updated_at": "Read the client before verifying identity."})
    if not actor or not actor.is_authenticated:
        raise PermissionDenied()
    actor = get_user_model().objects.filter(pk=actor.pk, is_active=True).first()
    if actor is None:
        raise PermissionDenied()
    business = Business.objects.select_for_update().filter(pk=business_id).first()
    if business is None:
        raise NotFound()
    branch = Branch.objects.filter(pk=branch_id, business=business).first()
    role = assert_medical_branch_permission(actor, business, "medical_patients", "approve", branch=branch)
    if role.kind != MedicalRoleAssignment.Kinds.RECEPTION:
        raise PermissionDenied("Identity verification requires an authorized reception assignment.")
    evidence = verification_evidence(business_id=business.pk, member_id=role.member_id,
        protocol_reference=protocol_reference, method=method, fields=fields)
    client_id = PatientProfile.objects.filter(pk=patient_id, business=business).values_list("client_id", flat=True).first()
    client = Client.objects.select_for_update().filter(pk=client_id, business=business, is_archived=False).first()
    if client is None:
        raise NotFound()
    assert_can(actor, business, Resources.CLIENTS, Actions.VIEW, obj=client)
    patient = PatientProfile.objects.select_for_update().get(pk=patient_id, business=business, client=client)
    return actor, business, branch, client, patient, evidence


def _validate_stored_identity(patient, client, business):
    context = {"business_id": business.pk, "subject_id": client.pk}
    try:
        demographics = json.loads(decrypt_medical_value(patient.demographics_encrypted, purpose="demographics", **context))
    except (ValueError, TypeError):
        raise MedicalDataUnavailable() from None
    _demographics(demographics, business)
    if patient.iin_digest:
        identifier = decrypt_medical_value(patient.iin_encrypted, purpose="iin", **context)
        if not hmac.compare_digest(iin_digest(identifier, business_id=business.pk), patient.iin_digest):
            raise MedicalDataUnavailable()


@transaction.atomic
def verify_patient_identity(*, actor, business_id, patient_id, branch_id, expected_revision,
                            expected_client_updated_at, protocol_reference, method, fields, idempotency_key):
    actor, business, branch, client, patient, evidence = _verification_context(
        actor=actor, business_id=business_id, patient_id=patient_id, branch_id=branch_id,
        expected_revision=expected_revision, expected_client_updated_at=expected_client_updated_at,
        protocol_reference=protocol_reference, method=method, fields=fields, idempotency_key=idempotency_key)
    fingerprint = medical_request_digest(evidence, business_id=business.pk)
    command_key = medical_request_digest({"idempotency_key": idempotency_key}, business_id=business.pk)

    def operation():
        if client.updated_at != expected_client_updated_at:
            raise InvalidTransition("The client changed; reload before verifying identity.")
        if patient.revision != expected_revision:
            raise InvalidTransition("Patient identity changed; reload before verifying it.")
        if patient.identity_status != PatientProfile.IdentityStatus.UNVERIFIED:
            raise InvalidTransition("Identity is already verified; use the controlled correction workflow.")
        if not client.full_name.strip():
            raise ValidationError({"patient": "Complete the patient identity before verification."})
        _validate_stored_identity(patient, client, business)
        if patient.iin_digest:
            if PatientProfile.objects.filter(business=business, iin_digest=patient.iin_digest,
                    identity_status=PatientProfile.IdentityStatus.VERIFIED).exclude(pk=patient.pk).exists():
                raise InvalidTransition("Medical identity requires review before verification.")
        retain_identity_revision(patient=patient, client=client, actor=actor, reason="identity_verification")
        verified_snapshot = {**evidence, "branch_id": branch.pk, "source_revision": patient.revision,
            "client_updated_at": client.updated_at.isoformat(),
            "full_name": client.full_name, "demographics_encrypted": patient.demographics_encrypted,
            "iin_encrypted": patient.iin_encrypted}
        patient.verification_evidence_encrypted = encrypt_medical_value(
            json.dumps(verified_snapshot, sort_keys=True, ensure_ascii=False),
            business_id=business.pk, subject_id=patient.pk, purpose="verification_evidence")
        patient.identity_status = PatientProfile.IdentityStatus.VERIFIED
        patient.verified_at = timezone.now()
        patient.verified_by = actor
        patient.revision += 1
        patient.full_clean()
        patient.save(update_fields=["identity_status", "verification_evidence_encrypted", "verified_at", "verified_by", "revision", "updated_at"])
        write_patient_audit(actor=actor, business=business, patient=patient, action=MedicalAuditEvent.Actions.IDENTITY_VERIFIED)
        return CRMCommandResult(data={}, status_code=200, resource=patient)

    result = run_idempotent_crm_command(business=business, actor=actor, action="medical.patient.verify",
        idempotency_key=command_key, payload={"patient": patient.pk, "branch": branch.pk,
            "expected_revision": expected_revision, "expected_client_updated_at": expected_client_updated_at.isoformat(),
            "fingerprint": fingerprint}, operation=operation)
    patient.refresh_from_db()
    return patient, result.replayed
