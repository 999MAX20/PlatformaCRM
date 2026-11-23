from django.contrib.auth import get_user_model
from rest_framework.exceptions import PermissionDenied, ValidationError

from apps.businesses.models import Business, BusinessMember
from apps.scheduling.models import Appointment, Resource
from .models import MedicalEncounter, PatientProfile
from .role_access import assert_medical_branch_permission


def assistant_management_context(*, actor, business_id, patient_id, appointment_id):
    """Caller holds an atomic transaction for the shared scheduling Business lock."""
    if any(type(value) is not int or value <= 0 for value in (business_id, patient_id, appointment_id)):
        raise ValidationError({"invitation": "Provide valid identifiers."})
    if not actor or not actor.is_authenticated:
        raise PermissionDenied()
    actor = get_user_model().objects.filter(pk=actor.pk, is_active=True).first()
    business = Business.objects.select_for_update().filter(pk=business_id).first()
    if actor is None or business is None:
        raise PermissionDenied()
    appointment = Appointment.objects.select_for_update().select_related("branch", "resource").filter(
        pk=appointment_id, business=business, branch__business=business, service__business=business,
        client__business=business, resource__business=business, resource__resource_type=Resource.ResourceTypes.STAFF,
        is_archived=False, status__in=["created", "confirmed", "rescheduled"]).first()
    if appointment is None or appointment.end_at <= appointment.start_at:
        raise PermissionDenied()
    permission = assert_medical_branch_permission(actor, business, "medical_participation", "create", branch=appointment.branch)
    if permission.kind != "head" and not (permission.kind == "doctor" and appointment.resource.linked_user_id == actor.pk):
        raise PermissionDenied()
    patient = PatientProfile.objects.filter(pk=patient_id, business=business, client_id=appointment.client_id).first()
    if patient is None or MedicalEncounter.objects.filter(appointment=appointment).exclude(state="draft", ended_at__isnull=True).exists():
        raise PermissionDenied()
    primary = BusinessMember.objects.select_related("user").filter(business=business,
        user_id=appointment.resource.linked_user_id, is_active=True).first()
    if primary is None:
        raise PermissionDenied()
    clinician_role = assert_medical_branch_permission(primary.user, business, "medical_records", "view", branch=appointment.branch)
    if clinician_role.kind not in ("doctor", "head"):
        raise PermissionDenied()
    return actor, business, patient, appointment, primary
