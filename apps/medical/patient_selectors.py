import json

from django.contrib.auth import get_user_model
from django.db import transaction
from rest_framework.exceptions import NotFound, PermissionDenied, ValidationError

from apps.branches.models import Branch
from apps.businesses.access import Actions, Resources, assert_can
from apps.businesses.models import Business
from apps.clients.models import Client
from .audit import write_patient_audit
from .identity_crypto import MedicalDataUnavailable, decrypt_medical_value
from .identity_policy import verification_form
from .models import MedicalAuditEvent, MedicalRoleAssignment, PatientProfile
from .role_access import assert_medical_branch_permission


def reception_context(*, actor, business_id, branch_id, action):
    if any(type(value) is not int or value <= 0 for value in (business_id, branch_id)):
        raise ValidationError({"scope": "Select a valid business and branch."})
    if not actor or not actor.is_authenticated:
        raise PermissionDenied()
    actor = get_user_model().objects.filter(pk=actor.pk, is_active=True).first()
    if actor is None:
        raise PermissionDenied()
    business = Business.objects.filter(pk=business_id).first()
    if business is None:
        raise NotFound()
    branch = Branch.objects.filter(pk=branch_id, business=business).first()
    role = assert_medical_branch_permission(actor, business, "medical_patients", action, branch=branch)
    if role.kind != MedicalRoleAssignment.Kinds.RECEPTION:
        raise PermissionDenied()
    return actor, business, branch


def patient_administration_access(*, actor, business_id, branch_id):
    actor, business, branch = reception_context(
        actor=actor, business_id=business_id, branch_id=branch_id, action="view")
    actions = {"view": True}
    for action in ("create", "update", "approve"):
        try:
            assert_medical_branch_permission(actor, business, "medical_patients", action, branch=branch)
        except PermissionDenied:
            actions[action] = False
        else:
            actions[action] = True
    return {"business_id": business.pk, "branch_id": branch.pk, "actions": actions}


def patient_verification_form(*, actor, business_id, branch_id):
    actor, business, branch = reception_context(
        actor=actor, business_id=business_id, branch_id=branch_id, action="approve")
    role = assert_medical_branch_permission(actor, business, "medical_patients", "approve", branch=branch)
    return verification_form(business_id=business.pk, member_id=role.member_id)


def patient_demographics(patient):
    try:
        values = json.loads(decrypt_medical_value(patient.demographics_encrypted, purpose="demographics",
            business_id=patient.business_id, subject_id=patient.client_id))
        if not isinstance(values, dict) or set(values) - {"date_of_birth", "sex", "address"}:
            raise ValueError
        return values
    except (ValueError, TypeError):
        raise MedicalDataUnavailable() from None


@transaction.atomic
def read_patient_administration(*, actor, business_id, branch_id, patient_id=None, client_id=None):
    if (patient_id is None) == (client_id is None):
        raise ValidationError({"patient": "Select one patient or client."})
    identifier = patient_id if patient_id is not None else client_id
    if type(identifier) is not int or identifier <= 0:
        raise ValidationError({"patient": "Select a valid patient or client."})
    actor, business, branch = reception_context(actor=actor, business_id=business_id, branch_id=branch_id, action="view")
    if patient_id is not None:
        client_id = PatientProfile.objects.filter(pk=patient_id, business=business).values_list("client_id", flat=True).first()
    client = Client.objects.select_for_update().filter(pk=client_id, business=business, is_archived=False).first()
    if client is None:
        raise NotFound()
    assert_can(actor, business, Resources.CLIENTS, Actions.VIEW, obj=client)
    patient = PatientProfile.objects.select_for_update().filter(client=client, business=business).first()
    if patient is None or (patient_id is not None and patient.pk != patient_id):
        raise NotFound()
    context = {"business_id": business.pk, "subject_id": client.pk}
    demographics = patient_demographics(patient)
    identifier = decrypt_medical_value(patient.iin_encrypted, purpose="iin", **context) if patient.iin_encrypted else None
    data = {"id": patient.pk, "business_id": business.pk, "client_id": client.pk,
        "full_name": client.full_name, "phone": client.phone, "email": client.email,
        "demographics": demographics, "iin": identifier, "identity_status": patient.identity_status,
        "revision": patient.revision, "client_updated_at": client.updated_at, "verified_at": patient.verified_at}
    write_patient_audit(actor=actor, business=business, patient=patient, action=MedicalAuditEvent.Actions.READ)
    return data
