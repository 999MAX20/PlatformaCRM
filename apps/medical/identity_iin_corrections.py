import json

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
from .identity_crypto import decrypt_medical_value, encrypt_medical_value, iin_digest, medical_request_digest, normalize_iin
from .identity_history import retain_identity_revision
from .identity_correction_reads import correction_proposal
from .identity_verification import _validate_stored_identity, _verification_context
from .models import MedicalAuditEvent, MedicalRoleAssignment, PatientIdentityCorrection, PatientProfile
from .role_access import assert_medical_branch_permission, assert_medical_role_permission


def _reason(value):
    if not isinstance(value, str) or not value.strip() or len(value) > 2000:
        raise ValidationError({"reason": "Provide a reason of at most 2000 characters."})
    return value.strip()


def _encrypted(patient, value, purpose):
    return encrypt_medical_value(json.dumps(value, sort_keys=True, ensure_ascii=False),
        business_id=patient.business_id, subject_id=patient.pk, purpose=purpose)


def _current_identity(patient, client, revision, client_updated_at):
    if patient.revision != revision or client.updated_at != client_updated_at:
        raise InvalidTransition("Patient identity changed; submit a new correction after rechecking it.")
    if patient.identity_status != "verified":
        raise InvalidTransition("Use the preliminary identity workflow before verification.")


def _apply(correction, *, patient, client, business, branch, applicant, decision_actor, proposal, evidence, decision_reason):
    _current_identity(patient, client, correction.source_revision, correction.source_client_updated_at)
    _validate_stored_identity(patient, client, business)
    decrypt_medical_value(patient.verification_evidence_encrypted, business_id=business.pk,
                         subject_id=patient.pk, purpose="verification_evidence")
    identifier = proposal["iin"]
    digest = iin_digest(identifier, business_id=business.pk) if identifier else None
    if digest == patient.iin_digest:
        raise InvalidTransition("The proposed identity is unchanged.")
    if digest and PatientProfile.objects.filter(business=business, iin_digest=digest,
            identity_status="verified").exclude(pk=patient.pk).exists():
        raise InvalidTransition("Medical identity requires review before correction.")
    retain_identity_revision(patient=patient, client=client, actor=decision_actor, reason=proposal["reason"])
    patient.iin_digest = digest
    patient.iin_encrypted = encrypt_medical_value(identifier, business_id=business.pk, subject_id=client.pk,
        purpose="iin") if identifier else ""
    patient.verification_evidence_encrypted = _encrypted(patient, {
        **evidence, "branch_id": branch.pk, "source_revision": patient.revision,
        "client_updated_at": client.updated_at.isoformat(), "full_name": client.full_name,
        "demographics_encrypted": patient.demographics_encrypted, "iin_encrypted": patient.iin_encrypted,
        "rechecked_by_id": applicant.pk, "medical_approver_id": decision_actor.pk if correction.medical_review_required else None,
    }, "verification_evidence")
    patient.verified_by = applicant
    patient.verified_at = timezone.now()
    patient.revision += 1
    patient.full_clean()
    patient.save(update_fields=["iin_digest", "iin_encrypted", "verification_evidence_encrypted", "verified_by",
                                "verified_at", "revision", "updated_at"])
    correction.state = "applied"
    correction.decided_by = decision_actor
    correction.decided_at = timezone.now()
    correction.decision_encrypted = _encrypted(patient, {"reason": decision_reason}, "identity_correction_decision")
    correction.applied_revision = patient.revision
    correction.full_clean()
    correction.save()
    write_patient_audit(actor=decision_actor, business=business, patient=patient,
        action=MedicalAuditEvent.Actions.IDENTITY_CORRECTION_APPLIED, identity_correction=correction)


@transaction.atomic
def request_iin_correction(*, actor, business_id, patient_id, branch_id, expected_revision,
        expected_client_updated_at, iin, reason, protocol_reference, method, fields, idempotency_key):
    actor, business, branch, client, patient, evidence = _verification_context(
        actor=actor, business_id=business_id, patient_id=patient_id, branch_id=branch_id,
        expected_revision=expected_revision, expected_client_updated_at=expected_client_updated_at,
        protocol_reference=protocol_reference, method=method, fields=fields, idempotency_key=idempotency_key)
    assert_medical_branch_permission(actor, business, "medical_patients", "update", branch=branch)
    proposal = {"iin": normalize_iin(iin) if iin not in (None, "") else None,
                "reason": _reason(reason), "evidence": evidence}
    fingerprint = medical_request_digest(proposal, business_id=business.pk)

    def operation():
        _current_identity(patient, client, expected_revision, expected_client_updated_at)
        digest = iin_digest(proposal["iin"], business_id=business.pk) if proposal["iin"] else None
        if digest == patient.iin_digest:
            raise InvalidTransition("The proposed identity is unchanged.")
        if digest and PatientProfile.objects.filter(business=business, iin_digest=digest,
                identity_status="verified").exclude(pk=patient.pk).exists():
            raise InvalidTransition("Medical identity requires review before correction.")
        review_required = patient.dental_records.exists() or patient.encounters.exists() or patient.tooth_states.exists()
        correction = PatientIdentityCorrection(patient=patient, branch=branch, requested_by=actor,
            source_revision=patient.revision, source_client_updated_at=client.updated_at,
            proposal_encrypted=_encrypted(patient, proposal, "identity_correction_proposal"),
            medical_review_required=review_required)
        if review_required:
            correction.full_clean()
            correction.save(force_insert=True)
            write_patient_audit(actor=actor, business=business, patient=patient,
                action=MedicalAuditEvent.Actions.IDENTITY_CORRECTION_REQUESTED, identity_correction=correction)
        else:
            _apply(correction, patient=patient, client=client, business=business, branch=branch, applicant=actor,
                   decision_actor=actor, proposal=proposal, evidence=evidence, decision_reason=proposal["reason"])
        return CRMCommandResult(data={}, status_code=201, resource=correction)

    result = run_idempotent_crm_command(business=business, actor=actor, action="medical.patient.request_iin_correction",
        idempotency_key=medical_request_digest({"key": idempotency_key}, business_id=business.pk),
        payload={"patient": patient.pk, "branch": branch.pk, "revision": expected_revision,
                 "client_updated_at": expected_client_updated_at.isoformat(), "fingerprint": fingerprint}, operation=operation)
    return PatientIdentityCorrection.objects.get(pk=result.resource_id if result.replayed else result.resource.pk,
                                                patient=patient), result.replayed


@transaction.atomic
def decide_iin_correction(*, actor, business_id, correction_id, approve, reason, idempotency_key):
    if any(type(value) is not int or value <= 0 for value in (business_id, correction_id)) or type(approve) is not bool:
        raise ValidationError({"correction": "Select a valid correction and decision."})
    reason = _reason(reason)
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
    role = assert_medical_role_permission(actor, business, "medical_patients", "approve")
    if role.kind != MedicalRoleAssignment.Kinds.HEAD:
        raise PermissionDenied("Medical identity correction review requires a medical head.")
    correction = PatientIdentityCorrection.objects.select_for_update().filter(pk=correction_id,
        patient__business=business, branch__business=business).first()
    if correction is None:
        raise NotFound()
    branch = Branch.objects.get(pk=correction.branch_id, business=business)
    role = assert_medical_branch_permission(actor, business, "medical_patients", "approve", branch=branch)
    if role.kind != MedicalRoleAssignment.Kinds.HEAD:
        raise PermissionDenied("Medical identity correction review requires a medical head.")
    assert_medical_branch_permission(actor, business, "medical_patients", "view", branch=branch)
    patient = PatientProfile.objects.get(pk=correction.patient_id, business=business)
    client = Client.objects.select_for_update().get(pk=patient.client_id, business=business)
    assert_can(actor, business, Resources.CLIENTS, Actions.VIEW, obj=client)
    patient = PatientProfile.objects.select_for_update().get(pk=patient.pk, business=business)

    def operation():
        if correction.state != "pending":
            raise InvalidTransition("This correction has already been decided.")
        if approve:
            proposal = correction_proposal(correction)
            applicant = get_user_model().objects.get(pk=correction.requested_by_id)
            applicant, _, _, current_client, current_patient, evidence = _verification_context(
                actor=applicant, business_id=business.pk, patient_id=patient.pk, branch_id=branch.pk,
                expected_revision=correction.source_revision, expected_client_updated_at=correction.source_client_updated_at,
                protocol_reference=proposal["evidence"]["protocol_reference"], method=proposal["evidence"]["method"],
                fields=proposal["evidence"]["fields"], idempotency_key=idempotency_key)
            assert_medical_branch_permission(applicant, business, "medical_patients", "update", branch=branch)
            _apply(correction, patient=current_patient, client=current_client, business=business, branch=branch,
                   applicant=applicant, decision_actor=actor, proposal=proposal, evidence=evidence, decision_reason=reason)
        else:
            correction.state = "rejected"
            correction.decided_by = actor
            correction.decided_at = timezone.now()
            correction.decision_encrypted = _encrypted(patient, {"reason": reason}, "identity_correction_decision")
            correction.full_clean()
            correction.save(update_fields=["state", "decided_by", "decided_at", "decision_encrypted", "updated_at"])
            write_patient_audit(actor=actor, business=business, patient=patient,
                action=MedicalAuditEvent.Actions.IDENTITY_CORRECTION_REJECTED, identity_correction=correction)
        return CRMCommandResult(data={}, status_code=200, resource=correction)

    result = run_idempotent_crm_command(business=business, actor=actor, action="medical.patient.decide_iin_correction",
        idempotency_key=medical_request_digest({"key": idempotency_key}, business_id=business.pk),
        payload={"correction": correction.pk, "approve": approve,
                 "reason": medical_request_digest({"reason": reason}, business_id=business.pk)}, operation=operation)
    correction.refresh_from_db()
    return correction, result.replayed
