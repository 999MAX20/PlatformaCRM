from datetime import datetime

from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied, ValidationError

from apps.businesses.models import Business, BusinessMember
from apps.core.audit import write_actor_audit_log
from apps.core.domain_errors import InvalidTransition
from apps.core.idempotency import CRMCommandResult, run_idempotent_crm_command
from apps.core.models import AuditLog
from apps.scheduling.models import Appointment, Resource
from .identity_crypto import medical_request_digest
from .models import AppointmentAssistant, MedicalEncounter
from .assistant_context import assistant_management_context
from .assistant_notifications import notify_assistant_invitation
from .role_access import assert_medical_branch_permission


@transaction.atomic
def invite_appointment_assistant(*, actor, business_id, patient_id, appointment_id, target_member_id,
                                expected_updated_at, idempotency_key):
    if any(type(value) is not int or value <= 0
           for value in (business_id, patient_id, appointment_id, target_member_id)):
        raise ValidationError({"invitation": "Provide valid identifiers."})
    if not isinstance(expected_updated_at, datetime) or timezone.is_naive(expected_updated_at):
        raise ValidationError({"expected_updated_at": "Provide the current appointment timestamp."})
    if not isinstance(idempotency_key, str) or not idempotency_key.strip() or len(idempotency_key) > 128:
        raise ValidationError({"idempotency_key": "Provide an idempotency key of at most 128 characters."})
    actor, business, _, appointment, primary = assistant_management_context(actor=actor,
        business_id=business_id, patient_id=patient_id, appointment_id=appointment_id)
    target = BusinessMember.objects.select_related("user").filter(business=business, pk=target_member_id, is_active=True).first()
    if target is None or primary.pk == target.pk or target.user_id == actor.pk:
        raise PermissionDenied()
    recipient = assert_medical_branch_permission(target.user, business, "medical_records", "view",
                                                 branch=appointment.branch)
    if recipient.kind != "assistant":
        raise PermissionDenied()

    def operation():
        if appointment.updated_at != expected_updated_at:
            raise InvalidTransition("The appointment changed; review its current clinician and branch.")
        if AppointmentAssistant.objects.filter(appointment=appointment, assignment_id=recipient.assignment_id,
                                                state__in=["pending", "active"]).exists():
            raise InvalidTransition("An open invitation already exists for this assistant and appointment.")
        item = AppointmentAssistant(business=business, patient_id=patient_id, appointment=appointment,
            branch=appointment.branch, assignment_id=recipient.assignment_id, primary_clinician=primary, invited_by=actor)
        item.full_clean()
        item.save(force_insert=True)
        write_actor_audit_log(actor=actor, business=business, action=AuditLog.Actions.CREATE, instance=item,
            metadata={"permission": True, "kind": "medical_assistant_invited", "revision": item.revision,
                      "state": item.state})
        notify_assistant_invitation(item)
        return CRMCommandResult(data={}, status_code=201, resource=item)

    result = run_idempotent_crm_command(business=business, actor=actor, action="medical.assistant.invite",
        idempotency_key=medical_request_digest({"key": idempotency_key}, business_id=business_id),
        payload={"patient": patient_id, "appointment": appointment_id, "target": target_member_id,
                 "expected_updated_at": expected_updated_at.isoformat()}, operation=operation)
    item = AppointmentAssistant.objects.get(business=business, appointment=appointment,
        assignment_id=recipient.assignment_id, pk=result.resource_id if result.replayed else result.resource.pk)
    return item, result.replayed


@transaction.atomic
def accept_appointment_assistant(*, actor, business_id, invitation_id, expected_revision, idempotency_key):
    if any(type(value) is not int or value <= 0 for value in (business_id, invitation_id, expected_revision)):
        raise ValidationError({"invitation": "Provide valid identifiers and a revision."})
    if not isinstance(idempotency_key, str) or not idempotency_key.strip() or len(idempotency_key) > 128:
        raise ValidationError({"idempotency_key": "Provide an idempotency key of at most 128 characters."})
    if not actor or not actor.is_authenticated:
        raise PermissionDenied()
    actor = get_user_model().objects.filter(pk=actor.pk, is_active=True).first()
    business = Business.objects.select_for_update().filter(pk=business_id).first()
    if actor is None or business is None:
        raise PermissionDenied()
    item = AppointmentAssistant.objects.select_for_update().select_related("branch", "primary_clinician").filter(
        pk=invitation_id, business=business, patient__business=business, patient__client__business=business,
        branch__business=business, primary_clinician__business=business,
        assignment__member__business=business, assignment__member__user=actor).first()
    if item is None:
        raise PermissionDenied()
    recipient = assert_medical_branch_permission(actor, business, "medical_records", "view", branch=item.branch)
    if recipient.kind != "assistant" or recipient.assignment_id != item.assignment_id:
        raise PermissionDenied()
    appointment = Appointment.objects.select_for_update().filter(pk=item.appointment_id, business=business,
        client_id=item.patient.client_id, client__business=business, service__business=business,
        branch_id=item.branch_id, resource__business=business, resource__resource_type=Resource.ResourceTypes.STAFF,
        resource__linked_user_id=item.primary_clinician.user_id,
        is_archived=False, status__in=["created", "confirmed", "rescheduled"]).first()
    if appointment is None or appointment.end_at <= appointment.start_at:
        raise PermissionDenied()
    primary = assert_medical_branch_permission(item.primary_clinician.user, business, "medical_records", "view", branch=item.branch)
    if primary.kind not in ("doctor", "head") or MedicalEncounter.objects.filter(
            appointment=appointment).exclude(state="draft", ended_at__isnull=True).exists():
        raise PermissionDenied()
    if item.invited_at > timezone.now() or item.state not in ("pending", "active"):
        raise PermissionDenied()

    def operation():
        if item.revision != expected_revision or item.state != "pending":
            raise InvalidTransition("The invitation changed; review its current state.")
        item.state, item.accepted_at = "active", timezone.now()
        item.revision += 1
        item.full_clean()
        item.save(update_fields=["state", "accepted_at", "revision"])
        write_actor_audit_log(actor=actor, business=business, action=AuditLog.Actions.UPDATE, instance=item,
            metadata={"permission": True, "kind": "medical_assistant_accepted", "revision": item.revision,
                      "state": item.state})
        return CRMCommandResult(data={}, resource=item)

    result = run_idempotent_crm_command(business=business, actor=actor, action="medical.assistant.accept",
        idempotency_key=medical_request_digest({"key": idempotency_key}, business_id=business_id),
        payload={"invitation": invitation_id, "expected_revision": expected_revision}, operation=operation)
    item.refresh_from_db()
    return item, result.replayed


@transaction.atomic
def revoke_appointment_assistant(*, actor, business_id, invitation_id, expected_revision, idempotency_key):
    if any(type(value) is not int or value <= 0 for value in (business_id, invitation_id, expected_revision)):
        raise ValidationError({"invitation": "Provide valid identifiers and a revision."})
    if not isinstance(idempotency_key, str) or not idempotency_key.strip() or len(idempotency_key) > 128:
        raise ValidationError({"idempotency_key": "Provide an idempotency key of at most 128 characters."})
    if not actor or not actor.is_authenticated:
        raise PermissionDenied()
    actor = get_user_model().objects.filter(pk=actor.pk, is_active=True).first()
    business = Business.objects.select_for_update().filter(pk=business_id).first()
    if actor is None or business is None:
        raise PermissionDenied()
    item = AppointmentAssistant.objects.select_for_update().select_related("branch").filter(
        pk=invitation_id, business=business, appointment__business=business, branch__business=business).first()
    if item is None:
        raise PermissionDenied()
    permission = assert_medical_branch_permission(actor, business, "medical_participation", "create", branch=item.branch)
    is_primary = Appointment.objects.filter(pk=item.appointment_id, business=business, branch_id=item.branch_id,
        resource__business=business, resource__resource_type=Resource.ResourceTypes.STAFF,
        resource__linked_user_id=actor.pk).exists()
    if permission.kind != "head" and not (permission.kind == "doctor" and is_primary):
        raise PermissionDenied()

    def operation():
        if item.revision != expected_revision or item.state not in ("pending", "active"):
            raise InvalidTransition("The invitation changed; review its current state.")
        item.state, item.closed_at, item.closed_by = "revoked", timezone.now(), actor
        item.revision += 1
        item.save(update_fields=["state", "closed_at", "closed_by", "revision"])
        write_actor_audit_log(actor=actor, business=business, action=AuditLog.Actions.UPDATE, instance=item,
            metadata={"permission": True, "kind": "medical_assistant_revoked", "revision": item.revision,
                      "state": item.state})
        return CRMCommandResult(data={}, resource=item)

    result = run_idempotent_crm_command(business=business, actor=actor, action="medical.assistant.revoke",
        idempotency_key=medical_request_digest({"key": idempotency_key}, business_id=business_id),
        payload={"invitation": invitation_id, "expected_revision": expected_revision}, operation=operation)
    item.refresh_from_db()
    return item, result.replayed
