from datetime import timedelta

from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import NotFound, PermissionDenied, ValidationError

from apps.businesses.access import Actions, Resources, assert_can
from apps.businesses.models import Business
from .audit import write_patient_audit
from .models import MedicalCorrectionAccess, MedicalDocument, MedicalEncounter
from .role_access import assert_medical_branch_permission, assert_medical_role_permission


def positive(**values):
    if any(type(value) is not int or value <= 0 for value in values.values()):
        raise ValidationError({"request": "Provide positive identifiers and revisions."})


def command_values(reason, idempotency_key):
    if not isinstance(reason, str) or not reason.strip() or len(reason) > 2000:
        raise ValidationError({"reason": "Provide a reason of at most 2000 characters."})
    if not isinstance(idempotency_key, str) or not idempotency_key.strip() or len(idempotency_key) > 128:
        raise ValidationError({"idempotency_key": "Provide a command key of at most 128 characters."})
    return reason.strip()


def locked_business(actor, business_id, *, head=False):
    positive(business_id=business_id)
    business = Business.objects.select_for_update().filter(pk=business_id).first()
    if business is None:
        raise NotFound()
    role = assert_medical_role_permission(actor, business, "medical_records", "manage" if head else "view")
    if role.kind not in ({"head"} if head else {"doctor", "head"}):
        raise PermissionDenied()
    return business, role


def own_target(actor, business, encounter_id, document_id=None, *, action="update"):
    positive(encounter_id=encounter_id)
    if document_id is not None:
        positive(document_id=document_id)
    resource = "medical_documents" if document_id is not None else "medical_records"
    role = assert_medical_role_permission(actor, business, resource, action)
    if role.kind not in {"doctor", "head"}:
        raise PermissionDenied()
    encounter = MedicalEncounter.objects.select_related("branch", "patient__client", "primary_clinician__user").filter(
        pk=encounter_id, business=business, primary_clinician_id=role.member_id).first()
    if encounter is None:
        raise PermissionDenied()
    encounter.clean()
    assert_medical_branch_permission(actor, business, resource, action, branch=encounter.branch)
    assert_medical_branch_permission(actor, business, resource, "view", branch=encounter.branch)
    assert_can(actor, business, Resources.CLIENTS, Actions.VIEW, obj=encounter.patient.client)
    document = None
    if document_id is not None:
        document = MedicalDocument.objects.filter(pk=document_id, encounter=encounter, business=business).first()
        if document is None:
            raise PermissionDenied()
        document.clean()
    return encounter, document, role


def scoped_request(actor, business, request_id, *, head=False):
    positive(request_id=request_id)
    query = MedicalCorrectionAccess.objects.select_for_update(of=("self",)).select_related(
        "patient__client", "encounter__branch", "requester__user", "document").filter(
        pk=request_id, patient__business=business, encounter__business=business, requester__business=business)
    if not head:
        query = query.filter(requester__user=actor)
    item = query.first()
    if item is None:
        raise PermissionDenied()
    item.clean()
    role = assert_medical_branch_permission(actor, business, "medical_records", "manage" if head else "view",
                                           branch=item.encounter.branch)
    if head:
        assert_medical_branch_permission(actor, business, "medical_records", "view", branch=item.encounter.branch)
    if role.kind not in ({"head"} if head else {"doctor", "head"}):
        raise PermissionDenied()
    assert_can(actor, business, Resources.CLIENTS, Actions.VIEW, obj=item.patient.client)
    if item.document_id is not None:
        assert_medical_branch_permission(actor, business, "medical_documents", "view", branch=item.encounter.branch)
    return item


def expire_observed(item, *, actor, business, now=None):
    now = now or timezone.now()
    if item.state != "active" or item.expires_at is None or now < item.expires_at:
        return False
    item.state = "expired"
    item.closed_at = item.expires_at
    item.revision += 1
    item.full_clean()
    item.save(update_fields=["state", "closed_at", "revision", "updated_at"])
    write_patient_audit(actor=actor, business=business, patient=item.patient,
                       action="correction_access_expired", correction_access=item)
    return True


@transaction.atomic
def observe_correction_access_expiry(*, actor, business_id, request_id, head=False):
    business, _ = locked_business(actor, business_id, head=head)
    item = scoped_request(actor, business, request_id, head=head)
    return expire_observed(item, actor=actor, business=business)


def assert_correction_access(*, actor, business, request_id, encounter_id, document_id=None, action="view"):
    item = scoped_request(actor, business, request_id)
    own_target(actor, business, encounter_id, document_id, action=action)
    now = timezone.now()
    if (item.encounter_id != encounter_id or item.document_id != document_id or item.state != "active"
            or item.reviewed_at is None or item.expires_at != item.reviewed_at + timedelta(hours=24)
            or not item.reviewed_at <= now < item.expires_at or item.reviewed_by_id == actor.pk):
        raise PermissionDenied()
    return item
