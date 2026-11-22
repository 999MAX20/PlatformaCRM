from django.db import transaction
from rest_framework.exceptions import PermissionDenied, ValidationError

from .common_template_services import read_approved_template_version
from .audit import write_patient_audit
from .document_reads import document_workspace_access
from .document_rendering import DOCUMENT_FIELDS, document_source_context, document_source_digest, render_document_text
from .identity_crypto import MedicalDataUnavailable
from .models import MedicalDocument, MedicalEncounter, MedicalEncounterRevision


@transaction.atomic
def preview_document_template(*, actor, business_id, patient_id, encounter_id, template_version_id,
                              appointment_id=None, participation_id=None, document_id=None):
    ids = [template_version_id] + ([document_id] if document_id is not None else [])
    if any(type(value) is not int or value < 1 for value in ids):
        raise ValidationError({"document": "Provide valid identifiers."})
    access = document_workspace_access(actor=actor, business_id=business_id, patient_id=patient_id,
        encounter_id=encounter_id, appointment_id=appointment_id, participation_id=participation_id)
    if not access["actions"]["update" if document_id is not None else "create"]:
        raise PermissionDenied()
    encounter = MedicalEncounter.objects.select_related("business", "branch", "record", "primary_clinician__user").get(
        pk=encounter_id, business_id=business_id, patient_id=patient_id)
    approved = read_approved_template_version(actor=actor, business_id=business_id, version_id=template_version_id)
    if document_id is not None and not MedicalDocument.objects.filter(pk=document_id,
            business_id=business_id, encounter=encounter, state="draft", template_code=approved["template"]["code"]).exists():
        raise PermissionDenied()
    source = MedicalEncounterRevision.objects.filter(encounter=encounter, revision=encounter.revision).first()
    if source is None:
        raise MedicalDataUnavailable()
    context = document_source_context(business=encounter.business, encounter=encounter, source=source)
    write_patient_audit(actor=actor, business=encounter.business, patient=encounter.patient,
        action="read", encounter_version=source)
    return {**render_document_text(approved["template"]["text"], context, started_at=encounter.started_at),
        "template": approved, "patient_revision": access["patient_revision"], "encounter_revision": access["encounter_revision"],
        "source_digest": document_source_digest(context=context, business_id=business_id, encounter_id=encounter_id,
            template_version_id=template_version_id, actor_id=actor.pk), "available_fields": DOCUMENT_FIELDS}
