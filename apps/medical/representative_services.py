import json
from datetime import datetime, timezone as datetime_timezone

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
from .identity_crypto import encrypt_medical_value, medical_request_digest
from .models import MedicalAuditEvent, MedicalRoleAssignment, PatientProfile, PatientRepresentative
from .representative_policy import representative_evidence
from .role_access import assert_medical_branch_permission


def _date(value, field, *, nullable=False):
    if value is None and nullable:
        return
    if not isinstance(value, datetime) or not timezone.is_aware(value):
        raise ValidationError({field: "Provide a timestamp with its timezone."})


def _context(actor, business_id, branch_id, patient_id, representative_client_id, idempotency_key, *, allow_archived=False):
    if any(type(value) is not int or value <= 0 for value in (business_id, branch_id, patient_id, representative_client_id)):
        raise ValidationError({"representative": "Select valid identifiers."})
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
    role = assert_medical_branch_permission(actor, business, "medical_patients", "approve", branch=branch)
    if role.kind != MedicalRoleAssignment.Kinds.RECEPTION:
        raise PermissionDenied("Representation verification requires an authorized reception assignment.")
    patient_client_id = PatientProfile.objects.filter(pk=patient_id, business=business).values_list("client_id", flat=True).first()
    clients = Client.objects.select_for_update().filter(business=business, pk__in=[patient_client_id, representative_client_id]).order_by("pk")
    if not allow_archived:
        clients = clients.filter(is_archived=False)
    clients = {client.pk: client for client in clients}
    if patient_client_id not in clients or representative_client_id not in clients:
        raise NotFound()
    if patient_client_id == representative_client_id:
        raise ValidationError({"representative_client": "Select a person other than the patient."})
    for client in clients.values():
        assert_can(actor, business, Resources.CLIENTS, Actions.VIEW, obj=client)
    patient = PatientProfile.objects.select_for_update().get(pk=patient_id, business=business, client_id=patient_client_id)
    return actor, business, role, patient, clients[representative_client_id]


@transaction.atomic
def verify_patient_representative(*, actor, business_id, branch_id, patient_id, representative_client_id,
                                 expected_patient_revision, expected_client_updated_at, protocol_reference,
                                 method, fields, permissions, valid_from, valid_until, idempotency_key):
    if type(expected_patient_revision) is not int or expected_patient_revision <= 0:
        raise ValidationError({"expected_patient_revision": "Provide the current patient revision."})
    _date(expected_client_updated_at, "expected_client_updated_at")
    _date(valid_from, "valid_from")
    _date(valid_until, "valid_until", nullable=True)
    valid_from = valid_from.astimezone(datetime_timezone.utc)
    valid_until = valid_until.astimezone(datetime_timezone.utc) if valid_until else None
    if valid_until is not None and valid_until <= valid_from:
        raise ValidationError({"valid_until": "The end must follow the start of authority."})
    actor, business, role, patient, client = _context(actor, business_id, branch_id, patient_id, representative_client_id, idempotency_key)
    evidence = representative_evidence(business_id=business.pk, member_id=role.member_id,
        protocol_reference=protocol_reference, method=method, fields=fields, permissions=permissions, valid_until=valid_until)
    fingerprint = medical_request_digest({**evidence, "valid_from": valid_from.isoformat(),
        "valid_until": valid_until.isoformat() if valid_until else None}, business_id=business.pk)
    command_key = medical_request_digest({"idempotency_key": idempotency_key}, business_id=business.pk)

    def operation():
        if patient.revision != expected_patient_revision or client.updated_at != expected_client_updated_at:
            raise InvalidTransition("Identity changed; reload before verifying representation.")
        if not client.full_name.strip():
            raise ValidationError({"representative_client": "Complete the representative identity."})
        now = timezone.now()
        if valid_until is not None and valid_until <= now:
            raise InvalidTransition("Representation has already expired.")
        snapshot = {**evidence, "patient_id": patient.pk, "patient_revision": patient.revision,
            "representative_client_id": client.pk, "full_name": client.full_name,
            "client_updated_at": client.updated_at.isoformat(), "branch_id": branch_id,
            "valid_from": valid_from.isoformat(), "valid_until": valid_until.isoformat() if valid_until else None}
        relation = PatientRepresentative(patient=patient, representative_client=client,
            verified_by=actor, verified_at=now, valid_from=valid_from, valid_until=valid_until,
            authority_encrypted=encrypt_medical_value(json.dumps(snapshot, sort_keys=True, ensure_ascii=False),
                business_id=business.pk, subject_id=patient.pk, purpose="representative_staging"))
        relation.full_clean()
        relation.save(force_insert=True)
        # Bind the final envelope to the allocated relationship ID before the transaction can commit.
        relation.authority_encrypted = encrypt_medical_value(json.dumps(snapshot, sort_keys=True, ensure_ascii=False),
            business_id=business.pk, subject_id=relation.pk, purpose="representative_authority")
        relation.save(update_fields=["authority_encrypted"])
        write_patient_audit(actor=actor, business=business, patient=patient,
                            action=MedicalAuditEvent.Actions.REPRESENTATIVE_VERIFIED, representative=relation)
        return CRMCommandResult(data={}, status_code=201, resource=relation)

    result = run_idempotent_crm_command(business=business, actor=actor, action="medical.representative.verify",
        idempotency_key=command_key, payload={"patient": patient.pk, "representative_client": client.pk,
            "branch": branch_id, "expected_patient_revision": expected_patient_revision,
            "expected_client_updated_at": expected_client_updated_at.isoformat(), "fingerprint": fingerprint}, operation=operation)
    relation = PatientRepresentative.objects.get(patient=patient, representative_client=client,
        pk=result.resource_id if result.replayed else result.resource.pk)
    return relation, result.replayed


@transaction.atomic
def revoke_patient_representative(*, actor, business_id, branch_id, patient_id, representative_client_id,
                                 representative_id, expected_revision, reason, idempotency_key):
    if any(type(value) is not int or value <= 0 for value in (representative_id, expected_revision)):
        raise ValidationError({"representative": "Provide a valid representation and revision."})
    if not isinstance(reason, str) or not reason.strip() or len(reason) > 2000:
        raise ValidationError({"reason": "Provide a revocation reason of at most 2000 characters."})
    actor, business, _, patient, client = _context(actor, business_id, branch_id, patient_id,
        representative_client_id, idempotency_key, allow_archived=True)
    relation = PatientRepresentative.objects.select_for_update().filter(pk=representative_id,
        patient=patient, representative_client=client).first()
    if relation is None:
        raise NotFound()
    fingerprint = medical_request_digest({"reason": reason}, business_id=business.pk)
    command_key = medical_request_digest({"idempotency_key": idempotency_key}, business_id=business.pk)

    def operation():
        if relation.revision != expected_revision:
            raise InvalidTransition("Representation changed; reload before revoking it.")
        if relation.revoked_at is not None:
            raise InvalidTransition("Representation is already revoked.")
        relation.revoked_at = timezone.now()
        relation.revoked_by = actor
        relation.revocation_encrypted = encrypt_medical_value(json.dumps({"reason": reason}, ensure_ascii=False),
            business_id=business.pk, subject_id=relation.pk, purpose="representative_revocation")
        relation.revision += 1
        relation.full_clean()
        relation.save(update_fields=["revoked_at", "revoked_by", "revocation_encrypted", "revision", "updated_at"])
        write_patient_audit(actor=actor, business=business, patient=patient,
                            action=MedicalAuditEvent.Actions.REPRESENTATIVE_REVOKED, representative=relation)
        return CRMCommandResult(data={}, resource=relation)

    result = run_idempotent_crm_command(business=business, actor=actor, action="medical.representative.revoke",
        idempotency_key=command_key, payload={"representative": relation.pk, "branch": branch_id,
            "expected_revision": expected_revision, "fingerprint": fingerprint}, operation=operation)
    relation.refresh_from_db()
    return relation, result.replayed
