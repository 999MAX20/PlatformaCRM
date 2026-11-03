from django.db.models import Exists, OuterRef, Prefetch, Q

from apps.branches.access import accessible_branches
from apps.businesses.access import Actions, Resources, can, scope_queryset, team_user_ids_for
from apps.businesses.capabilities import resource_is_enabled
from apps.businesses.models import BusinessMember, RolePermission
from apps.clients.models import Client
from apps.scheduling.models import Appointment, VisitPlan, VisitPlanStep


def readable_plan_steps(*, business, actor):
    steps = VisitPlanStep.objects.filter(plan__business=business)
    permission = can(actor, business, Resources.APPOINTMENTS, Actions.VIEW)
    if not permission.allowed or not resource_is_enabled(business, Resources.APPOINTMENTS):
        return steps.none()
    branches = accessible_branches(actor, business).values("pk")
    appointments = scope_queryset(Appointment.objects.filter(business=business), actor, business, Resources.APPOINTMENTS)
    appointments = appointments.filter(Q(branch__isnull=True) | Q(branch_id__in=branches))
    undated = Q(appointment__isnull=True) & (Q(branch__isnull=True) | Q(branch_id__in=branches))
    if permission.scope != RolePermission.Scopes.BUSINESS:
        ids = [actor.pk] if permission.scope == RolePermission.Scopes.OWN else team_user_ids_for(actor, business)
        active = BusinessMember.objects.filter(business=business, is_active=True).values("user_id")
        undated &= Q(resource__business=business, resource__linked_user_id__in=ids)
        undated &= Q(resource__linked_user_id=business.owner_id) | Q(resource__linked_user_id__in=active)
    return steps.filter(undated | Q(appointment_id__in=appointments.values("pk")))


def readable_plans(*, business, actor):
    plans = VisitPlan.objects.filter(business=business)
    if not resource_is_enabled(business, Resources.CLIENTS):
        return plans.none()
    clients = scope_queryset(Client.objects.filter(business=business), actor, business, Resources.CLIENTS)
    steps = readable_plan_steps(business=business, actor=actor)
    plans = plans.filter(client_id__in=clients.values("pk")).annotate(
        _visible_step=Exists(steps.filter(plan_id=OuterRef("pk"))),
        _any_step=Exists(VisitPlanStep.objects.filter(plan_id=OuterRef("pk"))))
    permission = can(actor, business, Resources.APPOINTMENTS, Actions.VIEW)
    condition = Q(_visible_step=True)
    if permission.allowed and permission.scope == RolePermission.Scopes.BUSINESS and resource_is_enabled(business, Resources.APPOINTMENTS):
        condition |= Q(_any_step=False)
    return plans.filter(condition).select_related("business", "client", "responsible_user").prefetch_related(
        Prefetch("steps", queryset=VisitPlanStep.objects.select_related("resource", "branch", "service", "appointment", "appointment__resource", "appointment__branch")))
