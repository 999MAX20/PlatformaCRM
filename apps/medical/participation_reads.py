from django.db import DatabaseError, transaction
from django.db.models import Q
from django.utils import timezone
from rest_framework.exceptions import NotFound, PermissionDenied, ValidationError

from apps.branches.access import accessible_branches
from apps.branches.models import Branch
from apps.businesses.access import Actions, Resources, assert_can
from apps.businesses.models import Business, BusinessMember
from apps.clients.models import Client
from .audit import MedicalAuditUnavailable, write_patient_audit
from .models import MedicalAuditEvent, MedicalRoleAssignment, PatientProfile, TreatmentParticipation
from .role_access import assert_medical_branch_permission, assert_medical_role_permission
from .participation_reasons import decline_reason_for_initiator


def _context(actor, business_id, before_id, limit):
    if type(business_id) is not int or business_id <= 0 or type(limit) is not int or not 1 <= limit <= 50 or (
            before_id is not None and (type(before_id) is not int or before_id <= 0)):
        raise ValidationError({"pagination": "Provide a valid business, cursor and limit from 1 to 50."})
    business = Business.objects.select_for_update().filter(pk=business_id).first()
    if business is None:
        raise NotFound()
    role = assert_medical_role_permission(actor, business, "medical_participation", "view")
    if role.kind not in (MedicalRoleAssignment.Kinds.DOCTOR, MedicalRoleAssignment.Kinds.HEAD):
        raise PermissionDenied()
    return business, role


def _rows(business):
    members = BusinessMember.objects.filter(business=business)
    return TreatmentParticipation.objects.select_related("patient__client", "member__user", "branch", "proposed_by").filter(
        patient__business=business, patient__client__business=business, member__business=business,
        branch__business=business).filter(
        Q(remaining_responsible__isnull=True) | Q(remaining_responsible__business=business)).filter(
        Q(proposed_by_id=business.owner_id) | Q(proposed_by_id__in=members.values("user_id")))


def _page(actor, business, rows, before_id, limit):
    if before_id is not None:
        rows = rows.filter(pk__lt=before_id)
    page = list(rows.order_by("-pk")[:limit + 1])
    try:
        event = MedicalAuditEvent.objects.create(business=business, actor=actor, action="read", result="success")
        if event is None or event.pk is None:
            raise MedicalAuditUnavailable()
    except DatabaseError:
        raise MedicalAuditUnavailable() from None
    result = []
    for item in page[:limit]:
        write_patient_audit(actor=actor, business=business, patient=item.patient, action="read", participation=item)
        result.append({"id": item.pk, "patient_id": item.patient_id, "patient_name": item.patient.client.full_name,
            "branch_id": item.branch_id, "branch_name": item.branch.name, "member_id": item.member_id,
            "member_name": item.member.user.full_name, "proposed_by_id": item.proposed_by_id,
            "proposer_name": item.proposed_by.full_name, "state": item.state, "revision": item.revision,
            "proposed_at": item.proposed_at, "accepted_at": item.accepted_at, "closed_at": item.closed_at,
            "remaining_responsible_id": item.remaining_responsible_id,
            "decline_reason": decline_reason_for_initiator(item, actor)})
    return {"results": result, "next_before_id": page[limit - 1].pk if len(page) > limit else None}


@transaction.atomic
def read_participation_workspace_access(*, actor, business_id):
    business, role = _context(actor, business_id, None, 20)
    branches = accessible_branches(actor, business)
    if not role.all_branches:
        branches = branches.filter(medical_assignments__pk=role.assignment_id)
    result = []
    for branch in branches.order_by("pk"):
        actions = {}
        for action in ("create", "approve", "manage"):
            try:
                assert_medical_branch_permission(actor, business, "medical_participation", action,
                    branch=branch, require_active=action != "manage")
                actions[action] = action != "manage" or role.kind == MedicalRoleAssignment.Kinds.HEAD
            except PermissionDenied:
                actions[action] = False
        result.append({"id": branch.pk, "name": branch.name, "actions": actions})
    return {"business_id": business.pk, "member_id": role.member_id, "kind": role.kind, "branches": result}


@transaction.atomic
def read_participation_patient_context(*, actor, business_id, client_id, branch_id):
    business, role = _context(actor, business_id, None, 20)
    if role.kind != MedicalRoleAssignment.Kinds.HEAD:
        raise PermissionDenied()
    if any(type(value) is not int or value <= 0 for value in (client_id, branch_id)):
        raise ValidationError({"scope": "Provide valid client and branch identifiers."})
    branch = Branch.objects.filter(pk=branch_id, business=business).first()
    assert_medical_branch_permission(actor, business, "medical_participation", "view", branch=branch)
    client = Client.objects.filter(pk=client_id, business=business, is_archived=False).first()
    if client is None:
        raise NotFound()
    assert_can(actor, business, Resources.CLIENTS, Actions.VIEW, obj=client)
    patient = PatientProfile.objects.filter(client=client, business=business).first()
    if patient is None:
        raise NotFound()
    write_patient_audit(actor=actor, business=business, patient=patient, action="read")
    return {"business_id": business.pk, "branch_id": branch.pk, "patient_id": patient.pk}


@transaction.atomic
def read_own_participations(*, actor, business_id, before_id=None, limit=20):
    business, role = _context(actor, business_id, before_id, limit)
    branches = accessible_branches(actor, business)
    if not role.all_branches:
        branches = branches.filter(medical_assignments__pk=role.assignment_id)
    rows = _rows(business).filter(member_id=role.member_id, proposed_at__lte=timezone.now(),
        branch_id__in=branches.values("pk"))
    return _page(actor, business, rows, before_id, limit)


@transaction.atomic
def read_participation_invitations(*, actor, business_id, before_id=None, limit=20):
    business, role = _context(actor, business_id, before_id, limit)
    branches = accessible_branches(actor, business, active_only=True)
    if not role.all_branches:
        branches = branches.filter(medical_assignments__pk=role.assignment_id)
    rows = _rows(business).filter(member_id=role.member_id, state="pending", proposed_at__lte=timezone.now(),
        branch_id__in=branches.values("pk"))
    return _page(actor, business, rows, before_id, limit)


@transaction.atomic
def read_managed_participations(*, actor, business_id, branch_id, patient_id=None, state=None, before_id=None, limit=20):
    business, role = _context(actor, business_id, before_id, limit)
    if role.kind != MedicalRoleAssignment.Kinds.HEAD:
        raise PermissionDenied()
    if type(branch_id) is not int or branch_id <= 0 or (
            patient_id is not None and (type(patient_id) is not int or patient_id <= 0)):
        raise ValidationError({"scope": "Provide valid branch and patient identifiers."})
    if state is not None and state not in TreatmentParticipation.States.values:
        raise ValidationError({"state": "Select a known participation state."})
    branch = Branch.objects.filter(pk=branch_id, business=business).first()
    assert_medical_branch_permission(actor, business, "medical_participation", "view", branch=branch, require_active=False)
    rows = _rows(business).filter(branch=branch)
    if patient_id is not None:
        rows = rows.filter(patient_id=patient_id)
    if state is not None:
        rows = rows.filter(state=state)
    return _page(actor, business, rows, before_id, limit)
