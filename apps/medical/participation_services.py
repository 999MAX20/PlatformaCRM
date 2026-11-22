import json

from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import NotFound, PermissionDenied, ValidationError

from apps.branches.models import Branch
from apps.businesses.models import Business, BusinessMember
from apps.core.domain_errors import InvalidTransition
from apps.core.idempotency import CRMCommandResult, run_idempotent_crm_command
from .appointment_access import assert_appointment_medical_basis
from .audit import write_patient_audit
from .identity_crypto import encrypt_medical_value, medical_request_digest
from .models import MedicalRoleAssignment, PatientProfile, TreatmentParticipation
from .participation_access import assert_treatment_medical_basis
from .participation_notifications import notify_participation_event
from .role_access import assert_medical_branch_permission, assert_medical_role_permission


def _positive(**values):
    if any(type(value) is not int or value <= 0 for value in values.values()):
        raise ValidationError({"participation": "Provide valid identifiers and revisions."})


def _context(actor, business_id, patient_id, idempotency_key, action):
    _positive(business_id=business_id, patient_id=patient_id)
    if not isinstance(idempotency_key, str) or not idempotency_key.strip() or len(idempotency_key) > 128:
        raise ValidationError({"idempotency_key": "Provide an idempotency key of at most 128 characters."})
    return participation_context(actor, business_id, patient_id, action)


def participation_context(actor, business_id, patient_id, action):
    _positive(business_id=business_id, patient_id=patient_id)
    if not actor or not actor.is_authenticated:
        raise PermissionDenied()
    actor = get_user_model().objects.filter(pk=actor.pk, is_active=True).first()
    if actor is None:
        raise PermissionDenied()
    business = Business.objects.select_for_update().filter(pk=business_id).first()
    if business is None:
        raise NotFound()
    role = assert_medical_role_permission(actor, business, "medical_participation", action)
    if role.kind not in (MedicalRoleAssignment.Kinds.DOCTOR, MedicalRoleAssignment.Kinds.HEAD):
        raise PermissionDenied()
    patient = PatientProfile.objects.select_for_update().filter(pk=patient_id, business=business,
        client__business_id=business_id).first()
    if patient is None:
        raise NotFound()
    return actor, business, patient, role


def assert_proposal_source(*, actor, business, patient_id, role,
                           source_appointment_id=None, source_participation_id=None):
    for name, value in (("source_appointment_id", source_appointment_id), ("source_participation_id", source_participation_id)):
        if value is not None:
            _positive(**{name: value})
    if source_appointment_id is not None and source_participation_id is not None:
        raise ValidationError({"source": "Select one participation basis."})
    if role.kind == MedicalRoleAssignment.Kinds.HEAD:
        return
    elif source_appointment_id is not None:
        assert_appointment_medical_basis(actor=actor, business=business, patient_id=patient_id,
            appointment_id=source_appointment_id, resource="medical_participation", action="create")
    elif source_participation_id is not None:
        assert_treatment_medical_basis(actor=actor, business=business, patient_id=patient_id,
            participation_id=source_participation_id, resource="medical_participation", action="create")
    else:
        raise PermissionDenied()


def proposal_branch(*, actor, business, patient_id, role, branch_id,
                    source_appointment_id=None, source_participation_id=None):
    _positive(branch_id=branch_id)
    assert_proposal_source(actor=actor, business=business, patient_id=patient_id, role=role,
        source_appointment_id=source_appointment_id, source_participation_id=source_participation_id)
    branch = Branch.objects.filter(pk=branch_id, business=business, is_active=True, archived_at__isnull=True).first()
    if branch is None:
        raise PermissionDenied()
    if role.kind == MedicalRoleAssignment.Kinds.HEAD:
        assert_medical_branch_permission(actor, business, "medical_participation", "create", branch=branch)
    return branch


@transaction.atomic
def propose_treatment_participation(*, actor, business_id, patient_id, branch_id, target_member_id,
                                    expected_patient_revision, idempotency_key, reason="",
                                    source_appointment_id=None, source_participation_id=None):
    _positive(branch_id=branch_id, target_member_id=target_member_id, expected_patient_revision=expected_patient_revision)
    if not isinstance(reason, str) or len(reason) > 2000:
        raise ValidationError({"reason": "Provide at most 2000 characters."})
    if source_appointment_id is not None:
        _positive(source_appointment_id=source_appointment_id)
    if source_participation_id is not None:
        _positive(source_participation_id=source_participation_id)
    if source_appointment_id is not None and source_participation_id is not None:
        raise ValidationError({"source": "Select one participation basis."})
    actor, business, patient, role = _context(actor, business_id, patient_id, idempotency_key, "create")
    branch = proposal_branch(actor=actor, business=business, patient_id=patient_id, role=role,
        branch_id=branch_id, source_appointment_id=source_appointment_id, source_participation_id=source_participation_id)
    target = BusinessMember.objects.select_related("user").filter(pk=target_member_id, business=business, is_active=True).first()
    if target is None or target.user_id == actor.pk:
        raise PermissionDenied()
    recipient = assert_medical_branch_permission(target.user, business, "medical_participation", "approve", branch=branch)
    if recipient.kind not in (MedicalRoleAssignment.Kinds.DOCTOR, MedicalRoleAssignment.Kinds.HEAD):
        raise PermissionDenied()
    digest = medical_request_digest({"reason": reason}, business_id=business_id)

    def operation():
        if patient.revision != expected_patient_revision:
            raise InvalidTransition("Patient changed; review it before proposing participation.")
        if TreatmentParticipation.objects.filter(patient=patient, member=target, branch=branch,
                                                state__in=["pending", "active"]).exists():
            raise InvalidTransition("An open participation already exists for this doctor and branch.")
        item = TreatmentParticipation(patient=patient, member=target, branch=branch, proposed_by=actor)
        if role.kind == MedicalRoleAssignment.Kinds.DOCTOR:
            item.source_appointment_id = source_appointment_id
            item.source_participation_id = source_participation_id
        item.full_clean()
        item.save(force_insert=True)
        item.reason_encrypted = encrypt_medical_value(json.dumps({"reason": reason}, ensure_ascii=False),
            business_id=business_id, subject_id=item.pk, purpose="participation_proposal")
        item.save(update_fields=["reason_encrypted"])
        event = write_patient_audit(actor=actor, business=business, patient=patient,
            action="participation_proposed", participation=item)
        notify_participation_event(event)
        return CRMCommandResult(data={}, status_code=201, resource=item)

    result = run_idempotent_crm_command(business=business, actor=actor, action="medical.participation.propose",
        idempotency_key=medical_request_digest({"key": idempotency_key}, business_id=business_id),
        payload={"patient": patient_id, "branch": branch_id, "target": target_member_id,
            "expected_patient_revision": expected_patient_revision, "reason_digest": digest,
            "source_appointment": source_appointment_id, "source_participation": source_participation_id}, operation=operation)
    item = TreatmentParticipation.objects.get(patient=patient, member=target, branch=branch,
        pk=result.resource_id if result.replayed else result.resource.pk)
    return item, result.replayed


@transaction.atomic
def respond_treatment_participation(*, actor, business_id, patient_id, participation_id,
                                    expected_revision, decision, idempotency_key, reason=""):
    _positive(participation_id=participation_id, expected_revision=expected_revision)
    if decision not in ("accept", "decline"):
        raise ValidationError({"decision": "Select accept or decline."})
    if not isinstance(reason, str) or len(reason) > 2000 or (decision == "decline" and not reason.strip()):
        raise ValidationError({"reason": "Provide a reason of at most 2000 characters."})
    if decision == "accept" and reason:
        raise ValidationError({"reason": "A reason applies only to declining an invitation."})
    actor, business, patient, _ = _context(actor, business_id, patient_id, idempotency_key, "approve")
    item = TreatmentParticipation.objects.select_for_update().select_related("branch").filter(
        pk=participation_id, patient=patient, member__business_id=business_id,
        member__user_id=actor.pk, branch__business_id=business_id).first()
    if item is None:
        raise PermissionDenied()
    assert_medical_branch_permission(actor, business, "medical_participation", "approve", branch=item.branch)

    def operation():
        if item.revision != expected_revision or item.state != "pending":
            raise InvalidTransition("Participation changed; review its current state.")
        if item.proposed_at > timezone.now():
            raise InvalidTransition("The proposal is not effective yet.")
        if decision == "accept":
            item.state, item.accepted_at = "active", timezone.now()
        else:
            item.state, item.closed_at, item.closed_by = "declined", timezone.now(), actor
            item.decline_reason_encrypted = encrypt_medical_value(
                json.dumps({"reason": reason, "revision": item.revision + 1}, ensure_ascii=False),
                business_id=business_id, subject_id=item.pk, purpose="participation_decline")
        item.revision += 1
        item.full_clean()
        item.save(update_fields=["state", "accepted_at", "closed_at", "closed_by", "revision", "decline_reason_encrypted", "updated_at"])
        event = write_patient_audit(actor=actor, business=business, patient=patient,
            action="participation_accepted" if decision == "accept" else "participation_declined", participation=item)
        notify_participation_event(event)
        return CRMCommandResult(data={}, resource=item)

    result = run_idempotent_crm_command(business=business, actor=actor, action="medical.participation.respond",
        idempotency_key=medical_request_digest({"key": idempotency_key}, business_id=business_id),
        payload={"patient": patient_id, "participation": participation_id,
                 "expected_revision": expected_revision, "decision": decision,
                 **({"reason_digest": medical_request_digest({"reason": reason}, business_id=business_id)}
                    if decision == "decline" else {})}, operation=operation)
    item.refresh_from_db()
    return item, result.replayed

@transaction.atomic
def withdraw_treatment_participation(*, actor, business_id, patient_id, participation_id,
                                     expected_revision, idempotency_key):
    _positive(participation_id=participation_id, expected_revision=expected_revision)
    actor, business, patient, role = _context(actor, business_id, patient_id, idempotency_key, "create")
    item = TreatmentParticipation.objects.select_for_update().select_related("branch").filter(
        pk=participation_id, patient=patient, member__business_id=business_id,
        branch__business_id=business_id).first()
    if item is None:
        raise PermissionDenied()
    if item.proposed_by_id != actor.pk:
        if role.kind != MedicalRoleAssignment.Kinds.HEAD:
            raise PermissionDenied()
        assert_medical_branch_permission(actor, business, "medical_participation", "manage", branch=item.branch)

    def operation():
        if item.revision != expected_revision or item.state != "pending":
            raise InvalidTransition("Participation changed; only a pending proposal can be withdrawn.")
        if item.proposed_at > timezone.now():
            raise InvalidTransition("The proposal is not effective yet.")
        item.state, item.closed_at, item.closed_by = "withdrawn", timezone.now(), actor
        item.revision += 1
        item.full_clean()
        item.save(update_fields=["state", "closed_at", "closed_by", "revision", "updated_at"])
        event = write_patient_audit(actor=actor, business=business, patient=patient,
            action="participation_withdrawn", participation=item)
        notify_participation_event(event)
        return CRMCommandResult(data={}, resource=item)

    result = run_idempotent_crm_command(business=business, actor=actor, action="medical.participation.withdraw",
        idempotency_key=medical_request_digest({"key": idempotency_key}, business_id=business_id),
        payload={"patient": patient_id, "participation": participation_id,
                 "expected_revision": expected_revision}, operation=operation)
    item.refresh_from_db()
    return item, result.replayed
