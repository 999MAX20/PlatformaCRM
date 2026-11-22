from django.db import transaction
from django.db.models import F
from rest_framework.exceptions import PermissionDenied, ValidationError

from .audit import write_patient_audit
from .document_services import document_read_context, document_version_payload
from .identity_crypto import MedicalDataUnavailable
from .models import MedicalDocument, MedicalDocumentRevision, MedicalEncounter


def _page_arguments(cursor, limit):
    if cursor is not None and (type(cursor) is not int or cursor <= 0):
        raise ValidationError({"cursor": "Provide a valid cursor."})
    if type(limit) is not int or not 1 <= limit <= 50:
        raise ValidationError({"limit": "Select a page size from 1 to 50."})


@transaction.atomic
def list_patient_documents(*, actor, business_id, patient_id, appointment_id=None,
                           participation_id=None, encounter_id=None, before_id=None, limit=20):
    _page_arguments(before_id, limit)
    business, patient = document_read_context(actor=actor, business_id=business_id, patient_id=patient_id,
        appointment_id=appointment_id, participation_id=participation_id)
    documents = MedicalDocument.objects.filter(business=business,
        encounter__business=business, encounter__patient=patient, revision__gte=1)
    if encounter_id is not None:
        if type(encounter_id) is not int or encounter_id <= 0:
            raise ValidationError({"encounter": "Provide a valid encounter."})
        if not MedicalEncounter.objects.filter(pk=encounter_id, business=business, patient=patient).exists():
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
                            participation_id=None, before_revision=None, limit=20):
    _page_arguments(before_revision, limit)
    if type(document_id) is not int or document_id <= 0:
        raise ValidationError({"document": "Provide a valid document."})
    business, patient = document_read_context(actor=actor, business_id=business_id, patient_id=patient_id,
        appointment_id=appointment_id, participation_id=participation_id)
    document = MedicalDocument.objects.filter(pk=document_id, business=business,
        encounter__business=business, encounter__patient=patient).first()
    if document is None:
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
