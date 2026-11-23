import json

from django.db import transaction
from rest_framework.exceptions import PermissionDenied

from apps.core.domain_errors import InvalidTransition
from apps.core.idempotency import CRMCommandResult, run_idempotent_crm_command
from .audit import write_patient_audit
from .correction_access_context import command_values, positive
from .document_artifact_access import document_artifact_access
from .document_content import append_document_text_correction
from .identity_crypto import decrypt_medical_value, encrypt_medical_value, medical_request_digest, MedicalDataUnavailable
from .models import MedicalDocumentCorrection, MedicalDocumentFinalization, MedicalDocumentRevision


def correction_source(version):
    from .document_finalization_services import finalization_evidence
    link = MedicalDocumentCorrection.objects.select_related("source__version__document", "version__document").filter(version=version).first()
    if link is None:
        return None
    expected = {"version": version.pk, "source": link.source_id, "author": version.author_id}
    try:
        proof = json.loads(decrypt_medical_value(link.evidence_encrypted,
            business_id=version.document.business_id, subject_id=version.pk, purpose="document_correction"))
        if (proof != expected or link.source.version.document_id != version.document_id
                or link.source.version.revision >= version.revision):
            raise ValueError
    except (ValueError, TypeError):
        raise MedicalDataUnavailable() from None
    finalization_evidence(link.source)
    return link.source


def link_correction(version, source):
    MedicalDocumentCorrection.objects.create(version=version, source=source,
        evidence_encrypted=encrypt_medical_value(json.dumps({"version": version.pk,
            "source": source.pk, "author": version.author_id}, sort_keys=True),
            business_id=version.document.business_id, subject_id=version.pk, purpose="document_correction"))


def reviewable_encounter(version):
    return (version.document.encounter.record.state == "active" and
        (version.document.encounter.state == "draft" or correction_source(version) is not None))


def document_version_state(version):
    if MedicalDocumentFinalization.objects.filter(version=version).exists():
        return "finalized"
    if version.revision == version.document.revision:
        return version.document.state
    return version.review_transitions.order_by("-state_revision").values_list("state", flat=True).first() or "draft"


def append_final_correction(*, document, author, document_text, reason):
    from .document_finalization_services import finalization_evidence
    source = MedicalDocumentFinalization.objects.select_related("version__document").filter(
        version__document=document, version__revision=document.revision).first()
    if document.state != "finalized" or source is None or document.encounter.record.state != "active":
        raise InvalidTransition("Select the current finalized version for correction.")
    finalization_evidence(source)
    document.state = "draft"
    document.state_revision += 1
    document.save(update_fields=["state", "state_revision", "updated_at"])
    version = append_document_text_correction(document=document, author=author, document_text=document_text, reason=reason,
        correction_origin=source)
    return version


@transaction.atomic
def correct_final_document(*, actor, business_id, patient_id, version_id, expected_state_revision,
                           document_text, reason, idempotency_key, **basis):
    from .document_review_services import _assert_review_writer
    reason = command_values(reason, idempotency_key)
    positive(expected_state_revision=expected_state_revision)
    context = document_artifact_access(actor=actor, business_id=business_id, patient_id=patient_id,
        version_id=version_id, **basis)
    if basis.get("head_branch_id") is not None:
        raise PermissionDenied()
    _assert_review_writer(context, actor, basis.get("appointment_id"), basis.get("participation_id"))
    document = context.version.document

    def operation():
        if document.state_revision != expected_state_revision or document.revision != context.version.revision:
            raise InvalidTransition("The document changed; reload its current version.")
        if document.state == "draft" and correction_source(context.version) is not None:
            if document.encounter.record.state != "active":
                raise InvalidTransition("The clinical record is inactive.")
            version = append_document_text_correction(document=document, author=actor, document_text=document_text, reason=reason)
        else:
            version = append_final_correction(document=document, author=actor, document_text=document_text, reason=reason)
        write_patient_audit(actor=actor, business=context.business, patient=context.patient,
            action="document_draft_saved", document_version=version, correction_access=context.correction)
        return CRMCommandResult(data={}, resource=version)

    result = run_idempotent_crm_command(business=context.business, actor=actor, action="medical.document.correct_final",
        idempotency_key=medical_request_digest({"key": idempotency_key}, business_id=business_id),
        payload={"version": version_id, "state_revision": expected_state_revision, "basis": basis,
            "digest": medical_request_digest({"text": document_text, "reason": reason}, business_id=business_id)}, operation=operation)
    return MedicalDocumentRevision.objects.get(pk=result.resource_id if result.replayed else result.resource.pk,
        document__business=context.business), result.replayed
