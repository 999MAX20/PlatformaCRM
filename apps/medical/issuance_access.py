import json

from django.conf import settings
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied, ValidationError

from apps.branches.models import Branch
from apps.businesses.models import Business
from apps.businesses.access import assert_can, Resources, Actions
from .clinical_identity import assert_verified_clinical_identity
from .identity_crypto import MedicalDataUnavailable, decrypt_medical_value
from .models import PatientProfile
from .representative_access import assert_representative_authority
from .role_access import assert_medical_branch_permission


def assert_local_issuance():
    if not getattr(settings, "MEDICAL_SYNTHETIC_ISSUANCE_ENABLED", False) or getattr(settings, "ENVIRONMENT", "") not in {"test", "local", "development"}:
        raise PermissionDenied("Synthetic document issuance is disabled.")


def issuance_context(actor, business_id, patient_id, branch_id):
    assert_local_issuance()
    if any(type(value) is not int or value <= 0 for value in (business_id, patient_id, branch_id)):
        raise ValidationError({"scope": "Provide positive scope identifiers."})
    business = Business.objects.select_for_update().filter(pk=business_id).first()
    if business is None:
        raise PermissionDenied()
    branch = Branch.objects.filter(pk=branch_id, business=business).first()
    role = assert_medical_branch_permission(actor, business, "medical_documents", "issue", branch=branch)
    patient = PatientProfile.objects.select_for_update().select_related("client").filter(pk=patient_id, business=business, client__business=business).first()
    if patient is None:
        raise PermissionDenied()
    assert_can(actor, business, Resources.CLIENTS, Actions.VIEW, obj=patient.client)
    return business, patient, branch, role


def recipient_proof(patient, representative):
    assert_verified_clinical_identity(patient)
    if representative is not None:
        assert_representative_authority(business_id=patient.business_id, patient_id=patient.pk,
            representative_client_id=representative.representative_client_id, representative_id=representative.pk,
            permission="receive_documents")
    return {"patient": patient.pk, "patient_revision": patient.revision,
        "verified_at": patient.verified_at.isoformat(),
        "representative": representative.pk if representative else None,
        "representative_revision": representative.revision if representative else None,
        "recipient_client": representative.representative_client_id if representative else patient.client_id}


def grant_binding(grant):
    return {"grant": str(grant.pk), "encounter": grant.encounter_id, "actor": grant.created_by_id,
        "code_hash": grant.code_hash, "versions": sorted(grant.items.values_list("version_id", flat=True)),
        "replaces": str(grant.replaces_id) if grant.replaces_id else None,
        "state": grant.state, "revision": grant.revision,
        "activated_at": grant.activated_at.isoformat() if grant.activated_at else None,
        "expires_at": grant.expires_at.isoformat() if grant.expires_at else None,
        "revoked_at": grant.revoked_at.isoformat() if grant.revoked_at else None}


def grant_evidence(grant, *, verify_recipient=True):
    try:
        proof = json.loads(decrypt_medical_value(grant.evidence_encrypted, business_id=grant.patient.business_id,
            subject_id=grant.pk, purpose="document_grant"))
        expected = grant_binding(grant)
        if verify_recipient:
            expected["recipient"] = recipient_proof(grant.patient, grant.representative)
        if any(proof.get(key) != value for key, value in expected.items()) or not proof.get("personal_verification"):
            raise ValueError
        if grant.encounter.patient_id != grant.patient_id or grant.encounter.business_id != grant.patient.business_id:
            raise ValueError
    except (ValueError, TypeError, AttributeError):
        raise MedicalDataUnavailable() from None
    return proof


def active_grant(grant):
    assert_local_issuance()
    if (grant.state != "active" or grant.activated_at is None or grant.expires_at is None
            or not grant.activated_at <= timezone.now() < grant.expires_at):
        raise PermissionDenied("The document access is unavailable.")
    from datetime import timedelta
    if grant.expires_at - grant.activated_at != timedelta(hours=72):
        raise MedicalDataUnavailable()
    grant_evidence(grant)
