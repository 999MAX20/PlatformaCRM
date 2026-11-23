from django.db import transaction
from rest_framework.exceptions import PermissionDenied, ValidationError

from apps.core.domain_errors import InvalidTransition
from apps.core.idempotency import CRMCommandResult, run_idempotent_crm_command
from .appointment_access import assert_appointment_medical_basis
from .audit import write_patient_audit
from .clinical_identity import assert_verified_clinical_identity
from .document_artifact_access import document_artifact_access
from .document_content import read_document_revision
from .identity_crypto import decrypt_medical_value, encrypt_medical_value, medical_request_digest
from .models import MedicalDocumentReviewTransition
from .participation_access import assert_treatment_medical_basis
from .role_access import assert_medical_branch_permission


def _assert_review_writer(context, actor, appointment_id, participation_id):
    document = context.version.document
    encounter = document.encounter
    role = assert_medical_branch_permission(actor, context.business, "medical_documents", "update", branch=encounter.branch)
    if role.member_id != encounter.primary_clinician_id:
        raise PermissionDenied()
    if participation_id is None:
        basis = assert_appointment_medical_basis(actor=actor, business=context.business, patient_id=context.patient.pk,
            appointment_id=appointment_id, resource="medical_documents", action="update")
    else:
        basis = assert_treatment_medical_basis(actor=actor, business=context.business, patient_id=context.patient.pk,
            participation_id=participation_id, resource="medical_documents", action="update")
    if basis.branch_id != encounter.branch_id:
        raise PermissionDenied()
    assert_verified_clinical_identity(context.patient)


@transaction.atomic
def transition_document_review(*, actor, business_id, patient_id, version_id, expected_state_revision,
                               target, reason, idempotency_key, appointment_id=None, participation_id=None):
    if target not in {"draft", "ready_for_review", "reviewed"}:
        raise ValidationError({"target": "Select a review transition."})
    if type(expected_state_revision) is not int or expected_state_revision < 1:
        raise ValidationError({"expected_state_revision": "Provide the current state revision."})
    if not isinstance(reason, str) or len(reason) > 2000 or (target == "draft" and not reason.strip()):
        raise ValidationError({"reason": "Provide a reason for returning the document to draft."})
    if not isinstance(idempotency_key, str) or not idempotency_key.strip() or len(idempotency_key) > 128:
        raise ValidationError({"idempotency_key": "Provide an idempotency key of at most 128 characters."})
    context = document_artifact_access(actor=actor, business_id=business_id, patient_id=patient_id,
        version_id=version_id, appointment_id=appointment_id, participation_id=participation_id)
    _assert_review_writer(context, actor, appointment_id, participation_id)
    document = context.version.document
    encounter = document.encounter

    def operation():
        if (document.state_revision != expected_state_revision or document.revision != context.version.revision
                or document.state not in {"ready_for_review": {"draft"}, "reviewed": {"ready_for_review"},
                    "draft": {"ready_for_review", "reviewed"}}[target]
                or encounter.state != "draft" or encounter.record.state != "active"):
            raise InvalidTransition("The document or encounter changed; reload before continuing.")
        read_document_revision(context.version)
        document.state = target
        document.state_revision += 1
        document.save(update_fields=["state", "state_revision", "updated_at"])
        transition = MedicalDocumentReviewTransition.objects.create(version=context.version,
            state_revision=document.state_revision, state=target, actor=actor,
            reason_encrypted=encrypt_medical_value("", business_id=business_id,
                subject_id=document.pk, purpose="document_review_staging"))
        transition.reason_encrypted = encrypt_medical_value(reason, business_id=business_id,
            subject_id=transition.pk, purpose="document_review_reason")
        transition.save(update_fields=["reason_encrypted"])
        write_patient_audit(actor=actor, business=context.business, patient=context.patient,
            action={"ready_for_review": "document_review_submitted", "draft": "document_review_withdrawn",
                    "reviewed": "document_review_confirmed"}[target],
            document_version=context.version)
        return CRMCommandResult(data={}, status_code=200, resource=transition)

    result = run_idempotent_crm_command(business=context.business, actor=actor,
        action="medical.document.review", idempotency_key=medical_request_digest({"key": idempotency_key}, business_id=business_id),
        payload={"patient": patient_id, "version": version_id, "state_revision": expected_state_revision,
            "target": target, "appointment": appointment_id, "participation": participation_id,
            "reason_digest": medical_request_digest({"reason": reason}, business_id=business_id)}, operation=operation)
    transition = MedicalDocumentReviewTransition.objects.get(
        pk=result.resource_id if result.replayed else result.resource.pk, version__document__business=context.business)
    return transition, result.replayed


@transaction.atomic
def read_document_review(*, actor, business_id, patient_id, version_id, before_id=None, limit=20, **basis):
    if type(limit) is not int or not 1 <= limit <= 50 or (before_id is not None and (type(before_id) is not int or before_id <= 0)):
        raise ValidationError({"page": "Provide a valid history cursor and page size."})
    context = document_artifact_access(actor=actor, business_id=business_id, patient_id=patient_id, version_id=version_id, **basis)
    document = context.version.document
    can_transition = False
    if basis.get("appointment_id") is not None or basis.get("participation_id") is not None:
        try:
            _assert_review_writer(context, actor, basis.get("appointment_id"), basis.get("participation_id"))
            can_transition = (document.revision == context.version.revision and document.encounter.state == "draft"
                and document.encounter.record.state == "active")
        except (PermissionDenied, InvalidTransition):
            pass
    history = MedicalDocumentReviewTransition.objects.filter(version=context.version).select_related("actor")
    if before_id is not None:
        history = history.filter(pk__lt=before_id)
    page = list(history.order_by("-pk")[:limit + 1])
    events = [{"id": event.pk, "state": event.state, "state_revision": event.state_revision,
        "actor": {"id": event.actor_id, "name": event.actor.full_name}, "created_at": event.created_at,
        "reason": decrypt_medical_value(event.reason_encrypted, business_id=business_id,
            subject_id=event.pk, purpose="document_review_reason")} for event in page[:limit]]
    write_patient_audit(actor=actor, business=context.business, patient=context.patient, action="read",
        document_version=context.version, correction_access=context.correction)
    return {"document_state": document.state, "state_revision": document.state_revision,
        "can_transition": can_transition, "results": events,
        "next_before_id": page[limit - 1].pk if len(page) > limit else None}
