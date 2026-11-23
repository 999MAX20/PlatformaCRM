from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied, ValidationError

from apps.branches.access import accessible_branches
from apps.businesses.models import Business, BusinessMember
from .assistant_access import assert_assistant_appointment_basis
from .assistant_context import assistant_management_context
from .assistant_lifecycle import appointment_basis_end_reason
from .audit import write_patient_audit
from .models import AppointmentAssistant
from .role_access import assert_medical_branch_permission, assert_medical_role_permission


def _pagination(before_id, limit):
    if (type(limit) is not int or not 1 <= limit <= 50 or
            (before_id is not None and (type(before_id) is not int or before_id <= 0))):
        raise ValidationError({"pagination": "Provide a valid cursor and a limit from 1 to 50."})


@transaction.atomic
def list_assistant_candidates(*, actor, business_id, patient_id, appointment_id, before_id=None, limit=20, query=""):
    _pagination(before_id, limit)
    if not isinstance(query, str) or len(query) > 100:
        raise ValidationError({"query": "Provide at most 100 characters."})
    actor, business, patient, appointment, primary = assistant_management_context(actor=actor,
        business_id=business_id, patient_id=patient_id, appointment_id=appointment_id)
    open_members = AppointmentAssistant.objects.filter(business=business, appointment=appointment,
        state__in=["pending", "active"]).values("assignment__member_id")
    members = BusinessMember.objects.select_related("user").filter(business=business, is_active=True,
        user__is_active=True, medical_role_assignment__kind="assistant",
        medical_role_assignment__revoked_at__isnull=True).exclude(user_id=actor.pk).exclude(pk=primary.pk).exclude(pk__in=open_members)
    if query.strip():
        members = members.filter(user__full_name__icontains=query.strip())
    if before_id is not None:
        members = members.filter(pk__lt=before_id)
    page = list(members.order_by("-pk")[:limit + 1])
    rows = []
    for member in page[:limit]:
        try:
            recipient = assert_medical_branch_permission(member.user, business, "medical_records", "view", branch=appointment.branch)
        except PermissionDenied:
            continue
        if recipient.kind == "assistant":
            rows.append({"member_id": member.pk, "name": member.user.full_name})
    write_patient_audit(actor=actor, business=business, patient=patient, action="read")
    return {"results": rows, "appointment_updated_at": appointment.updated_at,
            "next_before_id": page[limit - 1].pk if len(page) > limit else None}


@transaction.atomic
def list_appointment_assistants(*, actor, business_id, patient_id, appointment_id, before_id=None, limit=20):
    _pagination(before_id, limit)
    actor, business, patient, appointment, _ = assistant_management_context(actor=actor,
        business_id=business_id, patient_id=patient_id, appointment_id=appointment_id)
    items = AppointmentAssistant.objects.select_related("assignment__member__user", "invited_by").filter(
        business=business, appointment=appointment, patient=patient, assignment__member__business=business)
    if before_id is not None:
        items = items.filter(pk__lt=before_id)
    page = list(items.order_by("-pk")[:limit + 1])
    write_patient_audit(actor=actor, business=business, patient=patient, action="read")
    return {"results": [{"id": item.pk, "member_id": item.assignment.member_id,
        "name": item.assignment.member.user.full_name, "state": item.state, "revision": item.revision,
        "invited_at": item.invited_at, "accepted_at": item.accepted_at, "closed_at": item.closed_at,
        "inviter_name": item.invited_by.full_name} for item in page[:limit]],
        "appointment_updated_at": appointment.updated_at,
        "next_before_id": page[limit - 1].pk if len(page) > limit else None}


@transaction.atomic
def list_my_assistant_invitations(*, actor, business_id, before_id=None, limit=20):
    _pagination(before_id, limit)
    if type(business_id) is not int or business_id <= 0:
        raise ValidationError({"business": "Provide a valid business identifier."})
    business = Business.objects.select_for_update().filter(pk=business_id).first()
    if business is None:
        raise PermissionDenied()
    role = assert_medical_role_permission(actor, business, "medical_records", "view")
    if role.kind != "assistant":
        raise PermissionDenied()
    branches = accessible_branches(actor, business).filter(is_active=True, archived_at__isnull=True)
    if not role.all_branches:
        branches = branches.filter(medical_assignments__pk=role.assignment_id)
    items = AppointmentAssistant.objects.select_related("branch", "appointment__resource", "patient",
        "primary_clinician__user", "invited_by").filter(business=business, assignment_id=role.assignment_id,
        assignment__member__user_id=role.user_id, branch_id__in=branches.values("pk"),
        appointment__business=business, patient__business=business, patient__client__business=business,
        primary_clinician__business=business)
    if before_id is not None:
        items = items.filter(pk__lt=before_id)
    page = list(items.order_by("-pk")[:limit + 1])
    rows = []
    for item in page[:limit]:
        can_accept, can_open = False, False
        if item.state == "pending" and item.invited_at <= timezone.now() and appointment_basis_end_reason(item) is None:
            try:
                primary = assert_medical_branch_permission(item.primary_clinician.user, business,
                    "medical_records", "view", branch=item.branch)
                can_accept = primary.kind in ("doctor", "head")
            except PermissionDenied:
                pass
        if item.state == "active":
            try:
                assert_assistant_appointment_basis(actor=actor, business=business, patient_id=item.patient_id,
                    appointment_id=item.appointment_id, invitation_id=item.pk)
                can_open = True
            except PermissionDenied:
                pass
        rows.append({"id": item.pk, "state": item.state, "revision": item.revision,
            "branch_name": item.branch.name, "clinician_name": item.primary_clinician.user.full_name,
            "inviter_name": item.invited_by.full_name, "start_at": item.appointment.start_at,
            "invited_at": item.invited_at, "can_accept": can_accept, "can_open": can_open})
    return {"results": rows, "next_before_id": page[limit - 1].pk if len(page) > limit else None}
