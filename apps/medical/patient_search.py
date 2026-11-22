from datetime import date

from django.db import DatabaseError, transaction
from django.db.models import Q
from rest_framework.exceptions import NotFound, PermissionDenied, ValidationError

from apps.branches.access import accessible_branches
from apps.businesses.access import Actions, Resources, assert_can
from apps.businesses.models import Business
from apps.clients.identity import normalize_email, normalize_phone
from apps.clients.models import Client
from apps.core.crm_read_scope import readable_queryset
from .audit import MedicalAuditUnavailable, write_patient_audit
from .identity_crypto import iin_digest
from .models import MedicalAuditEvent
from .patient_selectors import patient_demographics, reception_context
from .role_access import assert_medical_role_permission


def patient_search_access(*, actor, business_id):
    if type(business_id) is not int or business_id <= 0:
        raise ValidationError({"business_id": "Select a valid business."})
    business = Business.objects.filter(pk=business_id).first()
    if business is None:
        raise NotFound()
    context = assert_medical_role_permission(actor, business, "medical_patients", "view")
    if context.kind != "reception":
        raise PermissionDenied()
    assert_can(actor, business, Resources.CLIENTS, Actions.VIEW)
    branches = accessible_branches(actor, business, active_only=True)
    if not context.all_branches:
        branches = branches.filter(medical_assignments__pk=context.assignment_id)
    can_create = False
    try:
        assert_medical_role_permission(actor, business, "medical_patients", "create")
        assert_can(actor, business, Resources.CLIENTS, Actions.CREATE)
        can_create = True
    except PermissionDenied:
        pass
    return {"business_id": business.pk, "branches": list(branches.order_by("pk").values("id", "name")),
            "actions": {"create": can_create}}


def _scope_audit(actor, business, *, denied=False):
    try:
        event = MedicalAuditEvent.objects.create(business=business, actor=actor,
            action="access_denied" if denied else "read", result="denied" if denied else "success")
        if event is None or event.pk is None:
            raise MedicalAuditUnavailable()
    except DatabaseError:
        raise MedicalAuditUnavailable() from None


def record_denied_patient_search(*, actor, business_id):
    business = Business.objects.filter(pk=business_id).filter(
        Q(owner=actor) | Q(members__user=actor, members__is_active=True)).distinct().first()
    if business is not None:
        _scope_audit(actor, business, denied=True)


def _search_value(kind, value):
    if not isinstance(kind, str) or kind not in {"name", "phone", "email", "birth", "iin"}:
        raise ValidationError({"kind": "Select a supported search field."})
    if not isinstance(value, str) or not 2 <= len(value.strip()) <= 255:
        raise ValidationError({"query": "Enter between 2 and 255 characters."})
    value = value.strip()
    if kind == "birth":
        try:
            if date.fromisoformat(value).isoformat() != value:
                raise ValueError
        except ValueError:
            raise ValidationError({"query": "Enter a date in YYYY-MM-DD format."}) from None
    if kind == "phone":
        value = normalize_phone(value)
        if len(value) < 4:
            raise ValidationError({"query": "Enter at least four phone digits."})
    if kind == "email":
        value = normalize_email(value)
    return value


@transaction.atomic
def resolve_patients(*, actor, business_id, branch_id, kind, query, include_archived=False, offset=0, limit=25):
    actor, business, branch = reception_context(actor=actor, business_id=business_id, branch_id=branch_id, action="view")
    Business.objects.select_for_update().get(pk=business.pk)
    actor, business, branch = reception_context(actor=actor, business_id=business_id, branch_id=branch_id, action="view")
    if type(include_archived) is not bool or type(offset) is not int or offset < 0 or type(limit) is not int or not 1 <= limit <= 50:
        raise ValidationError({"page": "Select a valid archive filter and page."})
    value = _search_value(kind, query)
    clients = readable_queryset(Client.objects.all(), actor=actor, business=business, resource=Resources.CLIENTS)
    if not include_archived:
        clients = clients.filter(is_archived=False)
    if kind == "iin":
        clients = clients.filter(medical_profile__business=business,
                                 medical_profile__iin_digest=iin_digest(value, business_id=business.pk))
    elif kind == "name":
        clients = clients.filter(full_name__icontains=value)
    elif kind == "phone":
        clients = clients.filter(Q(normalized_phone__icontains=value) | Q(phone__icontains=value))
    elif kind == "email":
        clients = clients.filter(Q(normalized_email__icontains=value) | Q(email__icontains=value))
    else:
        clients = clients.filter(medical_profile__business=business)
    _scope_audit(actor, business)
    results, matched = [], 0
    for client in clients.select_related("medical_profile").order_by("pk").iterator(chunk_size=50):
        patient = getattr(client, "medical_profile", None)
        if patient is not None and patient.business_id != business.pk:
            continue
        demographics = {}
        if patient is not None:
            write_patient_audit(actor=actor, business=business, patient=patient, action="read")
            demographics = patient_demographics(patient)
        if kind == "birth" and demographics.get("date_of_birth") != value:
            continue
        matched += 1
        if matched <= offset:
            continue
        if len(results) == limit:
            return {"results": results, "next_offset": offset + limit}
        results.append({"client_id": client.pk, "patient_id": patient.pk if patient else None,
            "full_name": client.full_name, "phone": client.phone, "email": client.email,
            "date_of_birth": demographics.get("date_of_birth"), "is_archived": client.is_archived,
            "identity_status": patient.identity_status if patient else None,
            "match": "exact_confirmed" if kind == "iin" and patient.identity_status == "verified" else "possible"})
    return {"results": results, "next_offset": None}
