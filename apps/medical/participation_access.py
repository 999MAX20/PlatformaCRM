from dataclasses import dataclass

from django.db.models import F
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied

from .models import MedicalRoleAssignment, TreatmentParticipation
from .role_access import assert_medical_branch_permission


@dataclass(frozen=True)
class TreatmentMedicalBasis:
    participation_id: int
    patient_id: int
    branch_id: int
    assignment_id: int


def assert_treatment_medical_basis(*, actor, business, patient_id, participation_id,
                                   resource="medical_records", action="view"):
    """Active participation prerequisite; callers still authorize and audit each operation."""
    if (not actor or not actor.is_authenticated or business is None or
            type(patient_id) is not int or type(participation_id) is not int):
        raise PermissionDenied()
    participation = TreatmentParticipation.objects.select_related("branch").filter(
        pk=participation_id, patient_id=patient_id, patient__business_id=business.pk,
        patient__client__business_id=business.pk, member__business_id=business.pk,
        member__user_id=actor.pk, branch__business_id=business.pk, state="active",
        accepted_at__lte=timezone.now(), accepted_at__gte=F("proposed_at"),
        closed_at__isnull=True, closed_by__isnull=True,
    ).first()
    if participation is None:
        raise PermissionDenied()
    context = assert_medical_branch_permission(actor, business, resource, action, branch=participation.branch)
    if context.kind not in (MedicalRoleAssignment.Kinds.DOCTOR, MedicalRoleAssignment.Kinds.HEAD):
        raise PermissionDenied()
    return TreatmentMedicalBasis(participation.pk, patient_id, participation.branch_id, context.assignment_id)
