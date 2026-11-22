from django.db import transaction
from rest_framework.exceptions import ValidationError

from apps.core.domain_errors import InvalidTransition
from apps.core.idempotency import CRMCommandResult, run_idempotent_crm_command
from .audit import write_patient_audit
from .clinical_identity import assert_verified_clinical_identity
from .correction_access_context import assert_correction_access, command_values, locked_business, positive, scoped_request
from .document_content import append_document_text_correction
from .encounter_services import save_primary_encounter_draft
from .identity_crypto import medical_request_digest
from .models import MedicalDocumentRevision


@transaction.atomic
def save_correction_target(*, actor, business_id, request_id, expected_revision, reason, idempotency_key,
                           content=None, document_text=None):
    reason = command_values(reason, idempotency_key)
    positive(expected_revision=expected_revision)
    business, _ = locked_business(actor, business_id)
    item = scoped_request(actor, business, request_id)
    assert_correction_access(actor=actor, business=business, request_id=request_id,
        encounter_id=item.encounter_id, document_id=item.document_id, action="update")
    if item.document_id is None:
        if document_text is not None:
            raise ValidationError({"document_text": "This request permits only the selected encounter."})
        return save_primary_encounter_draft(actor=actor, business_id=business_id, patient_id=item.patient_id,
            encounter_id=item.encounter_id, expected_revision=expected_revision, content=content,
            reason=reason, idempotency_key=idempotency_key, correction_access_id=item.pk)
    if content is not None or not isinstance(document_text, str) or len(document_text) > 131072:
        raise ValidationError({"document_text": "Provide only the corrected document text, at most 131072 characters."})
    assert_verified_clinical_identity(item.patient)

    def operation():
        if item.document.revision != expected_revision or item.document.state != "draft" or item.encounter.record.state != "active":
            raise InvalidTransition("The document changed; review its current draft.")
        version = append_document_text_correction(document=item.document, author=actor, document_text=document_text, reason=reason)
        write_patient_audit(actor=actor, business=business, patient=item.patient,
            action="document_draft_saved", document_version=version, correction_access=item)
        return CRMCommandResult(data={}, resource=version)

    result = run_idempotent_crm_command(business=business, actor=actor, action="medical.correction_access.document",
        idempotency_key=medical_request_digest({"key": idempotency_key}, business_id=business_id),
        payload={"request": request_id, "revision": expected_revision,
            "content_digest": medical_request_digest({"text": document_text, "reason": reason}, business_id=business_id)}, operation=operation)
    version = MedicalDocumentRevision.objects.get(document=item.document,
        pk=result.resource_id if result.replayed else result.resource.pk)
    return version, result.replayed
