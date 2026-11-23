from django.db import transaction
from django.db.models import F
from rest_framework.exceptions import PermissionDenied, ValidationError

from apps.core.domain_errors import InvalidTransition
from .audit import write_patient_audit
from .appointment_access import assert_appointment_medical_basis
from .clinical_identity import assert_verified_clinical_identity
from .document_services import document_read_context, document_version_payload
from .identity_crypto import MedicalDataUnavailable
from .models import MedicalDocument, MedicalDocumentRevision, MedicalEncounter
from .participation_access import assert_treatment_medical_basis
from .role_access import assert_medical_branch_permission


@transaction.atomic
def document_workspace_access(*, actor, business_id, patient_id, encounter_id,
                              appointment_id=None, participation_id=None):
    if type(encounter_id) is not int or encounter_id <= 0:
        raise ValidationError({"encounter": "Provide a valid encounter."})
    business, patient = document_read_context(actor=actor, business_id=business_id, patient_id=patient_id,
        appointment_id=appointment_id, participation_id=participation_id)
    encounter = MedicalEncounter.objects.select_related("branch", "record").filter(
        pk=encounter_id, business=business, patient=patient).first()
    if encounter is None:
        raise PermissionDenied()
    encounter.clean()

    def allowed(action):
        try:
            context = assert_medical_branch_permission(actor, business, "medical_documents", action, branch=encounter.branch)
            if encounter.primary_clinician_id != context.member_id or encounter.state != "draft" or encounter.record.state != "active":
                return False
            if participation_id is None:
                assert_appointment_medical_basis(actor=actor, business=business, patient_id=patient_id,
                    appointment_id=encounter.appointment_id, resource="medical_documents", action=action)
            else:
                basis = assert_treatment_medical_basis(actor=actor, business=business, patient_id=patient_id,
                    participation_id=participation_id, resource="medical_documents", action=action)
                if basis.branch_id != encounter.branch_id:
                    return False
            assert_verified_clinical_identity(patient)
            return True
        except (PermissionDenied, InvalidTransition):
            return False

    actions = {"view": True, "create": allowed("create"), "update": allowed("update")}
    write_patient_audit(actor=actor, business=business, patient=patient, action="read", record=encounter.record)
    return {"business_id": business.pk, "patient_id": patient.pk, "encounter_id": encounter.pk,
            "patient_revision": patient.revision, "encounter_revision": encounter.revision, "actions": actions}


def _page_arguments(cursor, limit):
    if cursor is not None and (type(cursor) is not int or cursor <= 0):
        raise ValidationError({"cursor": "Provide a valid cursor."})
    if type(limit) is not int or not 1 <= limit <= 50:
        raise ValidationError({"limit": "Select a page size from 1 to 50."})


@transaction.atomic
def list_patient_documents(*, actor, business_id, patient_id, appointment_id=None,
                           participation_id=None, encounter_id=None, before_id=None, limit=20, head_branch_id=None):
    _page_arguments(before_id, limit)
    business, patient = document_read_context(actor=actor, business_id=business_id, patient_id=patient_id,
        appointment_id=appointment_id, participation_id=participation_id, head_branch_id=head_branch_id)
    documents = MedicalDocument.objects.filter(business=business,
        encounter__business=business, encounter__patient=patient, revision__gte=1)
    if head_branch_id is not None:
        documents = documents.filter(encounter__branch_id=head_branch_id)
    if encounter_id is not None:
        if type(encounter_id) is not int or encounter_id <= 0:
            raise ValidationError({"encounter": "Provide a valid encounter."})
        encounters = MedicalEncounter.objects.filter(pk=encounter_id, business=business, patient=patient)
        if head_branch_id is not None:
            encounters = encounters.filter(branch_id=head_branch_id)
        if not encounters.exists():
            raise PermissionDenied()
        documents = documents.filter(encounter_id=encounter_id)
    if before_id is not None:
        documents = documents.filter(pk__lt=before_id)
    page = list(documents.order_by("-pk")[:limit + 1])
    versions = {version.document_id: version for version in MedicalDocumentRevision.objects.select_related("document").filter(
        document_id__in=[document.pk for document in page[:limit]], revision=F("document__revision"))}
    rows = []
    for document in page[:limit]:
        version = versions.get(document.pk)
        if version is None:
            raise MedicalDataUnavailable()
        payload = document_version_payload(actor=actor, business=business, patient=patient, version=version)
        rows.append({"document_id": document.pk, "version_id": version.pk, "revision": version.revision,
            "encounter_id": document.encounter_id, "state": document.state, "created_at": version.created_at,
            "title": payload["snapshot"]["template"]["title"]})
    return {"results": rows, "next_before_id": rows[-1]["document_id"] if len(page) > limit else None}


@transaction.atomic
def list_document_revisions(*, actor, business_id, patient_id, document_id, appointment_id=None,
                            participation_id=None, before_revision=None, limit=20, head_branch_id=None):
    _page_arguments(before_revision, limit)
    if type(document_id) is not int or document_id <= 0:
        raise ValidationError({"document": "Provide a valid document."})
    business, patient = document_read_context(actor=actor, business_id=business_id, patient_id=patient_id,
        appointment_id=appointment_id, participation_id=participation_id, head_branch_id=head_branch_id)
    document = MedicalDocument.objects.filter(pk=document_id, business=business,
        encounter__business=business, encounter__patient=patient).first()
    if document is None or (head_branch_id is not None and document.encounter.branch_id != head_branch_id):
        raise PermissionDenied()
    versions = MedicalDocumentRevision.objects.filter(document=document, revision__lte=document.revision)
    if not versions.filter(revision=document.revision).exists():
        raise MedicalDataUnavailable()
    if before_revision is not None:
        versions = versions.filter(revision__lt=before_revision)
    page = list(versions.order_by("-revision")[:limit + 1])
    rows = []
    for version in page[:limit]:
        write_patient_audit(actor=actor, business=business, patient=patient, action="read", document_version=version)
        rows.append({"version_id": version.pk, "revision": version.revision,
                     "author_id": version.author_id, "created_at": version.created_at})
    return {"document_id": document.pk, "current_revision": document.revision, "results": rows,
            "next_before_revision": rows[-1]["revision"] if len(page) > limit else None}
