import json

from rest_framework.exceptions import NotFound, PermissionDenied, ValidationError

from apps.core.domain_errors import InvalidTransition
from apps.core.idempotency import CRMCommandResult, run_idempotent_crm_command
from .audit import write_patient_audit
from .document_signing_prerequisites import assert_document_signing_prerequisites
from .identity_crypto import encrypt_medical_value, decrypt_medical_value, medical_request_digest, MedicalDataUnavailable
from .document_content import read_document_revision
from .document_artifact_content import read_document_artifact_manifest
from .models import MedicalDocumentArtifact, MedicalDocumentFinalization, MedicalSigningSession
from .role_access import assert_medical_branch_permission
from .signing_services import _context, _material, _signing_transaction, _synthetic_enabled, assert_signing_evidence


def finalization_evidence(item):
    snapshot = read_document_revision(item.version)
    rules = snapshot.get("document_rules")
    read_document_artifact_manifest(item.artifact)
    expected = {"version_id": item.version_id, "submission_id": item.submission_id,
        "artifact_id": item.artifact_id, "sha256": item.artifact.sha256,
        "session_id": str(item.signing_session_id) if item.signing_session_id else None,
        "rule_version_id": rules["version_id"] if rules else None, "actor_id": item.actor_id, "synthetic": True}
    try:
        value = json.loads(decrypt_medical_value(item.evidence_encrypted,
            business_id=item.version.document.business_id, subject_id=item.pk, purpose="document_finalization"))
        if (value != expected or not rules or item.artifact.version_id != item.version_id
                or item.submission.version_id != item.version_id or item.submission.state != "ready_for_review"):
            raise ValueError
        if rules["rule"]["signers"]:
            session = item.signing_session
            if session is None or session.artifact_id != item.artifact_id or session.submission_id != item.submission_id or session.state != "completed":
                raise ValueError
            assert_signing_evidence(session)
    except (ValueError, TypeError):
        raise MedicalDataUnavailable() from None
    return value


def finalization_data(item):
    finalization_evidence(item)
    return {"id": item.pk, "version_id": item.version_id, "artifact_id": item.artifact_id,
        "created_at": item.created_at, "synthetic": True, "actor": {"id": item.actor_id, "name": item.actor.full_name}}


@_signing_transaction
def finalize_document(*, actor, business_id, patient_id, version_id, artifact_id, expected_state_revision,
                      idempotency_key, **basis):
    # All currently configurable document matrices are explicitly synthetic.
    _synthetic_enabled()
    if type(expected_state_revision) is not int or expected_state_revision < 1:
        raise ValidationError({"expected_state_revision": "Provide the current document state revision."})
    if not isinstance(idempotency_key, str) or not idempotency_key.strip() or len(idempotency_key) > 128:
        raise ValidationError({"idempotency_key": "Provide an idempotency key of at most 128 characters."})
    context, role = _context(actor, business_id, patient_id, version_id, basis)
    document = context.version.document
    if role.member_id != document.encounter.primary_clinician_id:
        raise PermissionDenied()
    assert_medical_branch_permission(actor, context.business, "medical_documents", "update", branch=document.encounter.branch)
    artifact = MedicalDocumentArtifact.objects.select_related("attachment", "version__document").filter(
        pk=artifact_id, version=context.version, rendition="signing").first()
    if artifact is None:
        raise NotFound()
    _material(artifact)

    def operation():
        if document.state_revision != expected_state_revision or document.state != "reviewed":
            raise InvalidTransition("The document changed; reload its current state.")
        prerequisites = assert_document_signing_prerequisites(context.version)
        session = None
        if prerequisites["signers"]:
            session = MedicalSigningSession.objects.select_related("artifact__version__document").filter(
                submission_id=prerequisites["submission_id"], artifact=artifact, state="completed").first()
            if session is None:
                raise InvalidTransition("Complete every required signature of this exact PDF first.")
            assert_signing_evidence(session)
        finalization = MedicalDocumentFinalization.objects.create(version=context.version,
            submission_id=prerequisites["submission_id"], artifact=artifact, signing_session=session, actor=actor,
            evidence_encrypted=encrypt_medical_value("{}", business_id=business_id, subject_id=version_id, purpose="finalization_staging"))
        evidence = {"version_id": version_id, "submission_id": finalization.submission_id,
            "artifact_id": artifact.pk, "sha256": artifact.sha256, "session_id": str(session.pk) if session else None,
            "rule_version_id": prerequisites["rule_version_id"], "actor_id": actor.pk, "synthetic": True}
        finalization.evidence_encrypted = encrypt_medical_value(json.dumps(evidence, sort_keys=True),
            business_id=business_id, subject_id=finalization.pk, purpose="document_finalization")
        finalization.save(update_fields=["evidence_encrypted"])
        document.state = "finalized"
        document.state_revision += 1
        document.save(update_fields=["state", "state_revision", "updated_at"])
        write_patient_audit(actor=actor, business=context.business, patient=context.patient,
            action="document_finalized", document_version=context.version)
        return CRMCommandResult(data={}, status_code=200, resource=finalization)

    result = run_idempotent_crm_command(business=context.business, actor=actor, action="medical.document.finalize",
        idempotency_key=medical_request_digest({"key": idempotency_key}, business_id=business_id),
        payload={"patient": patient_id, "version": version_id, "artifact": artifact_id,
            "state_revision": expected_state_revision, "basis": basis}, operation=operation)
    return MedicalDocumentFinalization.objects.get(pk=result.resource_id if result.replayed else result.resource.pk,
        version__document__business=context.business), result.replayed
