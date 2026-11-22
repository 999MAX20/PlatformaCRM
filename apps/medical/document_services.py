from django.db import transaction
from rest_framework.exceptions import NotFound, PermissionDenied, ValidationError

from apps.businesses.models import Business
from apps.core.domain_errors import InvalidTransition
from apps.core.idempotency import CRMCommandResult, run_idempotent_crm_command
from .appointment_access import assert_appointment_medical_basis
from .audit import write_patient_audit
from .clinical_identity import assert_verified_clinical_identity
from .document_content import append_document_revision, read_document_revision, validate_document_template
from .identity_crypto import MedicalDataUnavailable, medical_request_digest
from .models import MedicalDocument, MedicalDocumentRevision, MedicalEncounter, MedicalEncounterRevision, PatientProfile
from .participation_access import assert_treatment_medical_basis
from .role_access import assert_medical_branch_permission, assert_medical_role_permission


@transaction.atomic
def save_primary_document_draft(*, actor, business_id, patient_id, encounter_id,
                                expected_encounter_revision, expected_patient_revision,
                                template, idempotency_key, document_id=None,
                                expected_document_revision=None, participation_id=None, reason=""):
    """Save a primary clinician's draft; template input does not certify an official form."""
    identifiers = [business_id, patient_id, encounter_id, expected_encounter_revision, expected_patient_revision]
    if document_id is not None:
        identifiers += [document_id, expected_document_revision]
    elif expected_document_revision is not None:
        raise ValidationError({"document": "A new document has no expected document revision."})
    if participation_id is not None:
        identifiers.append(participation_id)
    if any(type(value) is not int or value <= 0 for value in identifiers):
        raise ValidationError({"document": "Provide valid identifiers and revisions."})
    if not isinstance(idempotency_key, str) or not idempotency_key.strip() or len(idempotency_key) > 128:
        raise ValidationError({"idempotency_key": "Provide an idempotency key of at most 128 characters."})
    if not isinstance(reason, str) or len(reason) > 2000:
        raise ValidationError({"reason": "Provide a reason of at most 2000 characters."})
    template = validate_document_template(template, template.get("code") if isinstance(template, dict) else None)
    business = Business.objects.select_for_update().filter(pk=business_id).first()
    if business is None:
        raise NotFound()
    action = "update" if document_id is not None else "create"
    context = assert_medical_role_permission(actor, business, "medical_documents", action)
    patient = PatientProfile.objects.select_for_update().filter(pk=patient_id,
        business=business, client__business_id=business_id).first()
    if patient is None:
        raise NotFound()
    encounter = MedicalEncounter.objects.select_for_update().filter(pk=encounter_id,
        business=business, patient=patient, primary_clinician_id=context.member_id).first()
    if encounter is None:
        raise PermissionDenied()
    encounter.clean()
    assert_medical_branch_permission(actor, business, "medical_documents", action, branch=encounter.branch)
    if participation_id is None:
        assert_appointment_medical_basis(actor=actor, business=business, patient_id=patient_id,
            appointment_id=encounter.appointment_id, resource="medical_documents", action=action)
    else:
        basis = assert_treatment_medical_basis(actor=actor, business=business, patient_id=patient_id,
            participation_id=participation_id, resource="medical_documents", action=action)
        if basis.branch_id != encounter.branch_id:
            raise PermissionDenied()
    assert_verified_clinical_identity(patient)
    document = None
    if document_id is not None:
        document = MedicalDocument.objects.select_for_update().filter(pk=document_id,
            business=business, encounter=encounter).first()
        if document is None:
            raise PermissionDenied()

    def operation():
        if (encounter.revision != expected_encounter_revision or patient.revision != expected_patient_revision
                or encounter.state != "draft" or encounter.record.state != "active"):
            raise InvalidTransition("The patient or encounter changed; reload its current revision.")
        if document is not None and (document.revision != expected_document_revision or
                document.state != "draft" or document.template_code != template["code"]):
            raise InvalidTransition("The document changed; reload its current revision.")
        source = MedicalEncounterRevision.objects.filter(encounter=encounter, revision=encounter.revision).first()
        if source is None:
            raise MedicalDataUnavailable()
        draft = document or MedicalDocument.objects.create(business=business, encounter=encounter,
                                                            template_code=template["code"])
        version = append_document_revision(document=draft, source_version=source, author=actor,
                                           template=template, reason=reason)
        write_patient_audit(actor=actor, business=business, patient=patient,
            action="document_draft_saved" if document is not None else "document_draft_created",
            document_version=version)
        return CRMCommandResult(data={}, status_code=200 if document is not None else 201, resource=version)

    result = run_idempotent_crm_command(business=business, actor=actor, action="medical.document." + action,
        idempotency_key=medical_request_digest({"key": idempotency_key}, business_id=business_id),
        payload={"patient": patient_id, "encounter": encounter_id, "document": document_id,
            "patient_revision": expected_patient_revision, "encounter_revision": expected_encounter_revision,
            "document_revision": expected_document_revision, "participation": participation_id,
            "content_digest": medical_request_digest({"template": template, "reason": reason}, business_id=business_id)},
        operation=operation)
    version = MedicalDocumentRevision.objects.get(document__business=business, document__encounter=encounter,
        pk=result.resource_id if result.replayed else result.resource.pk)
    return version, result.replayed


@transaction.atomic
def read_document_for_treating_clinician(*, actor, business_id, patient_id, version_id,
                                       appointment_id=None, participation_id=None):
    if (appointment_id is None) == (participation_id is None):
        raise ValidationError({"basis": "Select one current treatment access basis."})
    ids = [business_id, patient_id, version_id, appointment_id if appointment_id is not None else participation_id]
    if any(type(value) is not int or value <= 0 for value in ids):
        raise ValidationError({"document": "Provide valid identifiers."})
    business = Business.objects.select_for_update().filter(pk=business_id).first()
    if business is None:
        raise NotFound()
    assert_medical_role_permission(actor, business, "medical_documents", "view")
    patient = PatientProfile.objects.select_for_update().filter(pk=patient_id,
        business=business, client__business_id=business_id).first()
    if patient is None:
        raise NotFound()
    if appointment_id is not None:
        assert_appointment_medical_basis(actor=actor, business=business, patient_id=patient_id,
            appointment_id=appointment_id, resource="medical_documents")
    else:
        assert_treatment_medical_basis(actor=actor, business=business, patient_id=patient_id,
            participation_id=participation_id, resource="medical_documents")
    version = MedicalDocumentRevision.objects.select_related("document").filter(pk=version_id,
        document__business=business, document__encounter__business=business,
        document__encounter__patient=patient).first()
    if version is None:
        raise PermissionDenied()
    write_patient_audit(actor=actor, business=business, patient=patient, action="read", document_version=version)
    snapshot = read_document_revision(version)
    return {"version_id": version.pk, "document_id": version.document_id, "revision": version.revision,
        "state": version.document.state, "created_at": version.created_at, "snapshot": snapshot}
