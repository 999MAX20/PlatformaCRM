import json

from django.db import transaction
from rest_framework.exceptions import NotFound, PermissionDenied, ValidationError

from apps.branches.models import Branch
from apps.businesses.access import Actions, Resources, assert_can
from apps.businesses.models import Business
from apps.clients.models import Client
from .audit import write_patient_audit
from .identity_crypto import MedicalDataUnavailable, decrypt_medical_value
from .models import PatientIdentityCorrection, PatientProfile
from .role_access import assert_medical_branch_permission


def correction_proposal(correction):
    try:
        value = json.loads(decrypt_medical_value(correction.proposal_encrypted,
            business_id=correction.patient.business_id, subject_id=correction.patient_id,
            purpose="identity_correction_proposal"))
        if not isinstance(value, dict) or set(value) != {"iin", "reason", "evidence"}:
            raise ValueError
        if not isinstance(value["reason"], str) or not isinstance(value["evidence"], dict):
            raise ValueError
        if set(value["evidence"]) != {"protocol_reference", "approval_reference", "method", "fields"}:
            raise ValueError
        return value
    except (ValueError, TypeError):
        raise MedicalDataUnavailable() from None


@transaction.atomic
def list_identity_corrections(*, actor, business_id, branch_id, client_id, offset=0, limit=25):
    if any(type(value) is not int or value <= 0 for value in (business_id, branch_id, client_id)):
        raise ValidationError({"scope": "Select a valid business, branch and client."})
    if type(offset) is not int or offset < 0 or type(limit) is not int or not 1 <= limit <= 50:
        raise ValidationError({"page": "Select a valid page."})
    business = Business.objects.filter(pk=business_id).first()
    if business is None:
        raise NotFound()
    branch = Branch.objects.filter(pk=branch_id, business=business).first()
    role = assert_medical_branch_permission(actor, business, "medical_patients", "view", branch=branch)
    if role.kind not in {"head", "reception"}:
        raise PermissionDenied()
    client = Client.objects.filter(pk=client_id, business=business, is_archived=False).first()
    if client is None:
        raise NotFound()
    assert_can(actor, business, Resources.CLIENTS, Actions.VIEW, obj=client)
    patient = PatientProfile.objects.filter(client=client, business=business).first()
    if patient is None:
        raise NotFound()
    can_approve = False
    if role.kind == "head":
        try:
            assert_medical_branch_permission(actor, business, "medical_patients", "approve", branch=branch)
            can_approve = True
        except PermissionDenied:
            pass
    write_patient_audit(actor=actor, business=business, patient=patient, action="read")
    rows = list(PatientIdentityCorrection.objects.filter(patient=patient, branch=branch)
        .select_related("requested_by", "decided_by", "patient").order_by("-pk")[offset:offset + limit + 1])
    results = []
    for correction in rows[:limit]:
        write_patient_audit(actor=actor, business=business, patient=patient, action="read", identity_correction=correction)
        proposal = correction_proposal(correction)
        decision_reason = None
        if correction.decision_encrypted:
            try:
                decision_reason = json.loads(decrypt_medical_value(correction.decision_encrypted,
                    business_id=business.pk, subject_id=patient.pk, purpose="identity_correction_decision"))["reason"]
                if not isinstance(decision_reason, str):
                    raise ValueError
            except (ValueError, TypeError, KeyError):
                raise MedicalDataUnavailable() from None
        results.append({"id": correction.pk, "patient_id": patient.pk, "state": correction.state,
            "source_revision": correction.source_revision, "applied_revision": correction.applied_revision,
            "medical_review_required": correction.medical_review_required,
            "requested_by": correction.requested_by.full_name, "created_at": correction.created_at,
            "proposed_iin": proposal["iin"], "reason": proposal["reason"],
            "decided_by": correction.decided_by.full_name if correction.decided_by else None,
            "decided_at": correction.decided_at, "decision_reason": decision_reason})
    current_iin = decrypt_medical_value(patient.iin_encrypted, business_id=business.pk, subject_id=client.pk,
        purpose="iin") if patient.iin_encrypted else None
    return {"current_iin": current_iin, "results": results, "next_offset": offset + limit if len(rows) > limit else None,
            "actions": {"approve": can_approve}}
