"""Fail closed when a stored export's authorization context has changed."""
import hashlib
import json

from rest_framework.exceptions import PermissionDenied

from apps.businesses.access import (
    Actions, PERMISSION_CATALOG, Resources, can, can_view_sensitive_field,
    scope_queryset, team_user_ids_for,
)
from apps.businesses.capabilities import resource_is_enabled


def export_access_fingerprint(job, actor):
    from apps.accounts.models import User
    from apps.businesses.models import Business, BusinessMember
    from apps.branches.access import accessible_branches
    from apps.core.export_jobs import export_resource

    actor = User.objects.filter(pk=getattr(actor, "pk", None)).first()
    job.business = Business.objects.get(pk=job.business_id)
    resource = export_resource(job.export_key)
    if not actor or not actor.is_active or resource is None:
        raise PermissionDenied("Export access is no longer available.")
    if actor.pk == job.actor_id:
        job.actor = actor
    if not resource_is_enabled(job.business, resource) or not can(
        actor, job.business, resource, Actions.VIEW
    ).allowed:
        raise PermissionDenied("Export access is no longer available.")
    resources = sorted(PERMISSION_CATALOG) if job.kind == "analytics_report" else [resource]
    access = {}
    for key in resources:
        permission = can(actor, job.business, key, Actions.VIEW)
        access[key] = [permission.allowed, permission.scope, resource_is_enabled(job.business, key)]
    context = {
        "version": 1, "actor": actor.pk, "business": job.business_id,
        "kind": job.kind, "key": job.export_key, "access": access,
        "branches": list(accessible_branches(actor, job.business).order_by("pk").values_list("pk", flat=True)),
    }
    if any(value[1] == "team" for value in access.values()):
        context["team"] = sorted(team_user_ids_for(actor, job.business))
    # Restricted scopes can change without editing a role (e.g. reassignment).
    from apps.clients.models import Client
    from apps.crm.models import Deal
    from apps.leads.models import Lead
    from apps.scheduling.models import Appointment
    from apps.tasks.models import Task
    from apps.bots.models import BotConversation
    from apps.payments.models import Payment

    models = {Resources.CLIENTS: Client, Resources.LEADS: Lead, Resources.DEALS: Deal,
              Resources.APPOINTMENTS: Appointment, Resources.TASKS: Task,
              Resources.CONVERSATIONS: BotConversation, Resources.PAYMENTS: Payment}
    for key, model in models.items():
        if key in access and access[key][1] in {"own", "team"}:
            rows = scope_queryset(model.objects.filter(business=job.business), actor,
                                  job.business, key, Actions.VIEW)
            digest = hashlib.sha256()
            for pk in rows.order_by("pk").values_list("pk", flat=True).iterator(chunk_size=2000):
                digest.update(f"{pk},".encode())
            context[key] = digest.hexdigest()
    if job.kind == "analytics_report":
        from apps.analytics.crm_metrics import _performance_scope, _visible_performance_members

        context["performance"] = [_performance_scope(business=job.business, user=actor),
                                  list(_visible_performance_members(business=job.business, user=actor)
                                       .order_by("pk").values_list("pk", flat=True))]
        context["members"] = list(BusinessMember.objects.filter(business=job.business)
                                  .order_by("pk").values_list("user_id", "role", "is_active"))
        context["sensitive"] = [can_view_sensitive_field(actor, job.business, Resources.CLIENTS, field)
                                for field in ("notes", "amount")]
    return hashlib.sha256(json.dumps(context, sort_keys=True).encode()).hexdigest()


def assert_export_download_access(job, actor):
    fingerprint = export_access_fingerprint(job, actor)
    if job.parameters_json.get("access_fingerprint_v1") != fingerprint:
        raise PermissionDenied("Export access has changed. Request a new export.")
