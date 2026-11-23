from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import NotFound, ValidationError

from apps.businesses.access import Actions, Resources, assert_can
from apps.businesses.models import Business
from .audit import write_patient_audit
from .models import MedicalAuditEvent, PatientProfile, PatientRepresentative
from .patient_selectors import reception_context
from .representative_policy import representative_form
from .representative_access import read_representative_authority
from .role_access import assert_medical_branch_permission


def representation_verification_form(*, actor, business_id, branch_id):
    actor, business, branch = reception_context(actor=actor, business_id=business_id, branch_id=branch_id, action="approve")
    role = assert_medical_branch_permission(actor, business, "medical_patients", "approve", branch=branch)
    return representative_form(business_id=business.pk, member_id=role.member_id)


@transaction.atomic
def list_patient_representatives(*, actor, business_id, branch_id, patient_id, offset=0, limit=25):
    if (any(type(value) is not int or value <= 0 for value in (business_id, branch_id, patient_id)) or type(offset) is not int or offset < 0 or
            type(limit) is not int or not 1 <= limit <= 50):
        raise ValidationError({"page": "Select a valid patient and page."})
    if not Business.objects.select_for_update().filter(pk=business_id).first():
        raise NotFound()
    actor, business, _ = reception_context(actor=actor, business_id=business_id, branch_id=branch_id, action="view")
    patient = PatientProfile.objects.select_related("client").filter(pk=patient_id, business=business,
        client__business=business).first()
    if patient is None:
        raise NotFound()
    assert_can(actor, business, Resources.CLIENTS, Actions.VIEW, obj=patient.client)
    return _representative_page(actor=actor, business=business, patient=patient, offset=offset, limit=limit)


@transaction.atomic
def list_clinical_representatives(*, actor, business_id, patient_id, appointment_id=None,
                                  participation_id=None, offset=0, limit=25):
    from .encounter_reads import _clinical_read_context
    if type(offset) is not int or offset < 0 or type(limit) is not int or not 1 <= limit <= 50:
        raise ValidationError({"page": "Select a valid page."})
    business, patient = _clinical_read_context(actor=actor, business_id=business_id, patient_id=patient_id,
        appointment_id=appointment_id, participation_id=participation_id)
    assert_can(actor, business, Resources.CLIENTS, Actions.VIEW, obj=patient.client)
    return _representative_page(actor=actor, business=business, patient=patient, offset=offset, limit=limit)


def _representative_page(*, actor, business, patient, offset, limit):
    query = PatientRepresentative.objects.filter(patient=patient,
        representative_client__business=business).select_related("representative_client").order_by("-pk")
    rows = list(query[offset:offset + limit + 1])
    data = []
    now = timezone.now()
    for relation in rows[:limit]:
        client = relation.representative_client
        assert_can(actor, business, Resources.CLIENTS, Actions.VIEW, obj=client)
        authority = read_representative_authority(relation, business_id=business.pk)
        state = "revoked" if relation.revoked_at else "scheduled" if max(relation.valid_from, relation.verified_at) > now else (
            "expired" if relation.valid_until is not None and relation.valid_until <= now else "active")
        data.append({"id": relation.pk, "representative_client_id": client.pk, "full_name": client.full_name,
            "revision": relation.revision, "permissions": authority["permissions"], "status": state,
            "permission_labels": authority.get("permission_labels"),
            "valid_from": relation.valid_from, "valid_until": relation.valid_until,
            "verified_at": relation.verified_at, "revoked_at": relation.revoked_at})
        write_patient_audit(actor=actor, business=business, patient=patient,
            action=MedicalAuditEvent.Actions.READ, representative=relation)
    if not data:
        write_patient_audit(actor=actor, business=business, patient=patient, action=MedicalAuditEvent.Actions.READ)
    return {"results": data, "next_offset": offset + limit if len(rows) > limit else None}
