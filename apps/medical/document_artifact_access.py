from dataclasses import dataclass

from django.db import transaction
from rest_framework.exceptions import NotFound, PermissionDenied, ValidationError

from apps.branches.models import Branch
from apps.businesses.access import Actions, Resources, assert_can
from apps.businesses.models import Business
from .appointment_access import assert_appointment_medical_basis
from .correction_access_context import assert_correction_access, scoped_request
from .models import MedicalCorrectionAccess, MedicalDocumentRevision, PatientProfile
from .participation_access import assert_treatment_medical_basis
from .role_access import assert_medical_branch_permission, assert_medical_role_permission


@dataclass(frozen=True)
class DocumentArtifactAccess:
    business: Business
    patient: PatientProfile
    version: MedicalDocumentRevision
    correction: MedicalCorrectionAccess | None


def document_artifact_can_export(**scope):
    try:
        document_artifact_access(action="export", **scope)
        return True
    except PermissionDenied:
        return False


@transaction.atomic
def document_artifact_access(*, actor, business_id, patient_id, version_id, action="view",
                             appointment_id=None, participation_id=None, correction_access_id=None,
                             head_branch_id=None):
    """Current basis only; caller holds the encompassing generation/read/audit transaction."""
    bases = (appointment_id, participation_id, correction_access_id, head_branch_id)
    if sum(value is not None for value in bases) != 1:
        raise ValidationError({"basis": "Select one current medical access basis."})
    if any(type(value) is not int or value <= 0 for value in
           (business_id, patient_id, version_id, *(value for value in bases if value is not None))):
        raise ValidationError({"scope": "Provide positive medical scope identifiers."})
    if action not in {"view", "export"}:
        raise PermissionDenied()
    business = Business.objects.select_for_update().filter(pk=business_id).first()
    if business is None:
        raise NotFound()
    role = assert_medical_role_permission(actor, business, "medical_documents", action)
    assert_medical_role_permission(actor, business, "medical_documents", "view")
    assert_medical_role_permission(actor, business, "medical_records", "view")
    if role.kind not in {"doctor", "head"}:
        raise PermissionDenied()
    patient = PatientProfile.objects.select_for_update().select_related("client").filter(
        pk=patient_id, business=business, client__business=business).first()
    if patient is None:
        raise NotFound()
    assert_can(actor, business, Resources.CLIENTS, Actions.VIEW, obj=patient.client)
    version = MedicalDocumentRevision.objects.select_related("document__encounter__branch").filter(
        pk=version_id, document__business=business, document__encounter__business=business,
        document__encounter__patient=patient).first()
    if version is None:
        raise PermissionDenied()
    document = version.document
    document.clean()
    if version.revision > document.revision:
        raise PermissionDenied()
    correction = None
    if appointment_id is not None:
        basis = assert_appointment_medical_basis(actor=actor, business=business, patient_id=patient_id,
            appointment_id=appointment_id, resource="medical_documents", action=action)
        branch_id = basis.branch_id
    elif participation_id is not None:
        basis = assert_treatment_medical_basis(actor=actor, business=business, patient_id=patient_id,
            participation_id=participation_id, resource="medical_documents", action=action)
        branch_id = basis.branch_id
    elif correction_access_id is not None:
        request = scoped_request(actor, business, correction_access_id)
        if request.patient_id != patient.pk or request.document_id != document.pk:
            raise PermissionDenied()
        correction = assert_correction_access(actor=actor, business=business, request_id=request.pk,
            encounter_id=document.encounter_id, document_id=document.pk, action=action)
        branch_id = document.encounter.branch_id
    else:
        if role.kind != "head" or document.encounter.branch_id != head_branch_id:
            raise PermissionDenied()
        branch_id = head_branch_id
    branch = Branch.objects.filter(pk=branch_id, business=business).first()
    for resource, permission in (("medical_documents", action), ("medical_documents", "view"),
                                 ("medical_records", "view")):
        assert_medical_branch_permission(actor, business, resource, permission, branch=branch)
    return DocumentArtifactAccess(business, patient, version, correction)
