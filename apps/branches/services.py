from django.db import transaction
from rest_framework.exceptions import ValidationError

from apps.businesses.access import Actions, Resources, assert_can
from apps.businesses.models import Business
from apps.core.audit import write_actor_audit_log
from apps.core.models import AuditLog
from .access import assert_network_grant, assert_branch_access, accessible_branches
from .models import Branch, BranchAccess


@transaction.atomic
def create_branch(*, business, actor, **values):
    Business.objects.select_for_update().get(pk=business.pk)
    assert_can(actor, business, Resources.SETTINGS, Actions.UPDATE)
    assert_network_grant(actor, business)
    first = not Branch.objects.filter(business=business).exists()
    branch = Branch.objects.create(business=business, **values)
    if first:
        from .compatibility import adopt_first_branch
        adopt_first_branch(branch)
        # Existing memberships keep the original location, not automatic access
        # to every future branch. Owner always retains the full Business scope.
        for member in business.members.all():
            grant, _ = BranchAccess.objects.get_or_create(member=member)
            grant.branches.add(branch)
    write_actor_audit_log(actor=actor, business=business, action=AuditLog.Actions.CREATE, instance=branch, metadata={"kind": "branch"})
    return branch


@transaction.atomic
def update_branch(*, branch, actor, changes):
    Business.objects.select_for_update().get(pk=branch.business_id)
    branch = Branch.objects.select_for_update().get(pk=branch.pk)
    assert_can(actor, branch.business, Resources.SETTINGS, Actions.UPDATE)
    assert_branch_access(actor, branch.business, branch)
    if branch.archived_at is not None:
        raise ValidationError({"branch": "Archived branches cannot be edited."})
    for key, value in changes.items():
        if key not in {"name", "address", "phone"}:
            raise ValidationError({key: "Use the explicit branch lifecycle action."})
        setattr(branch, key, value)
    branch.save()
    write_actor_audit_log(actor=actor, business=branch.business, action=AuditLog.Actions.UPDATE, instance=branch, metadata={"kind": "branch"})
    return branch


@transaction.atomic
def set_branch_access(*, member, actor, branch_ids, all_branches=False):
    business = member.business
    Business.objects.select_for_update().get(pk=business.pk)
    assert_can(actor, business, Resources.TEAM, Actions.MANAGE)
    if member.user_id == business.owner_id:
        raise ValidationError({"member": "The owner retains access to every branch."})
    branches = Branch.objects.filter(business=business, pk__in=set(branch_ids))
    if branches.count() != len(set(branch_ids)):
        raise ValidationError({"branch_ids": "Select branches of this business."})
    permitted = accessible_branches(actor, business)
    current = BranchAccess.objects.filter(member=member).first()
    affected = branches
    if current:
        affected = Branch.objects.filter(business=business) if current.all_branches else (branches | current.branches.all()).distinct()
    if all_branches:
        assert_network_grant(actor, business)
    if affected.exclude(pk__in=permitted).exists():
        raise ValidationError({"branch_ids": "Cannot change grants outside your own branch scope."})
    grant, _ = BranchAccess.objects.get_or_create(member=member)
    grant.all_branches = all_branches
    grant.save()
    grant.branches.set(branches if not all_branches else [])
    write_actor_audit_log(actor=actor, business=business, action=AuditLog.Actions.UPDATE, instance=member,
                         metadata={"kind": "branch_access", "all_branches": all_branches, "branch_ids": sorted(branch_ids)})
    return grant
