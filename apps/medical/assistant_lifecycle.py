from django.db import transaction
from django.utils import timezone

from apps.businesses.models import Business
from apps.core.audit import write_actor_audit_log
from apps.core.models import AuditLog
from .models import AppointmentAssistant, MedicalEncounter


def appointment_basis_end_reason(item):
    appointment = item.appointment
    if appointment.business_id != item.business_id or appointment.client_id != item.patient.client_id:
        return "patient_changed"
    if appointment.is_archived:
        return "appointment_archived"
    if appointment.status not in ("created", "confirmed", "rescheduled"):
        return "appointment_ended"
    if appointment.branch_id != item.branch_id:
        return "branch_changed"
    resource = appointment.resource
    if (resource is None or resource.business_id != item.business_id or resource.resource_type != "staff"
            or resource.linked_user_id != item.primary_clinician.user_id):
        return "clinician_changed"
    if MedicalEncounter.objects.filter(appointment_id=item.appointment_id).exclude(
            state="draft", ended_at__isnull=True).exists():
        return "encounter_ended"
    return None


@transaction.atomic
def end_invalid_assistant_invitations(*, business_id, appointment_id=None, resource_id=None):
    """Called synchronously inside the source domain command's transaction."""
    if appointment_id is None and resource_id is None:
        raise ValueError("An appointment or resource is required.")
    Business.objects.select_for_update().get(pk=business_id)
    items = AppointmentAssistant.objects.select_for_update(of=("self",)).filter(
        business_id=business_id, state__in=["pending", "active"])
    if appointment_id is not None:
        items = items.filter(appointment_id=appointment_id)
    if resource_id is not None:
        items = items.filter(appointment__resource_id=resource_id)
    items = items.select_related("appointment__resource", "patient", "primary_clinician")
    for item in items.order_by("pk"):
        reason = appointment_basis_end_reason(item)
        if reason is None:
            continue
        item.state, item.closed_at = "ended", timezone.now()
        item.revision += 1
        item.save(update_fields=["state", "closed_at", "revision"])
        write_actor_audit_log(actor=None, business=item.business, action=AuditLog.Actions.UPDATE, instance=item,
            metadata={"permission": True, "kind": "medical_assistant_basis_ended", "revision": item.revision,
                      "state": item.state, "reason": reason})
