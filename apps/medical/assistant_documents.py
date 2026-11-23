from django.db import transaction
from rest_framework.exceptions import PermissionDenied, ValidationError

from apps.businesses.models import Business
from .assistant_access import assert_assistant_appointment_basis
from .assistant_templates import read_assistant_template_source
from .audit import write_patient_audit
from .document_rendering import DOCUMENT_FIELDS, document_source_context, document_source_digest, render_document_text
from .document_services import document_version_payload
from .identity_crypto import MedicalDataUnavailable
from .models import MedicalDocument, MedicalDocumentRevision, MedicalEncounter, MedicalEncounterRevision


def assistant_document_context(*, actor, business_id, patient_id, encounter_id, invitation_id, action):
    """Caller holds an atomic transaction; this context never grants patient-wide history."""
    if any(type(value) is not int or value <= 0 for value in (business_id, patient_id, encounter_id, invitation_id)):
        raise ValidationError({"document": "Provide valid identifiers."})
    business = Business.objects.select_for_update().filter(pk=business_id).first()
    if business is None:
        raise PermissionDenied()
    encounter = MedicalEncounter.objects.select_related("patient", "branch", "record", "primary_clinician__user").filter(
        pk=encounter_id, business=business, patient_id=patient_id, patient__business=business,
        patient__client__business=business, state="draft", ended_at__isnull=True, record__state="active").first()
    if encounter is None:
        raise PermissionDenied()
    basis = assert_assistant_appointment_basis(actor=actor, business=business, patient_id=patient_id,
        appointment_id=encounter.appointment_id, invitation_id=invitation_id, resource="medical_documents", action=action)
    if encounter.primary_clinician_id != basis.primary_clinician_id or encounter.branch_id != basis.branch_id:
        raise PermissionDenied()
    encounter.clean()
    return business, encounter.patient, encounter


@transaction.atomic
def read_assistant_document_draft(*, actor, business_id, patient_id, encounter_id, invitation_id, document_id):
    if type(document_id) is not int or document_id <= 0:
        raise ValidationError({"document": "Provide a valid document identifier."})
    business, patient, encounter = assistant_document_context(actor=actor, business_id=business_id, patient_id=patient_id,
        encounter_id=encounter_id, invitation_id=invitation_id, action="update")
    document = MedicalDocument.objects.filter(pk=document_id, business=business, encounter=encounter, state="draft").first()
    if document is None:
        raise PermissionDenied()
    version = MedicalDocumentRevision.objects.select_related("document").filter(document=document, revision=document.revision).first()
    if version is None:
        raise MedicalDataUnavailable()
    return document_version_payload(actor=actor, business=business, patient=patient, version=version)


@transaction.atomic
def preview_assistant_document_template(*, actor, business_id, patient_id, encounter_id, invitation_id,
                                        template_version_id, document_id=None):
    identifiers = [template_version_id] + ([document_id] if document_id is not None else [])
    if any(type(value) is not int or value <= 0 for value in identifiers):
        raise ValidationError({"document": "Provide valid identifiers."})
    business, patient, encounter = assistant_document_context(actor=actor, business_id=business_id, patient_id=patient_id,
        encounter_id=encounter_id, invitation_id=invitation_id, action="update" if document_id is not None else "create")
    approved = read_assistant_template_source(actor=actor, business=business, version_id=template_version_id)
    if document_id is not None and not MedicalDocument.objects.filter(pk=document_id, business=business,
            encounter=encounter, state="draft", template_code=approved["template"]["code"]).exists():
        raise PermissionDenied()
    source = MedicalEncounterRevision.objects.filter(encounter=encounter, revision=encounter.revision).first()
    if source is None:
        raise MedicalDataUnavailable()
    context = document_source_context(business=business, encounter=encounter, source=source)
    write_patient_audit(actor=actor, business=business, patient=patient, action="read", encounter_version=source)
    return {**render_document_text(approved["template"]["text"], context, started_at=encounter.started_at),
        "template": approved, "patient_revision": patient.revision, "encounter_revision": encounter.revision,
        "source_digest": document_source_digest(context=context, business_id=business_id, encounter_id=encounter_id,
            template_version_id=template_version_id, actor_id=actor.pk), "available_fields": DOCUMENT_FIELDS}
