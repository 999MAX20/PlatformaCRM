from dataclasses import dataclass

from django.db import transaction
from rest_framework.exceptions import NotFound, PermissionDenied, ValidationError

from apps.branches.models import Branch
from apps.businesses.access import Actions, Resources, assert_can
from apps.businesses.models import Business
from .appointment_access import assert_appointment_medical_basis
from .correction_access_context import assert_correction_access, scoped_request
from .models import MedicalAttachment, MedicalCorrectionAccess, PatientProfile
from .participation_access import assert_treatment_medical_basis
from .role_access import MedicalRoleContext, assert_medical_branch_permission, assert_medical_role_permission


@dataclass(frozen=True)
class FileAccessContext:
    business: Business
    patient: PatientProfile
    branch: Branch
    role: MedicalRoleContext
    correction: MedicalCorrectionAccess | None = None
    head_scope: bool = False

    def files(self):
        query = MedicalAttachment.objects.filter(business=self.business, patient=self.patient,
            record__business=self.business, record__patient=self.patient,
            attachment__business=self.business, attachment__entity_type="medical_attachment")
        if self.head_scope:
            query = query.filter(branch=self.branch)
        if self.correction is not None:
            query = query.filter(encounter_id=self.correction.encounter_id)
        return query


@transaction.atomic
def medical_file_context(*, actor, business_id, patient_id, action="view", appointment_id=None,
                         participation_id=None, correction_access_id=None, head_branch_id=None):
    basis = (appointment_id, participation_id, correction_access_id, head_branch_id)
    if sum(value is not None for value in basis) != 1:
        raise ValidationError({"basis": "Select one current medical access basis."})
    if any(type(value) is not int or value <= 0 for value in (business_id, patient_id, *(x for x in basis if x is not None))):
        raise ValidationError({"scope": "Provide positive medical scope identifiers."})
    if action not in {"view", "create", "export"}:
        raise PermissionDenied()
    business = Business.objects.select_for_update().filter(pk=business_id).first()
    if business is None:
        raise NotFound()
    role = assert_medical_role_permission(actor, business, "medical_files", action)
    if role.kind not in {"doctor", "head"}:
        raise PermissionDenied()
    assert_medical_role_permission(actor, business, "medical_records", "view")
    patient = PatientProfile.objects.select_for_update().select_related("client").filter(
        pk=patient_id, business=business, client__business=business).first()
    if patient is None:
        raise NotFound()
    assert_can(actor, business, Resources.CLIENTS, Actions.VIEW, obj=patient.client)
    correction = None
    if appointment_id is not None:
        access = assert_appointment_medical_basis(actor=actor, business=business, patient_id=patient_id,
            appointment_id=appointment_id, resource="medical_files", action=action)
        branch_id = access.branch_id
    elif participation_id is not None:
        access = assert_treatment_medical_basis(actor=actor, business=business, patient_id=patient_id,
            participation_id=participation_id, resource="medical_files", action=action)
        branch_id = access.branch_id
    elif correction_access_id is not None:
        item = scoped_request(actor, business, correction_access_id)
        if item.patient_id != patient_id or item.document_id is not None:
            raise PermissionDenied()
        correction = assert_correction_access(actor=actor, business=business, request_id=item.pk,
            encounter_id=item.encounter_id, action="update" if action == "create" else "view")
        branch_id = item.encounter.branch_id
    else:
        if role.kind != "head":
            raise PermissionDenied()
        branch_id = head_branch_id
    branch = Branch.objects.filter(pk=branch_id, business=business).first()
    assert_medical_branch_permission(actor, business, "medical_files", action, branch=branch)
    assert_medical_branch_permission(actor, business, "medical_records", "view", branch=branch)
    return FileAccessContext(business, patient, branch, role, correction, head_branch_id is not None)
