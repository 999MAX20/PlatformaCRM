"""Token-free employee diagnostics; every dependency stays in the selected Business."""
from django.db.models import Count, Q
from django.utils import timezone

from apps.businesses.employee_access import CONSENT_ACTIONS, revision
from apps.businesses.models import BusinessMember, BusinessInvitation, BusinessRole, EmployeeAccessRepair
from apps.scheduling.models import Resource, Appointment
from apps.tasks.models import Task
from apps.leads.models import Lead
from apps.crm.models import Deal
from apps.bots.models import BotConversation


def repair_rows():
    return EmployeeAccessRepair.objects.select_related("business", "prepared_by", "executed_by")


def projection(item):
    status = "expired" if item.status == "pending" and item.expires_at <= timezone.now() else item.status
    return {"id": str(item.pk), "business_id": item.business_id, "business_name": item.business.name,
        "target_id": item.target_id, "target_name": item.target_name,
        "target_email": item.target_email,
        "action": item.action, "status": status, "reason": item.reason,
        "target_role": {"id": item.target_role_id, "name": item.target_role_name} if item.target_role_id else None,
        "target_role_key": item.target_role_key,
        "prepared_by": item.prepared_by.full_name or item.prepared_by.email,
        "executed_by": (item.executed_by.full_name or item.executed_by.email) if item.executed_by_id else None,
        "owner_required": item.action in CONSENT_ACTIONS, "owner_confirmed_at": item.owner_confirmed_at,
        "expires_at": item.expires_at, "completed_at": item.completed_at,
        "support_case_id": item.support_case_id}


def counts(model, business, field, ids):
    return dict(model.objects.filter(business=business, **{f"{field}__in": ids}).values(field).annotate(total=Count("pk")).values_list(field, "total"))


def diagnostics(business, *, search="", page=1, page_size=20):
    members = BusinessMember.objects.filter(business=business).select_related("user", "business_role").order_by("pk")
    invitations = BusinessInvitation.objects.filter(business=business).select_related("business_role").order_by("-pk")
    if search:
        members = members.filter(Q(user__email__icontains=search) | Q(user__full_name__icontains=search))
        invitations = invitations.filter(Q(email__icontains=search) | Q(full_name__icontains=search))
    total_members, total_invitations = members.count(), invitations.count()
    start = (page - 1) * page_size
    rows = list(members[start:start + page_size])
    user_ids = [row.user_id for row in rows]
    resources = list(Resource.objects.filter(business=business, linked_user_id__in=user_ids).values("id", "linked_user_id", "name", "is_active", "retired_at"))
    appointment_counts = counts(Appointment, business, "resource_id", [row["id"] for row in resources])
    dependency_counts = {name: counts(model, business, field, user_ids) for name, model, field in [
        ("tasks", Task, "assignee_id"), ("leads", Lead, "responsible_user_id"),
        ("deals", Deal, "owner_id"), ("conversations", BotConversation, "assigned_to_id")]}
    people = []
    for member in rows:
        protected = member.user_id == business.owner_id or member.role == "owner" or member.user.is_platform_user
        role = member.business_role
        people.append({"id": member.pk, "user_id": member.user_id, "name": member.user.full_name or member.user.email,
            "email": member.user.email, "account_active": member.user.is_active, "membership_active": member.is_active,
            "role": member.role, "business_role": {"id": role.pk, "name": role.name, "active": role.is_active} if role and role.business_id == business.pk else None,
            "protected": protected, "revision": revision(business, member),
            "specialists": [{**resource, "appointments": appointment_counts.get(resource["id"], 0)} for resource in resources if resource["linked_user_id"] == member.user_id],
            "dependencies": {key: values.get(member.user_id, 0) for key, values in dependency_counts.items()}})
    return {"members": people, "members_count": total_members, "invitations_count": total_invitations,
        "page": page, "page_size": page_size,
        "invitations": [{"id": row.pk, "name": row.full_name or row.email, "email": row.email,
            "role": row.role, "status": row.status, "expires_at": row.expires_at,
            "protected": row.role == "owner" or row.email.casefold() == business.owner.email.casefold(),
            "revision": revision(business, row)} for row in invitations[start:start + page_size]],
        "roles": list(BusinessRole.objects.filter(business=business, is_active=True).exclude(preset_key="owner").values("id", "name")),
        "requests": [projection(row) for row in repair_rows().filter(business=business)[:50]]}
