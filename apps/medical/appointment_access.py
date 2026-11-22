from dataclasses import dataclass

from django.db.models import F
from rest_framework.exceptions import PermissionDenied

from apps.scheduling.models import Appointment, Resource
from .models import MedicalRoleAssignment, PatientProfile
from .role_access import assert_medical_branch_permission, assert_medical_role_permission


@dataclass(frozen=True)
class AppointmentMedicalBasis:
    appointment_id: int
    patient_id: int
    branch_id: int
    assignment_id: int


def assert_assigned_medical_appointment(*, actor, business, appointment_id,
                                        resource="medical_records", action="view"):
    """Validate the assigned clinician before resolving a medical patient from a booking."""
    context = assert_medical_role_permission(actor, business, resource, action)
    if context.kind not in (MedicalRoleAssignment.Kinds.DOCTOR, MedicalRoleAssignment.Kinds.HEAD):
        raise PermissionDenied()
    if type(appointment_id) is not int:
        raise PermissionDenied()
    appointment = Appointment.objects.select_related("branch", "client").filter(
        pk=appointment_id, business_id=business.pk,
        client__business_id=business.pk, service__business_id=business.pk,
        branch__business_id=business.pk, resource__business_id=business.pk,
        resource__resource_type=Resource.ResourceTypes.STAFF,
        resource__linked_user_id=context.user_id, is_archived=False,
        status__in=(Appointment.Statuses.CREATED, Appointment.Statuses.CONFIRMED,
                    Appointment.Statuses.RESCHEDULED), end_at__gt=F("start_at"),
    ).first()
    if appointment is None:
        raise PermissionDenied()
    current = assert_medical_branch_permission(actor, business, resource, action, branch=appointment.branch)
    if current.kind not in (MedicalRoleAssignment.Kinds.DOCTOR, MedicalRoleAssignment.Kinds.HEAD):
        raise PermissionDenied()
    return appointment, current


def assert_appointment_medical_basis(*, actor, business, patient_id, appointment_id,
                                     resource="medical_records", action="view"):
    """One access prerequisite, not a clinical read, write permission or audit boundary."""
    if type(patient_id) is not int:
        raise PermissionDenied()
    appointment, context = assert_assigned_medical_appointment(actor=actor, business=business,
        appointment_id=appointment_id, resource=resource, action=action)
    if not PatientProfile.objects.filter(pk=patient_id, business_id=business.pk,
            client_id=appointment.client_id, client__business_id=business.pk).exists():
        raise PermissionDenied()
    return AppointmentMedicalBasis(appointment.pk, patient_id, appointment.branch_id, context.assignment_id)
