from django.db import transaction
from django.db.models import OuterRef, Subquery
from rest_framework.exceptions import PermissionDenied, ValidationError

from apps.businesses.models import Business
from apps.core.domain_errors import InvalidTransition
from .assistant_access import assert_assistant_appointment_basis
from .assistant_documents import assistant_document_context
from .assistant_selectors import _pagination
from .audit import write_patient_audit
from .clinical_identity import assert_verified_clinical_identity
from .document_services import document_version_payload
from .identity_crypto import MedicalDataUnavailable
from .models import AppointmentAssistant, MedicalEncounter, MedicalDocument, MedicalDocumentRevision, MedicalDocumentTemplateRevision
from .template_services import read_template_version_payload


def _invitation_context(actor, business_id, invitation_id):
    if any(type(value) is not int or value <= 0 for value in (business_id, invitation_id)):
        raise ValidationError({"invitation": "Provide valid identifiers."})
    if not actor or not actor.is_authenticated:
        raise PermissionDenied()
    business = Business.objects.select_for_update().filter(pk=business_id).first()
    item = AppointmentAssistant.objects.select_related("patient__client", "appointment", "branch", "primary_clinician__user").filter(
        pk=invitation_id, business=business, assignment__member__user_id=actor.pk).first() if business else None
    if item is None:
        raise PermissionDenied()
    assert_assistant_appointment_basis(actor=actor, business=business, patient_id=item.patient_id,
        appointment_id=item.appointment_id, invitation_id=item.pk)
    return business, item


def _draft_context(actor, business_id, invitation_id, action):
    business, item = _invitation_context(actor, business_id, invitation_id)
    encounter = MedicalEncounter.objects.filter(business=business, patient_id=item.patient_id,
        appointment_id=item.appointment_id, primary_clinician_id=item.primary_clinician_id, branch_id=item.branch_id).first()
    if encounter is None:
        raise PermissionDenied()
    return assistant_document_context(actor=actor, business_id=business_id, patient_id=item.patient_id,
        encounter_id=encounter.pk, invitation_id=invitation_id, action=action)


@transaction.atomic
def read_assistant_workspace(*, actor, business_id, invitation_id):
    business, item = _invitation_context(actor, business_id, invitation_id)
    encounter = MedicalEncounter.objects.filter(business=business, patient_id=item.patient_id,
        appointment_id=item.appointment_id, primary_clinician_id=item.primary_clinician_id, branch_id=item.branch_id).first()
    actions = {"create": False, "update": False}
    if encounter is not None:
        for action in actions:
            try:
                _, patient, _ = assistant_document_context(actor=actor, business_id=business_id, patient_id=item.patient_id,
                    encounter_id=encounter.pk, invitation_id=invitation_id, action=action)
                assert_verified_clinical_identity(patient)
                actions[action] = True
            except (PermissionDenied, InvalidTransition):
                pass
    write_patient_audit(actor=actor, business=business, patient=item.patient, action="read")
    return {"invitation_id": item.pk, "business_id": business.pk, "patient_id": item.patient_id,
        "patient_name": item.patient.client.full_name, "patient_revision": item.patient.revision,
        "appointment_id": item.appointment_id, "start_at": item.appointment.start_at,
        "branch_name": item.branch.name, "clinician_name": item.primary_clinician.user.full_name,
        "encounter_id": encounter.pk if encounter else None, "encounter_revision": encounter.revision if encounter else None,
        "actions": actions}


@transaction.atomic
def list_assistant_drafts(*, actor, business_id, invitation_id, before_id=None, limit=20):
    _pagination(before_id, limit)
    business, patient, encounter = _draft_context(actor, business_id, invitation_id, "update")
    documents = MedicalDocument.objects.filter(business=business, encounter=encounter, state="draft", revision__gte=1)
    if before_id is not None:
        documents = documents.filter(pk__lt=before_id)
    page = list(documents.order_by("-pk")[:limit + 1])
    rows = []
    for document in page[:limit]:
        version = MedicalDocumentRevision.objects.select_related("document").filter(document=document, revision=document.revision).first()
        if version is None:
            raise MedicalDataUnavailable()
        payload = document_version_payload(actor=actor, business=business, patient=patient, version=version)
        rows.append({"id": document.pk, "version_id": version.pk, "revision": version.revision,
            "title": payload["snapshot"]["template"]["title"], "created_at": version.created_at,
            "prepared_by": payload["snapshot"]["prepared_by"], "state": document.state})
    return {"results": rows, "next_before_id": page[limit - 1].pk if len(page) > limit else None}


@transaction.atomic
def list_assistant_templates(*, actor, business_id, invitation_id, before_id=None, limit=20):
    _pagination(before_id, limit)
    business, _, _ = _draft_context(actor, business_id, invitation_id, "create")
    latest = MedicalDocumentTemplateRevision.objects.filter(template_id=OuterRef("template_id"),
        review__state="approved").order_by("-revision").values("pk")[:1]
    versions = MedicalDocumentTemplateRevision.objects.select_related("template").filter(template__business=business,
        template__owner_member__isnull=True, template__is_active=True, pk=Subquery(latest))
    if before_id is not None:
        versions = versions.filter(template_id__lt=before_id)
    page = list(versions.order_by("-template_id")[:limit + 1])
    rows = []
    for version in page[:limit]:
        payload = read_template_version_payload(actor=actor, business=business, version=version)
        rows.append({"template_id": version.template_id, "version_id": version.pk, "revision": version.revision,
                     "title": payload["template"]["title"]})
    return {"results": rows, "next_before_id": page[limit - 1].template_id if len(page) > limit else None}
