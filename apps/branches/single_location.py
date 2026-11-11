"""Initial locations are ordinary branches; legacy conversion preserves existing work."""
from django.db import transaction

from apps.businesses.models import Business
from .models import Branch, BranchAccess


@transaction.atomic
def ensure_initial_location(business):
    business = Business.objects.select_for_update().get(pk=business.pk)
    existing = Branch.objects.filter(business=business).first()
    if existing is not None:
        return existing
    branch = Branch.objects.create(business=business, name=business.name,
        address=business.address, phone=business.phone, city=business.city)
    from .compatibility import adopt_first_branch
    adopt_first_branch(branch)
    for member in business.members.all():
        grant, created = BranchAccess.objects.get_or_create(member=member)
        if created:
            grant.branches.add(branch)
    from apps.core.audit import write_actor_audit_log
    from apps.core.models import AuditLog
    write_actor_audit_log(actor=business.owner, business=business, action=AuditLog.Actions.CREATE,
        instance=branch, metadata={"kind": "initial_location"})
    return branch


def materialize_initial_location(branch):
    if not branch.uses_business_defaults:
        return
    from .compatibility import adopt_first_branch
    adopt_first_branch(branch)
    from .catalog import automatic_days
    from .models import ScheduleDay
    from apps.scheduling.models import Resource
    Resource.objects.filter(business=branch.business, branch__isnull=True).exclude(resource_type="staff").update(branch=branch)
    for day in automatic_days(branch, list(Resource.objects.filter(business=branch.business, resource_type="staff"))):
        ScheduleDay.objects.update_or_create(branch=branch, resource_id=day["resource"],
            weekday=day["weekday"], date=day["date"], defaults={"business": branch.business, "intervals": day["intervals"]})
    for member in branch.business.members.all():
        grant, created = BranchAccess.objects.get_or_create(member=member)
        if created:
            grant.branches.add(branch)
    branch.uses_business_defaults = False
    branch.save(update_fields=["uses_business_defaults", "updated_at"])


def sync_initial_location(business):
    Branch.objects.filter(business=business, uses_business_defaults=True).update(
        name=business.name, address=business.address, phone=business.phone)
