from django.db import transaction
from rest_framework.exceptions import PermissionDenied, ValidationError

from apps.core.domain_errors import InvalidTransition
from apps.core.idempotency import CRMCommandResult, run_idempotent_crm_command
from .audit import write_patient_audit
from .clinical_identity import assert_verified_clinical_identity
from .document_artifact_access import document_artifact_access
from .document_content import read_document_revision
from .identity_crypto import medical_request_digest
from .models import MedicalDocumentHeadConfirmation
from .role_access import assert_medical_branch_permission


def document_review_submission(version):
    document = version.document
    if version.revision != document.revision or document.state not in {"ready_for_review", "reviewed"}:
        return None
    latest = version.review_transitions.order_by("-state_revision").first()
    if latest is None or latest.state_revision != document.state_revision or latest.state != document.state:
        return None
    return version.review_transitions.filter(state="ready_for_review").order_by("-state_revision").first()


def current_review_submission(version):
    document = version.document
    from .document_corrections import reviewable_encounter
    if not reviewable_encounter(version):
        return None
    return document_review_submission(version)


@transaction.atomic
def read_document_head_review(*, actor, business_id, patient_id, version_id, **basis):
    context = document_artifact_access(actor=actor, business_id=business_id, patient_id=patient_id,
        version_id=version_id, **basis)
    rules = read_document_revision(context.version).get("document_rules")
    required = rules is not None and "medical_head" in rules["rule"]["reviewers"]
    submission = current_review_submission(context.version)
    from .models import MedicalDocumentFinalization
    finalization = MedicalDocumentFinalization.objects.filter(version=context.version).select_related("submission").first()
    if finalization:
        submission = finalization.submission
    confirmation = (MedicalDocumentHeadConfirmation.objects.select_related("actor").filter(
        submission=submission).first() if submission else None)
    can_confirm = False
    if required and submission and confirmation is None and not finalization and basis.get("head_branch_id") is not None:
        try:
            assert_medical_branch_permission(actor, context.business, "medical_documents", "approve",
                branch=context.version.document.encounter.branch)
            assert_verified_clinical_identity(context.patient)
            can_confirm = True
        except (PermissionDenied, InvalidTransition):
            pass
    write_patient_audit(actor=actor, business=context.business, patient=context.patient,
        action="read", document_version=context.version, correction_access=context.correction)
    return {"required": required, "can_confirm": can_confirm,
        "state_revision": context.version.document.state_revision,
        "confirmation": {"id": confirmation.pk, "actor": {"id": confirmation.actor_id,
            "name": confirmation.actor.full_name}, "created_at": confirmation.created_at} if confirmation else None}


@transaction.atomic
def confirm_document_by_head(*, actor, business_id, patient_id, version_id, head_branch_id,
                             expected_state_revision, idempotency_key):
    if type(expected_state_revision) is not int or expected_state_revision < 1:
        raise ValidationError({"expected_state_revision": "Provide the current state revision."})
    if not isinstance(idempotency_key, str) or not idempotency_key.strip() or len(idempotency_key) > 128:
        raise ValidationError({"idempotency_key": "Provide an idempotency key of at most 128 characters."})
    context = document_artifact_access(actor=actor, business_id=business_id, patient_id=patient_id,
        version_id=version_id, head_branch_id=head_branch_id)
    document = context.version.document
    role = assert_medical_branch_permission(actor, context.business, "medical_documents", "approve",
        branch=document.encounter.branch)
    if role.kind != "head":
        raise PermissionDenied()
    assert_verified_clinical_identity(context.patient)
    rules = read_document_revision(context.version).get("document_rules")
    if rules is None or "medical_head" not in rules["rule"]["reviewers"]:
        raise InvalidTransition("The saved document rules do not require head review.")

    def operation():
        submission = current_review_submission(context.version)
        if document.state_revision != expected_state_revision or submission is None:
            raise InvalidTransition("The document review changed; reload before continuing.")
        if MedicalDocumentHeadConfirmation.objects.filter(submission=submission).exists():
            raise InvalidTransition("This document review already has head confirmation.")
        confirmation = MedicalDocumentHeadConfirmation.objects.create(submission=submission, actor=actor)
        write_patient_audit(actor=actor, business=context.business, patient=context.patient,
            action="document_head_confirmed", document_version=context.version)
        return CRMCommandResult(data={}, status_code=200, resource=confirmation)

    result = run_idempotent_crm_command(business=context.business, actor=actor,
        action="medical.document.head_confirm", idempotency_key=medical_request_digest({"key": idempotency_key}, business_id=business_id),
        payload={"patient": patient_id, "version": version_id, "branch": head_branch_id,
            "state_revision": expected_state_revision}, operation=operation)
    confirmation = MedicalDocumentHeadConfirmation.objects.get(
        pk=result.resource_id if result.replayed else result.resource.pk,
        submission__version__document__business=context.business)
    return confirmation, result.replayed
