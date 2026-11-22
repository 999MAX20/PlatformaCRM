from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied, ValidationError

from apps.businesses.models import BusinessMember
from apps.core.domain_errors import InvalidTransition
from .audit import write_patient_audit
from .models import MedicalRoleAssignment, TreatmentParticipation
from .participation_services import participation_context, proposal_branch
from .role_access import assert_medical_branch_permission


@transaction.atomic
def read_responsible_candidates(*, actor, business_id, patient_id, participation_id,
                                after_member_id=None, limit=20, query=""):
    if type(participation_id) is not int or participation_id <= 0 or type(limit) is not int or not 1 <= limit <= 50 or (
            after_member_id is not None and (type(after_member_id) is not int or after_member_id <= 0)):
        raise ValidationError({"pagination": "Provide valid identifiers and a limit from 1 to 50."})
    if not isinstance(query, str) or len(query) > 100:
        raise ValidationError({"query": "Provide at most 100 characters."})
    actor, business, patient, role = participation_context(actor, business_id, patient_id, "manage")
    if role.kind != MedicalRoleAssignment.Kinds.HEAD:
        raise PermissionDenied()
    item = TreatmentParticipation.objects.select_related("branch").filter(pk=participation_id, patient=patient,
        member__business=business, branch__business=business).first()
    if item is None:
        raise PermissionDenied()
    assert_medical_branch_permission(actor, business, "medical_participation", "manage",
                                     branch=item.branch, require_active=False)
    if item.state != "active" or item.accepted_at is None or item.accepted_at > timezone.now():
        raise InvalidTransition("Participation is not active; review its current state.")
    members = BusinessMember.objects.select_related("user").filter(business=business,
        is_active=True, user__is_active=True)
    if query.strip():
        members = members.filter(user__full_name__icontains=query.strip())
    if after_member_id is not None:
        members = members.filter(pk__gt=after_member_id)
    page = list(members.order_by("pk")[:limit + 1])
    rows = [{"member_id": member.pk, "name": member.user.full_name}
            for member in page[:limit] if not member.user.is_platform_user]
    write_patient_audit(actor=actor, business=business, patient=patient, action="read", participation=item)
    return {"results": rows, "participation_revision": item.revision,
            "next_after_member_id": page[limit - 1].pk if len(page) > limit else None}


@transaction.atomic
def read_proposal_candidates(*, actor, business_id, patient_id, branch_id,
                            source_appointment_id=None, source_participation_id=None,
                            after_member_id=None, limit=20, query=""):
    if type(limit) is not int or not 1 <= limit <= 50 or (
            after_member_id is not None and (type(after_member_id) is not int or after_member_id <= 0)):
        raise ValidationError({"pagination": "Provide a valid cursor and limit from 1 to 50."})
    if not isinstance(query, str) or len(query) > 100:
        raise ValidationError({"query": "Provide at most 100 characters."})
    actor, business, patient, role = participation_context(actor, business_id, patient_id, "create")
    branch = proposal_branch(actor=actor, business=business, patient_id=patient_id, role=role, branch_id=branch_id,
        source_appointment_id=source_appointment_id, source_participation_id=source_participation_id)
    open_members = TreatmentParticipation.objects.filter(patient=patient, branch=branch,
        state__in=["pending", "active"]).values("member_id")
    members = BusinessMember.objects.select_related("user").filter(business=business, is_active=True,
        user__is_active=True, medical_role_assignment__kind__in=["doctor", "head"]).exclude(
        user_id=actor.pk).exclude(pk__in=open_members)
    if query.strip():
        members = members.filter(user__full_name__icontains=query.strip())
    if after_member_id is not None:
        members = members.filter(pk__gt=after_member_id)
    page = list(members.order_by("pk")[:limit + 1])
    rows = []
    for member in page[:limit]:
        try:
            recipient = assert_medical_branch_permission(member.user, business, "medical_participation", "approve", branch=branch)
        except PermissionDenied:
            continue
        if recipient.kind in (MedicalRoleAssignment.Kinds.DOCTOR, MedicalRoleAssignment.Kinds.HEAD):
            rows.append({"member_id": member.pk, "name": member.user.full_name})
    write_patient_audit(actor=actor, business=business, patient=patient, action="read")
    return {"results": rows, "patient_revision": patient.revision,
        "next_after_member_id": page[limit - 1].pk if len(page) > limit else None}
