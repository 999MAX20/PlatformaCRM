import json
from datetime import timedelta

from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied, ValidationError

from apps.core.domain_errors import InvalidTransition
from apps.core.idempotency import CRMCommandResult, run_idempotent_crm_command
from .audit import write_patient_audit
from .correction_access_context import command_values, expire_observed, locked_business, own_target, positive, scoped_request
from .identity_crypto import encrypt_medical_value, medical_request_digest
from .models import MedicalCorrectionAccess


def _encrypted(reason, *, business, subject_id, purpose):
    return encrypt_medical_value(json.dumps({"reason": reason}, ensure_ascii=False),
        business_id=business.pk, subject_id=subject_id, purpose=purpose)


def _command(*, actor, business, key, action, payload, operation):
    result = run_idempotent_crm_command(business=business, actor=actor, action=action,
        idempotency_key=medical_request_digest({"key": key}, business_id=business.pk),
        payload=payload, operation=operation)
    item = MedicalCorrectionAccess.objects.get(pk=result.resource_id if result.replayed else result.resource.pk)
    return item, result.replayed


@transaction.atomic
def request_correction_access(*, actor, business_id, encounter_id, expected_patient_revision,
        expected_target_revision, reason, idempotency_key, document_id=None):
    reason = command_values(reason, idempotency_key)
    positive(expected_patient_revision=expected_patient_revision, expected_target_revision=expected_target_revision)
    business, _ = locked_business(actor, business_id)
    encounter, document, role = own_target(actor, business, encounter_id, document_id)
    patient, target = encounter.patient, document or encounter

    def operation():
        if patient.revision != expected_patient_revision or target.revision != expected_target_revision:
            raise InvalidTransition("The target changed; review it before requesting access.")
        existing = MedicalCorrectionAccess.objects.select_for_update().filter(
            requester_id=role.member_id, encounter=encounter, document=document, state__in=["pending", "active"]).first()
        if existing is not None and not expire_observed(existing, actor=actor, business=business):
            raise InvalidTransition("An open correction request already exists for this target.")
        item = MedicalCorrectionAccess(patient=patient, encounter=encounter, document=document,
            requester_id=role.member_id, patient_revision=patient.revision, target_revision=target.revision,
            reason_encrypted=_encrypted(reason, business=business, subject_id=encounter.pk,
                                        purpose="correction_access_request"))
        item.full_clean()
        item.save(force_insert=True)
        write_patient_audit(actor=actor, business=business, patient=patient,
                            action="correction_access_requested", correction_access=item)
        return CRMCommandResult(data={}, status_code=201, resource=item)

    return _command(actor=actor, business=business, key=idempotency_key, action="medical.correction_access.request",
        payload={"encounter": encounter_id, "document": document_id, "patient_revision": expected_patient_revision,
                 "target_revision": expected_target_revision,
                 "reason_digest": medical_request_digest({"reason": reason}, business_id=business_id)}, operation=operation)


@transaction.atomic
def review_correction_access(*, actor, business_id, request_id, expected_revision, decision, reason, idempotency_key):
    reason = command_values(reason, idempotency_key)
    positive(expected_revision=expected_revision)
    if decision not in {"approve", "reject"}:
        raise ValidationError({"decision": "Select approve or reject."})
    business, _ = locked_business(actor, business_id, head=True)
    item = scoped_request(actor, business, request_id, head=True)
    if item.requester.user_id == actor.pk:
        raise PermissionDenied()

    def operation():
        if item.state != "pending" or item.revision != expected_revision:
            raise InvalidTransition("The correction request changed; review its current state.")
        if decision == "approve":
            encounter, document, _ = own_target(item.requester.user, business, item.encounter_id, item.document_id)
            if encounter.patient.revision != item.patient_revision or (document or encounter).revision != item.target_revision:
                raise InvalidTransition("The source changed; a new correction request is required.")
        item.state = "active" if decision == "approve" else "rejected"
        item.reviewed_by, item.reviewed_at = actor, timezone.now()
        item.expires_at = item.reviewed_at + timedelta(hours=24) if decision == "approve" else None
        item.decision_encrypted = _encrypted(reason, business=business, subject_id=item.pk, purpose="correction_access_decision")
        item.revision += 1
        item.full_clean()
        item.save(update_fields=["state", "reviewed_by", "reviewed_at", "expires_at", "decision_encrypted", "revision", "updated_at"])
        write_patient_audit(actor=actor, business=business, patient=item.patient,
            action="correction_access_approved" if decision == "approve" else "correction_access_rejected", correction_access=item)
        return CRMCommandResult(data={}, resource=item)

    return _command(actor=actor, business=business, key=idempotency_key, action="medical.correction_access.review",
        payload={"request": request_id, "revision": expected_revision, "decision": decision,
                 "reason_digest": medical_request_digest({"reason": reason}, business_id=business_id)}, operation=operation)


@transaction.atomic
def close_correction_access(*, actor, business_id, request_id, expected_revision, decision, reason, idempotency_key):
    reason = command_values(reason, idempotency_key)
    positive(expected_revision=expected_revision)
    states = {"withdraw": ("pending", "withdrawn"), "complete": ("active", "completed"), "revoke": ("active", "revoked")}
    if decision not in states:
        raise ValidationError({"decision": "Select withdraw, complete or revoke."})
    business, _ = locked_business(actor, business_id, head=decision == "revoke")
    item = scoped_request(actor, business, request_id, head=decision == "revoke")

    def operation():
        source, target = states[decision]
        if item.revision != expected_revision or item.state != source:
            raise InvalidTransition("The correction request changed; review its current state.")
        if source == "active" and timezone.now() >= item.expires_at:
            raise InvalidTransition("Correction access has expired.")
        item.state, item.closed_by, item.closed_at = target, actor, timezone.now()
        item.closure_encrypted = _encrypted(reason, business=business, subject_id=item.pk, purpose="correction_access_closure")
        item.revision += 1
        item.full_clean()
        item.save(update_fields=["state", "closed_by", "closed_at", "closure_encrypted", "revision", "updated_at"])
        write_patient_audit(actor=actor, business=business, patient=item.patient,
                            action="correction_access_" + target, correction_access=item)
        return CRMCommandResult(data={}, resource=item)

    return _command(actor=actor, business=business, key=idempotency_key, action="medical.correction_access.close",
        payload={"request": request_id, "revision": expected_revision, "decision": decision,
                 "reason_digest": medical_request_digest({"reason": reason}, business_id=business_id)}, operation=operation)
