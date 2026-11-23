from django.db import transaction
from rest_framework.exceptions import PermissionDenied, ValidationError

from .common_template_services import read_approved_template_version
from .document_rendering import document_source_context, document_source_digest, render_document_text
from .encounter_reads import read_encounter_for_treating_clinician
from .identity_crypto import MedicalDataUnavailable
from .models import MedicalEncounter, MedicalEncounterRevision, MedicalOrder, MedicalTemplateReview


def order_template_source(*, actor, encounter, template_version_id, participation_id=None):
    if type(template_version_id) is not int or template_version_id <= 0:
        raise ValidationError({"template_version_id": "Provide an approved template version."})
    encounter = MedicalEncounter.objects.select_related("business", "branch", "record", "primary_clinician__user").get(
        pk=encounter.pk, business_id=encounter.business_id, patient_id=encounter.patient_id)
    source = MedicalEncounterRevision.objects.filter(encounter=encounter, revision=encounter.revision).first()
    if source is None:
        raise MedicalDataUnavailable()
    read_encounter_for_treating_clinician(actor=actor, business_id=encounter.business_id,
        patient_id=encounter.patient_id, version_id=source.pk,
        appointment_id=encounter.appointment_id if participation_id is None else None,
        participation_id=participation_id)
    approved = read_approved_template_version(actor=actor, business_id=encounter.business_id,
                                              version_id=template_version_id)
    review = MedicalTemplateReview.objects.get(version_id=template_version_id, state="approved")
    context = document_source_context(business=encounter.business, encounter=encounter, source=source)
    digest = document_source_digest(context=context, business_id=encounter.business_id,
        encounter_id=encounter.pk, template_version_id=template_version_id, actor_id=actor.pk)
    provenance = {"template": approved["template"], "approval": {
        "template_id": approved["template_id"], "version_id": template_version_id,
        "revision": approved["revision"], "review_id": review.pk,
        "approved_by": review.decided_by_id, "approved_at": review.decided_at.isoformat()},
        "source_digest": digest}
    return source, provenance, context


@transaction.atomic
def preview_order_template(*, actor, business_id, patient_id, encounter_id, template_version_id,
                           appointment_id=None, participation_id=None, order_id=None):
    from .order_reads import order_workspace_access
    access = order_workspace_access(actor=actor, business_id=business_id, patient_id=patient_id,
        encounter_id=encounter_id, appointment_id=appointment_id, participation_id=participation_id)
    if not access["actions"]["update" if order_id is not None else "create"]:
        raise PermissionDenied()
    encounter = MedicalEncounter.objects.select_related("business", "branch", "record", "primary_clinician__user").get(
        pk=encounter_id, business_id=business_id, patient_id=patient_id)
    if order_id is not None and not MedicalOrder.objects.filter(pk=order_id, encounter=encounter,
            business_id=business_id, author=actor, state="draft").exists():
        raise PermissionDenied()
    _, provenance, context = order_template_source(actor=actor, encounter=encounter,
        template_version_id=template_version_id, participation_id=participation_id)
    rendered = render_document_text(provenance["template"]["text"], context, started_at=encounter.started_at)
    if len(rendered["document_text"]) > 32768:
        raise ValidationError({"template": "The rendered order exceeds 32768 characters."})
    return {**rendered, "template_source": provenance,
        "patient_revision": access["patient_revision"], "encounter_revision": access["encounter_revision"]}
