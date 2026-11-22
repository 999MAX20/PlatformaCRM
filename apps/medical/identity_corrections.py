import json
from datetime import timedelta

from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from apps.clients.models import Client
from apps.core.domain_errors import InvalidTransition
from apps.core.idempotency import CRMCommandResult, run_idempotent_crm_command
from .audit import write_patient_audit
from .identity_crypto import decrypt_medical_value, encrypt_medical_value, medical_request_digest
from .identity_history import retain_identity_revision
from .identity_verification import _validate_stored_identity, _verification_context
from .models import MedicalAuditEvent, PatientProfile
from .patient_services import _demographics
from .role_access import assert_medical_branch_permission


@transaction.atomic
def correct_patient_administrative_identity(*, actor, business_id, patient_id, branch_id, expected_revision,
        expected_client_updated_at, full_name, demographics, reason, protocol_reference, method, fields, idempotency_key):
    actor, business, branch, client, patient, evidence = _verification_context(
        actor=actor, business_id=business_id, patient_id=patient_id, branch_id=branch_id,
        expected_revision=expected_revision, expected_client_updated_at=expected_client_updated_at,
        protocol_reference=protocol_reference, method=method, fields=fields, idempotency_key=idempotency_key)
    assert_medical_branch_permission(actor, business, "medical_patients", "update", branch=branch)
    if not isinstance(reason, str) or not reason.strip() or len(reason) > 2000:
        raise ValidationError({"reason": "Provide a correction reason of at most 2000 characters."})
    if not isinstance(full_name, str) or not full_name.strip() or len(full_name) > 255:
        raise ValidationError({"full_name": "Provide a valid patient name."})
    values = _demographics(demographics, business)
    fingerprint = medical_request_digest({"full_name": full_name, "demographics": values, "reason": reason,
                                         "evidence": evidence}, business_id=business.pk)
    command_key = medical_request_digest({"idempotency_key": idempotency_key}, business_id=business.pk)

    def operation():
        if client.updated_at != expected_client_updated_at or patient.revision != expected_revision:
            raise InvalidTransition("Patient identity changed; reload before correcting it.")
        if patient.identity_status != PatientProfile.IdentityStatus.VERIFIED:
            raise InvalidTransition("Use the preliminary identity workflow before verification.")
        _validate_stored_identity(patient, client, business)
        decrypt_medical_value(patient.verification_evidence_encrypted, business_id=business.pk,
                             subject_id=patient.pk, purpose="verification_evidence")
        retain_identity_revision(patient=patient, client=client, actor=actor, reason=reason)
        client_version = max(timezone.now(), client.updated_at + timedelta(microseconds=1))
        # This controlled writer shares the Client lock and commits only with recheck/history/audit.
        Client.objects.filter(pk=client.pk, business=business).update(full_name=full_name, updated_at=client_version)
        patient.demographics_encrypted = encrypt_medical_value(json.dumps(values, sort_keys=True, ensure_ascii=False),
            business_id=business.pk, subject_id=client.pk, purpose="demographics")
        snapshot = {**evidence, "branch_id": branch.pk, "source_revision": patient.revision,
            "client_updated_at": client_version.isoformat(), "full_name": full_name,
            "demographics_encrypted": patient.demographics_encrypted, "iin_encrypted": patient.iin_encrypted}
        patient.verification_evidence_encrypted = encrypt_medical_value(json.dumps(snapshot, sort_keys=True, ensure_ascii=False),
            business_id=business.pk, subject_id=patient.pk, purpose="verification_evidence")
        patient.verified_at = timezone.now()
        patient.verified_by = actor
        patient.revision += 1
        patient.full_clean()
        patient.save(update_fields=["demographics_encrypted", "verification_evidence_encrypted", "verified_at", "verified_by", "revision", "updated_at"])
        write_patient_audit(actor=actor, business=business, patient=patient, action=MedicalAuditEvent.Actions.PATIENT_UPDATED)
        return CRMCommandResult(data={}, status_code=200, resource=patient)

    result = run_idempotent_crm_command(business=business, actor=actor, action="medical.patient.correct_administrative",
        idempotency_key=command_key, payload={"patient": patient.pk, "branch": branch.pk,
            "expected_revision": expected_revision, "expected_client_updated_at": expected_client_updated_at.isoformat(),
            "fingerprint": fingerprint}, operation=operation)
    patient.refresh_from_db()
    return patient, result.replayed
