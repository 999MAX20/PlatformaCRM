from dataclasses import dataclass

from django.db.models import F
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied

from .assistant_lifecycle import appointment_basis_end_reason
from .models import AppointmentAssistant
from .role_access import assert_medical_branch_permission


@dataclass(frozen=True)
class AssistantAppointmentBasis:
    invitation_id: int
    appointment_id: int
    patient_id: int
    branch_id: int
    assignment_id: int
    primary_clinician_id: int


def assert_assistant_appointment_basis(*, actor, business, patient_id, appointment_id, invitation_id,
                                      resource="medical_records", action="view"):
    """One-appointment prerequisite; callers still scope and audit the clinical operation."""
    if (not actor or not actor.is_authenticated or business is None or
            any(type(value) is not int or value <= 0 for value in (patient_id, appointment_id, invitation_id))):
        raise PermissionDenied()
    item = AppointmentAssistant.objects.select_related(
        "branch", "appointment__resource", "patient", "primary_clinician__user").filter(
        pk=invitation_id, business_id=business.pk, patient_id=patient_id, appointment_id=appointment_id,
        patient__business_id=business.pk, patient__client__business_id=business.pk,
        appointment__business_id=business.pk, appointment__service__business_id=business.pk,
        appointment__end_at__gt=F("appointment__start_at"),
        branch__business_id=business.pk, primary_clinician__business_id=business.pk,
        primary_clinician__is_active=True, assignment__member__business_id=business.pk,
        assignment__member__user_id=actor.pk, state="active", accepted_at__lte=timezone.now(),
        accepted_at__gte=F("invited_at"), closed_at__isnull=True, closed_by__isnull=True).first()
    if item is None or appointment_basis_end_reason(item) is not None:
        raise PermissionDenied()
    context = assert_medical_branch_permission(actor, business, resource, action, branch=item.branch)
    if context.kind != "assistant" or context.assignment_id != item.assignment_id:
        raise PermissionDenied()
    primary = assert_medical_branch_permission(item.primary_clinician.user, business, "medical_records", "view", branch=item.branch)
    if primary.kind not in ("doctor", "head"):
        raise PermissionDenied()
    return AssistantAppointmentBasis(item.pk, appointment_id, patient_id, item.branch_id,
                                     context.assignment_id, item.primary_clinician_id)
