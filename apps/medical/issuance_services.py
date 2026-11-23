import json
import secrets
from datetime import timedelta

from django.db import DatabaseError, transaction
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied, ValidationError

from apps.core.domain_errors import InvalidTransition
from apps.core.idempotency import CRMCommandResult, run_idempotent_crm_command
from .audit import MedicalAuditUnavailable
from .document_content import read_document_revision
from .document_finalization_services import finalization_evidence
from .identity_crypto import encrypt_medical_value, medical_request_digest
from .issuance_access import issuance_context, recipient_proof, grant_binding, grant_evidence
from .models import (MedicalDocumentGrant, MedicalDocumentGrantItem, MedicalDocumentGrantEvent,
    MedicalDocumentRevision, MedicalDocumentFinalization, MedicalEncounter, PatientRepresentative)
from .signing_services import _material


def grant_event(grant, action, *, actor=None, version=None, reason=""):
    try:
        with transaction.atomic():
            event = MedicalDocumentGrantEvent.objects.create(grant=grant, actor=actor, action=action, version=version,
                evidence_encrypted="staging")
            event.evidence_encrypted = encrypt_medical_value(json.dumps({"grant": grant.pk, "event": event.pk,
                "action": action, "actor": actor.pk if actor else None, "version": version.pk if version else None,
                "grant_revision": grant.revision, "reason": reason}, ensure_ascii=False, sort_keys=True),
                business_id=grant.patient.business_id, subject_id=event.pk, purpose="document_grant_event")
            event.save(update_fields=["evidence_encrypted"])
            return event
    except DatabaseError:
        raise MedicalAuditUnavailable() from None


def seal_grant(grant, proof):
    grant.evidence_encrypted = encrypt_medical_value(json.dumps(proof | grant_binding(grant), ensure_ascii=False, sort_keys=True),
        business_id=grant.patient.business_id, subject_id=grant.pk, purpose="document_grant")
    grant.save(update_fields=["evidence_encrypted"])


def scoped_grant(*, business, patient, branch, grant_id):
    grant = MedicalDocumentGrant.objects.select_for_update(of=("self",)).select_related(
        "patient", "encounter", "representative").filter(pk=grant_id, patient=patient,
        encounter__business=business, encounter__branch=branch).first()
    if grant is None:
        raise PermissionDenied()
    return grant


def _command(business, actor, action, key, payload, operation):
    if not isinstance(key, str) or not key.strip() or len(key) > 128:
        raise ValidationError({"idempotency_key": "Provide an idempotency key."})
    return run_idempotent_crm_command(business=business, actor=actor, action=action,
        idempotency_key=medical_request_digest({"key": key}, business_id=business.pk), payload=payload, operation=operation)


@transaction.atomic
def create_document_grant(*, actor, business_id, patient_id, branch_id, encounter_id, version_ids,
                          personally_verified, verification_reason, idempotency_key, representative_id=None, replaces_id=None):
    business, patient, branch, _ = issuance_context(actor, business_id, patient_id, branch_id)
    if personally_verified is not True or not isinstance(verification_reason, str) or not verification_reason.strip() or len(verification_reason) > 2000:
        raise ValidationError({"verification": "Confirm personal recipient verification and record its basis."})
    if (not isinstance(version_ids, list) or not 1 <= len(version_ids) <= 20
            or any(type(pk) is not int or pk <= 0 for pk in version_ids) or len(set(version_ids)) != len(version_ids)):
        raise ValidationError({"versions": "Select one to twenty distinct saved versions."})
    encounter = MedicalEncounter.objects.filter(pk=encounter_id, patient=patient, business=business, branch=branch).first()
    if encounter is None:
        raise PermissionDenied()
    representative = None
    if representative_id is not None:
        representative = PatientRepresentative.objects.filter(pk=representative_id, patient=patient).first()
        if representative is None:
            raise PermissionDenied()
    recipient = recipient_proof(patient, representative)
    versions = list(MedicalDocumentRevision.objects.select_related("document__encounter").filter(pk__in=version_ids,
        document__encounter=encounter, document__business=business))
    if len(versions) != len(version_ids):
        raise PermissionDenied()
    for version in versions:
        rules = read_document_revision(version).get("document_rules")
        if not rules or not rules["rule"]["issuable"]:
            raise InvalidTransition("The selected document is internal or has no issuance permission.")
    replaced = scoped_grant(business=business, patient=patient, branch=branch, grant_id=replaces_id) if replaces_id else None
    if replaced:
        grant_evidence(replaced, verify_recipient=False)
    returned_code = None

    def operation():
        nonlocal returned_code
        if replaced and replaced.state != "revoked":
            proof = grant_evidence(replaced, verify_recipient=False)
            replaced.state, replaced.revoked_at = "revoked", timezone.now()
            replaced.revision += 1
            replaced.save(update_fields=["state", "revoked_at", "revision"])
            seal_grant(replaced, proof)
            grant_event(replaced, "revoked", actor=actor, reason="Reissued after recipient verification")
        code = "".join(secrets.choice("23456789ABCDEFGHJKLMNPQRSTUVWXYZ") for _ in range(20))
        grant = MedicalDocumentGrant.objects.create(patient=patient, encounter=encounter, representative=representative,
            created_by=actor, replaces=replaced, code_hash=medical_request_digest({"document_code": code}, business_id=business_id),
            evidence_encrypted="staging")
        for version in versions:
            MedicalDocumentGrantItem.objects.create(grant=grant, version=version)
        seal_grant(grant, {"recipient": recipient, "personal_verification": verification_reason})
        grant_event(grant, "created", actor=actor, reason=verification_reason)
        returned_code = code
        return CRMCommandResult(data={}, resource=grant, status_code=201)

    result = _command(business, actor, "medical.issuance.create", idempotency_key,
        {"patient": patient_id, "branch": branch_id, "encounter": encounter_id, "versions": sorted(version_ids),
            "representative": representative_id, "replaces": replaces_id,
            "verification_digest": medical_request_digest({"reason": verification_reason}, business_id=business_id)}, operation)
    grant = scoped_grant(business=business, patient=patient, branch=branch,
        grant_id=result.resource_id if result.replayed else result.resource.pk)
    return grant, returned_code, result.replayed


def ready_finalization(version):
    rules = read_document_revision(version).get("document_rules")
    if not rules or not rules["rule"]["issuable"]:
        raise InvalidTransition("The selected document cannot be issued.")
    finalization = MedicalDocumentFinalization.objects.select_related("version__document", "artifact__attachment").filter(version=version).first()
    if finalization is None:
        raise InvalidTransition("Complete the exact saved document version before activation.")
    finalization_evidence(finalization)
    _material(finalization.artifact)
    return finalization


@transaction.atomic
def transition_document_grant(*, actor, business_id, patient_id, branch_id, grant_id,
                              expected_revision, action, reason, idempotency_key):
    business, patient, branch, _ = issuance_context(actor, business_id, patient_id, branch_id)
    grant = scoped_grant(business=business, patient=patient, branch=branch, grant_id=grant_id)
    if action not in {"activate", "revoke"} or type(expected_revision) is not int or expected_revision < 1:
        raise ValidationError({"action": "Select activation or revocation of the current grant."})
    if not isinstance(reason, str) or len(reason) > 2000 or action == "revoke" and not reason.strip():
        raise ValidationError({"reason": "Provide a revocation reason."})
    proof = grant_evidence(grant, verify_recipient=action == "activate")

    def operation():
        if grant.revision != expected_revision or grant.state == "revoked" or action == "activate" and grant.state != "pending":
            raise InvalidTransition("The document access changed; reload its state.")
        now = timezone.now()
        if action == "activate":
            for item in grant.items.select_related("version__document__encounter"):
                item.finalization = ready_finalization(item.version)
                item.save(update_fields=["finalization"])
            grant.state, grant.activated_at, grant.expires_at = "active", now, now + timedelta(hours=72)
        else:
            grant.state, grant.revoked_at = "revoked", now
        grant.revision += 1
        grant.save(update_fields=["state", "activated_at", "expires_at", "revoked_at", "revision"])
        seal_grant(grant, proof)
        grant_event(grant, "activated" if action == "activate" else "revoked", actor=actor, reason=reason)
        return CRMCommandResult(data={}, resource=grant)

    result = _command(business, actor, "medical.issuance.transition", idempotency_key,
        {"grant": grant.pk, "revision": expected_revision, "action": action,
            "reason_digest": medical_request_digest({"reason": reason}, business_id=business_id)}, operation)
    grant.refresh_from_db()
    return grant, result.replayed
