import json

from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied, ValidationError

from apps.businesses.models import BusinessMember
from apps.core.domain_errors import InvalidTransition
from apps.core.idempotency import CRMCommandResult, run_idempotent_crm_command
from .audit import write_patient_audit
from .identity_crypto import encrypt_medical_value, medical_request_digest
from .models import MedicalRoleAssignment, TreatmentParticipation
from .participation_services import _context, _positive
from .participation_notifications import notify_participation_event
from .role_access import assert_medical_branch_permission


@transaction.atomic
def end_participation_by_head(*, actor, business_id, patient_id, participation_id,
                              expected_revision, responsible_member_id, reason, idempotency_key):
    _positive(participation_id=participation_id, expected_revision=expected_revision,
              responsible_member_id=responsible_member_id)
    if not isinstance(reason, str) or not reason.strip() or len(reason) > 2000:
        raise ValidationError({"reason": "Provide a reason of at most 2000 characters."})
    actor, business, patient, role = _context(actor, business_id, patient_id, idempotency_key, "manage")
    if role.kind != MedicalRoleAssignment.Kinds.HEAD:
        raise PermissionDenied()
    item = TreatmentParticipation.objects.select_for_update().select_related("branch").filter(
        pk=participation_id, patient=patient, member__business_id=business_id,
        branch__business_id=business_id).first()
    if item is None:
        raise PermissionDenied()
    assert_medical_branch_permission(actor, business, "medical_participation", "manage",
                                     branch=item.branch, require_active=False)
    responsible = BusinessMember.objects.select_related("user").filter(pk=responsible_member_id, business=business,
        is_active=True, user__is_active=True).first()
    if responsible is None or responsible.user.is_platform_user:
        raise ValidationError({"responsible_member_id": "Select an active member of this business."})

    def operation():
        now = timezone.now()
        if item.revision != expected_revision or item.state != "active":
            raise InvalidTransition("Participation changed; review its current state.")
        if item.accepted_at is None or item.accepted_at > now:
            raise InvalidTransition("Participation is not effective yet.")
        item.state, item.closed_at, item.closed_by = "ended", now, actor
        item.remaining_responsible = responsible
        item.revision += 1
        item.closure_reason_encrypted = encrypt_medical_value(json.dumps({"reason": reason,
            "revision": item.revision, "responsible_member_id": responsible.pk}, ensure_ascii=False),
            business_id=business_id, subject_id=item.pk, purpose="participation_closure")
        item.full_clean()
        item.save(update_fields=["state", "closed_at", "closed_by", "remaining_responsible",
            "revision", "closure_reason_encrypted", "updated_at"])
        event = write_patient_audit(actor=actor, business=business, patient=patient,
            action="participation_ended", participation=item)
        notify_participation_event(event)
        return CRMCommandResult(data={}, resource=item)

    result = run_idempotent_crm_command(business=business, actor=actor, action="medical.participation.end_head",
        idempotency_key=medical_request_digest({"key": idempotency_key}, business_id=business_id),
        payload={"patient": patient_id, "participation": participation_id, "expected_revision": expected_revision,
                 "responsible_member": responsible_member_id,
                 "reason_digest": medical_request_digest({"reason": reason}, business_id=business_id)}, operation=operation)
    item.refresh_from_db()
    return item, result.replayed
