import json
from functools import wraps

from django.conf import settings
from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import NotFound, PermissionDenied, ValidationError

from apps.core.domain_errors import InvalidTransition
from apps.core.file_scanning import FileQuarantined, open_clean_attachment
from apps.core.idempotency import CRMCommandResult, run_idempotent_crm_command
from .audit import write_patient_audit
from .clinical_identity import assert_verified_clinical_identity
from .document_artifact_access import document_artifact_access
from .document_artifact_content import verify_document_artifact_bytes
from .document_content import read_document_revision
from .document_signing_prerequisites import assert_document_signing_prerequisites, document_signing_prerequisites
from .identity_crypto import encrypt_medical_value, decrypt_medical_value, medical_request_digest, MedicalDataUnavailable
from .models import MedicalDocumentArtifact, MedicalSigningSession, MedicalSigningEvent
from .role_access import assert_medical_branch_permission


def _signing_transaction(function):
    @wraps(function)
    def wrapped(*args, **kwargs):
        failure = None
        with transaction.atomic(durable=True):
            try:
                result = function(*args, **kwargs)
            except FileQuarantined as error:
                failure = error
        if failure is not None:
            raise failure
        return result
    return wrapped


def _synthetic_enabled():
    if not getattr(settings, "MEDICAL_SYNTHETIC_SIGNING_ENABLED", False) or settings.ENVIRONMENT not in {"development", "local", "test"}:
        raise PermissionDenied("Synthetic signing is disabled in this environment.")


def signing_session_data(session):
    return {"id": str(session.pk), "revision": session.revision, "state": session.state,
        "adapter": session.adapter, "artifact_id": session.artifact_id, "submission_id": session.submission_id,
        "created_at": session.created_at, "ended_at": session.ended_at,
        "events": [{"revision": event.revision, "action": event.action, "signer": event.signer,
            "position": event.position, "created_at": event.created_at,
            "actor": {"id": event.actor_id, "name": event.actor.full_name}}
            for event in session.events.select_related("actor").order_by("revision")]}


def assert_signing_evidence(session):
    events = list(session.events.order_by("revision"))
    if len(events) != session.revision or not events or events[0].action != "created":
        raise MedicalDataUnavailable()
    rules = read_document_revision(session.artifact.version).get("document_rules")
    if not rules:
        raise MedicalDataUnavailable()
    signers = rules["rule"]["signers"]
    signed = 0
    for revision, event in enumerate(events, start=1):
        try:
            proof = json.loads(decrypt_medical_value(event.proof_encrypted,
                business_id=session.artifact.version.document.business_id, subject_id=event.pk, purpose="signing_event"))
            expected = {"adapter": session.adapter, "session_id": str(session.pk), "sha256": session.artifact.sha256,
                "signer": event.signer, "position": event.position, "simulated": True,
                "action": event.action, "revision": event.revision, "actor_id": event.actor_id}
            if event.revision != revision or proof != expected:
                raise ValueError
            if event.action == "signed":
                signed += 1
                if signed > len(signers) or event.position != signed or event.signer != signers[signed - 1]:
                    raise ValueError
            elif event.action == "created" and revision != 1 or event.action == "cancelled" and revision != len(events):
                raise ValueError
        except (ValueError, TypeError):
            raise MedicalDataUnavailable() from None
    expected_state = "cancelled" if events[-1].action == "cancelled" else "completed" if signed == len(signers) else "pending"
    if session.state != expected_state:
        raise MedicalDataUnavailable()


@transaction.atomic
def read_document_signing(*, actor, business_id, patient_id, version_id, language, **basis):
    context = document_artifact_access(actor=actor, business_id=business_id, patient_id=patient_id,
        version_id=version_id, **basis)
    prerequisites = document_signing_prerequisites(context.version)
    enabled, role = False, None
    try:
        _synthetic_enabled()
        _, role = _context(actor, business_id, patient_id, version_id, basis)
        enabled = True
    except PermissionDenied:
        pass
    artifact = MedicalDocumentArtifact.objects.filter(version=context.version, rendition="signing", language=language).select_related("attachment").first()
    sessions = MedicalSigningSession.objects.filter(artifact__version=context.version).select_related("artifact").order_by("-created_at")
    current = sessions.filter(submission_id=prerequisites["submission_id"]).first() if prerequisites["submission_id"] else None
    primary = role is not None and role.member_id == context.version.document.encounter.primary_clinician_id
    next_signer = None
    if current is not None and current.state == "pending" and prerequisites["ready"]:
        position = current.events.filter(action="signed").count()
        if position < len(prerequisites["signers"]):
            next_signer = prerequisites["signers"][position]
    can_sign = enabled and next_signer is not None and (role.kind == "head" if next_signer == "medical_head" else primary)
    write_patient_audit(actor=actor, business=context.business, patient=context.patient, action="read", document_version=context.version)
    return {"version_id": version_id, "synthetic_enabled": enabled, "prerequisites": prerequisites,
        "artifact": {"id": artifact.pk, "scan_status": artifact.attachment.scan_status, "sha256": artifact.sha256} if artifact else None,
        "can_prepare": enabled and primary and prerequisites["ready"],
        "can_start": enabled and primary and prerequisites["ready"] and artifact is not None and artifact.attachment.scan_status == "clean" and (current is None or current.state == "cancelled"),
        "can_sign": can_sign, "can_cancel": enabled and primary and current is not None and current.state == "pending",
        "next_signer": next_signer, "current": signing_session_data(current) if current else None,
        "history": [signing_session_data(item) for item in sessions[:20]]}


def _context(actor, business_id, patient_id, version_id, basis):
    context = document_artifact_access(actor=actor, business_id=business_id, patient_id=patient_id,
        version_id=version_id, **basis)
    role = assert_medical_branch_permission(actor, context.business, "medical_documents", "sign",
        branch=context.version.document.encounter.branch)
    if context.correction is not None or context.version.document.encounter.record.state != "active":
        raise PermissionDenied()
    assert_verified_clinical_identity(context.patient)
    return context, role


def _material(artifact):
    if artifact.rendition != "signing" or artifact.format != "pdf":
        raise InvalidTransition("Prepare the exact PDF for signing first.")
    with open_clean_attachment(artifact.attachment, memory_only=True) as source:
        return verify_document_artifact_bytes(artifact, source.read())


@_signing_transaction
def read_signing_pdf(*, actor, business_id, patient_id, version_id, artifact_id, **basis):
    context, _ = _context(actor, business_id, patient_id, version_id, basis)
    artifact = MedicalDocumentArtifact.objects.select_related("attachment", "version__document").filter(
        pk=artifact_id, version=context.version, rendition="signing", format="pdf").first()
    if artifact is None:
        raise NotFound()
    content = _material(artifact)
    write_patient_audit(actor=actor, business=context.business, patient=context.patient,
        action="read", document_version=context.version)
    return content


def _event(context, session, actor, action, proof, *, signer="", position=None):
    proof = proof | {"session_id": str(session.pk), "signer": signer, "position": position,
        "simulated": True, "action": action, "revision": session.revision, "actor_id": actor.pk}
    event = MedicalSigningEvent.objects.create(session=session, revision=session.revision, actor=actor,
        action=action, signer=signer, position=position, proof_encrypted=encrypt_medical_value("{}",
            business_id=context.business.pk, subject_id=context.version.pk, purpose="signing_event_staging"))
    event.proof_encrypted = encrypt_medical_value(json.dumps(proof, sort_keys=True),
        business_id=context.business.pk, subject_id=event.pk, purpose="signing_event")
    event.save(update_fields=["proof_encrypted"])
    write_patient_audit(actor=actor, business=context.business, patient=context.patient,
        action="document_signing_changed", document_version=context.version)


def _command(context, actor, action, key, payload, operation):
    if not isinstance(key, str) or not key.strip() or len(key) > 128:
        raise ValidationError({"idempotency_key": "Provide an idempotency key of at most 128 characters."})
    result = run_idempotent_crm_command(business=context.business, actor=actor,
        action=action, idempotency_key=medical_request_digest({"key": key}, business_id=context.business.pk),
        payload=payload, operation=operation)
    return MedicalSigningSession.objects.get(pk=result.resource_id if result.replayed else result.resource.pk,
        artifact__version__document__business=context.business), result.replayed


@_signing_transaction
def start_synthetic_signing(*, actor, business_id, patient_id, version_id, artifact_id, idempotency_key, **basis):
    _synthetic_enabled()
    context, role = _context(actor, business_id, patient_id, version_id, basis)
    if role.member_id != context.version.document.encounter.primary_clinician_id:
        raise PermissionDenied()
    prerequisites = assert_document_signing_prerequisites(context.version)
    artifact = MedicalDocumentArtifact.objects.select_related("attachment", "version__document").filter(
        pk=artifact_id, version=context.version).first()
    if artifact is None:
        raise NotFound()
    _material(artifact)

    def operation():
        if MedicalSigningSession.objects.filter(submission_id=prerequisites["submission_id"],
                state__in=["pending", "completed"]).exists():
            raise InvalidTransition("This document review already has a signing session.")
        session = MedicalSigningSession.objects.create(artifact=artifact, submission_id=prerequisites["submission_id"],
            created_by=actor, adapter="synthetic", state="pending" if prerequisites["signers"] else "completed",
            ended_at=None if prerequisites["signers"] else timezone.now())
        _event(context, session, actor, "created", {"adapter": "synthetic", "sha256": artifact.sha256})
        return CRMCommandResult(data={}, status_code=201, resource=session)

    return _command(context, actor, "medical.signing.start", idempotency_key,
        {"patient": patient_id, "version": version_id, "artifact": artifact_id, "basis": basis}, operation)


@_signing_transaction
def advance_synthetic_signing(*, actor, business_id, patient_id, version_id, session_id,
                              expected_revision, action, idempotency_key, **basis):
    _synthetic_enabled()
    if action not in {"sign", "cancel"} or type(expected_revision) is not int or expected_revision < 1:
        raise ValidationError({"action": "Select an action and the current signing revision."})
    context, role = _context(actor, business_id, patient_id, version_id, basis)
    session = MedicalSigningSession.objects.select_for_update().select_related("artifact__attachment", "artifact__version__document").filter(
        pk=session_id, artifact__version=context.version, adapter="synthetic").first()
    if session is None:
        raise NotFound()
    assert_signing_evidence(session)
    primary = role.member_id == context.version.document.encounter.primary_clinician_id
    if action == "sign":
        _material(session.artifact)

    def operation():
        if session.state != "pending" or session.revision != expected_revision:
            raise InvalidTransition("The signing session changed; reload before continuing.")
        if action == "cancel":
            if not primary and actor.pk != session.created_by_id:
                raise PermissionDenied()
            session.state = "cancelled"; session.ended_at = timezone.now()
            signer, position = "", None
        else:
            prerequisites = assert_document_signing_prerequisites(context.version)
            if session.submission_id != prerequisites["submission_id"]:
                raise InvalidTransition("The document review cycle changed.")
            position = session.events.filter(action="signed").count() + 1
            if position > len(prerequisites["signers"]):
                raise InvalidTransition("No remaining signer.")
            signer = prerequisites["signers"][position - 1]
            if (signer == "medical_head" and role.kind != "head") or (signer != "medical_head" and not primary):
                raise PermissionDenied()
            if position == len(prerequisites["signers"]):
                session.state = "completed"; session.ended_at = timezone.now()
        session.revision += 1
        session.save(update_fields=["state", "ended_at", "revision"])
        _event(context, session, actor, "signed" if action == "sign" else "cancelled",
            {"adapter": "synthetic", "session_id": str(session.pk), "sha256": session.artifact.sha256,
             "signer": signer, "position": position, "simulated": True}, signer=signer, position=position)
        return CRMCommandResult(data={}, status_code=200, resource=session)

    return _command(context, actor, "medical.signing.advance", idempotency_key,
        {"patient": patient_id, "version": version_id, "session": str(session_id),
         "revision": expected_revision, "action": action, "basis": basis}, operation)
