import json

from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError
from rest_framework.exceptions import NotFound, PermissionDenied

from apps.branches.models import Branch
from apps.businesses.access import Actions, Resources, assert_can

from .audit import write_patient_audit
from .correction_access_context import assert_correction_access, expire_observed, locked_business, scoped_request
from .document_content import read_document_revision
from .encounter_content import read_encounter_revision
from .identity_crypto import MedicalDataUnavailable, decrypt_medical_value
from .models import MedicalCorrectionAccess, MedicalDocument, MedicalDocumentRevision, MedicalEncounter, MedicalEncounterRevision, PatientProfile
from .role_access import assert_medical_branch_permission


def correction_access_payload(item):
    return {"id": item.pk, "patient_id": item.patient_id, "encounter_id": item.encounter_id,
        "document_id": item.document_id, "requester_id": item.requester_id, "state": item.state,
        "revision": item.revision, "patient_revision": item.patient_revision, "target_revision": item.target_revision,
        "created_at": item.created_at, "reviewed_at": item.reviewed_at, "expires_at": item.expires_at,
        "closed_at": item.closed_at, "encounter_started_at": item.encounter.started_at,
        "requester_name": item.requester.user.full_name or item.requester.user.username,
        "reviewed_by_name": (item.reviewed_by.full_name or item.reviewed_by.username) if item.reviewed_by_id else None,
        "closed_by_name": (item.closed_by.full_name or item.closed_by.username) if item.closed_by_id else None}


def _reason(value, *, business, subject_id, purpose):
    if not value:
        return ""
    try:
        payload = json.loads(decrypt_medical_value(value, business_id=business.pk, subject_id=subject_id, purpose=purpose))
        if not isinstance(payload, dict) or set(payload) != {"reason"} or not isinstance(payload["reason"], str):
            raise ValueError
        return payload["reason"]
    except (TypeError, ValueError, KeyError):
        raise MedicalDataUnavailable() from None


@transaction.atomic
def read_correction_request(*, actor, business_id, request_id, head=False):
    business, _ = locked_business(actor, business_id, head=head)
    item = scoped_request(actor, business, request_id, head=head)
    expire_observed(item, actor=actor, business=business)
    write_patient_audit(actor=actor, business=business, patient=item.patient, action="read", correction_access=item)
    return {**correction_access_payload(item),
        "reason": _reason(item.reason_encrypted, business=business, subject_id=item.encounter_id, purpose="correction_access_request"),
        "decision_reason": _reason(item.decision_encrypted, business=business, subject_id=item.pk, purpose="correction_access_decision"),
        "closure_reason": _reason(item.closure_encrypted, business=business, subject_id=item.pk, purpose="correction_access_closure")}


@transaction.atomic
def read_correction_target(*, actor, business_id, request_id, version_id=None):
    if version_id is not None and (type(version_id) is not int or version_id <= 0):
        raise ValidationError({"version_id": "Provide a positive version identifier."})
    business, _ = locked_business(actor, business_id)
    item = scoped_request(actor, business, request_id)
    assert_correction_access(actor=actor, business=business, request_id=item.pk,
                             encounter_id=item.encounter_id, document_id=item.document_id)
    model = MedicalDocumentRevision if item.document_id is not None else MedicalEncounterRevision
    target = item.document if item.document_id is not None else item.encounter
    query = model.objects.filter(**({"document": target} if item.document_id is not None else {"encounter": target}))
    version = query.filter(**({"pk": version_id} if version_id is not None else {"revision": target.revision})).first()
    if version is None or version.revision > target.revision:
        raise MedicalDataUnavailable()
    audit_ref = {"document_version": version} if item.document_id is not None else {"encounter_version": version}
    write_patient_audit(actor=actor, business=business, patient=item.patient, action="read", correction_access=item, **audit_ref)
    content = read_document_revision(version) if item.document_id is not None else read_encounter_revision(version)
    from .document_corrections import document_version_state
    return {"access": correction_access_payload(item), "version_id": version.pk, "revision": version.revision,
            "state": document_version_state(version) if item.document_id is not None else target.state, "content": content}


@transaction.atomic
def list_correction_access(*, actor, business_id, branch_id, client_id, head=False, before_id=None, limit=25):
    from .correction_access_context import positive
    positive(branch_id=branch_id, client_id=client_id)
    if type(limit) is not int or not 1 <= limit <= 50:
        raise ValidationError({"limit": "Select a limit from 1 to 50."})
    if before_id is not None:
        positive(before_id=before_id)
    business, role = locked_business(actor, business_id, head=head)
    branch = Branch.objects.filter(pk=branch_id, business=business).first()
    assert_medical_branch_permission(actor, business, "medical_records", "manage" if head else "view", branch=branch)
    assert_medical_branch_permission(actor, business, "medical_records", "view", branch=branch)
    patient = PatientProfile.objects.select_related("client").filter(business=business, client_id=client_id,
        client__business=business).first()
    if patient is None:
        raise NotFound()
    assert_can(actor, business, Resources.CLIENTS, Actions.VIEW, obj=patient.client)
    query = MedicalCorrectionAccess.objects.filter(patient=patient, encounter__branch=branch,
        encounter__business=business, requester__business=business)
    if not head:
        query = query.filter(requester_id=role.member_id)
    if before_id is not None:
        query = query.filter(pk__lt=before_id)
    page = list(query.order_by("-pk")[:limit + 1])
    results = [read_correction_request(actor=actor, business_id=business_id, request_id=item.pk, head=head)
               for item in page[:limit]]
    write_patient_audit(actor=actor, business=business, patient=patient, action="read")
    can_review = False
    if role.kind == "head":
        try:
            assert_medical_branch_permission(actor, business, "medical_records", "manage", branch=branch)
            can_review = True
        except PermissionDenied:
            pass
    return {"results": results, "next_before_id": page[limit - 1].pk if len(page) > limit else None,
            "member_id": role.member_id, "can_review": can_review, "server_time": timezone.now()}


@transaction.atomic
def list_correction_targets(*, actor, business_id, branch_id, client_id, before_id=None, limit=25):
    from .correction_access_context import own_target, positive
    positive(branch_id=branch_id, client_id=client_id)
    if type(limit) is not int or not 1 <= limit <= 50:
        raise ValidationError({"limit": "Select a limit from 1 to 50."})
    if before_id is not None:
        positive(before_id=before_id)
    business, role = locked_business(actor, business_id)
    branch = Branch.objects.filter(pk=branch_id, business=business).first()
    assert_medical_branch_permission(actor, business, "medical_records", "view", branch=branch)
    query = MedicalEncounter.objects.filter(business=business, branch=branch, patient__business=business,
        patient__client_id=client_id, patient__client__business=business, primary_clinician_id=role.member_id)
    if before_id is not None:
        query = query.filter(pk__lt=before_id)
    page = list(query.order_by("-pk")[:limit + 1])
    rows = []
    for item in page[:limit]:
        encounter, _, _ = own_target(actor, business, item.pk, action="view")
        write_patient_audit(actor=actor, business=business, patient=encounter.patient, action="read")
        documents = []
        try:
            assert_medical_branch_permission(actor, business, "medical_documents", "view", branch=branch)
            assert_medical_branch_permission(actor, business, "medical_documents", "update", branch=branch)
        except PermissionDenied:
            pass
        else:
            documents = list(MedicalDocument.objects.filter(business=business, encounter=encounter).order_by("pk")
                .values("id", "revision", "created_at", "state"))
        rows.append({"encounter_id": encounter.pk, "patient_id": encounter.patient_id,
            "patient_revision": encounter.patient.revision, "revision": encounter.revision, "state": encounter.state,
            "started_at": encounter.started_at, "documents": documents})
    return {"results": rows, "next_before_id": page[limit - 1].pk if len(page) > limit else None}
