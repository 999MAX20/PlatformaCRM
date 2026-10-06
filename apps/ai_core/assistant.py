from apps.clients.models import Client
from apps.businesses.access import Actions, Resources, scope_queryset
from apps.core.permissions import user_can_access_business
from apps.leads.models import Lead
from apps.scheduling.models import Appointment
from apps.services.models import Service
from apps.tasks.models import Task
from apps.crm.models import Deal
from django.utils import timezone
from django.core.serializers.json import DjangoJSONEncoder
import json
from apps.scheduling.availability import business_zone


def build_crm_context(business, user=None):
    from apps.ai_core.workflows import assert_workflow_enabled
    config = assert_workflow_enabled(business, "employee")
    now = timezone.now()
    zone = business_zone(business)
    today = timezone.localtime(now, zone).date()
    clients_queryset = _scoped_queryset(
        Client.objects.filter(business=business),
        user=user,
        business=business,
        resource=Resources.CLIENTS,
    )
    leads_queryset = _scoped_queryset(
        Lead.objects.select_related("client", "service").filter(business=business),
        user=user,
        business=business,
        resource=Resources.LEADS,
    )
    appointments_queryset = _scoped_queryset(
        Appointment.objects.select_related("client", "service", "resource").filter(business=business),
        user=user,
        business=business,
        resource=Resources.APPOINTMENTS,
    )
    leads = leads_queryset.order_by("-created_at")[:8]
    appointments = appointments_queryset.filter(start_at__gte=timezone.now(), status__in=[Appointment.Statuses.CREATED, Appointment.Statuses.CONFIRMED]).order_by("start_at")[:8]
    clients_count = clients_queryset.count()
    new_leads_count = leads_queryset.filter(status=Lead.Statuses.NEW).count()
    open_appointments_count = appointments_queryset.filter(
        business=business,
        status__in=[Appointment.Statuses.CREATED, Appointment.Statuses.CONFIRMED],
    ).count()

    tasks_queryset = _scoped_queryset(Task.objects.filter(business=business, is_archived=False), user=user, business=business, resource=Resources.TASKS)
    context = {
        "generated_at": timezone.localtime(now, zone).isoformat(),
        "local_date": today.isoformat(),
        "timezone": business.timezone,
        "coverage": "Permission-scoped summary and up to 8 records per category; not a complete history. Financial receipts/refunds are not supplied.",
        "services": list(_scoped_queryset(Service.objects.filter(business=business, is_active=True), user=user, business=business, resource=Resources.APPOINTMENTS).order_by("name").values("id", "name", "price_from")[:8]),
        "tasks": list(tasks_queryset.order_by("due_at").values("id", "title", "status", "due_at")[:8]),
        "deals": list(_scoped_queryset(Deal.objects.filter(business=business), user=user, business=business, resource=Resources.DEALS).order_by("-created_at").values("id", "title", "status")[:8]),
        "business": {"id": business.id, "name": business.name, "type": business.business_type, "city": business.city},
        "summary": {
            "clients_count": clients_count,
            "new_leads_count": new_leads_count,
            "open_appointments_count": open_appointments_count,
            "overdue_tasks_count": tasks_queryset.filter(due_at__lt=now, status__in=[Task.Statuses.OPEN, Task.Statuses.IN_PROGRESS]).count(),
        },
        "latest_leads": [
            {
                "id": lead.id,
                "client": lead.client.full_name,
                "service": lead.service.name if lead.service else None,
                "source": lead.source,
                "status": lead.status,
                "message": lead.message,
                "created_at": timezone.localtime(lead.created_at, zone).isoformat(),
            }
            for lead in leads
        ],
        "upcoming_appointments": [
            {
                "id": appointment.id,
                "client": appointment.client.full_name,
                "service": appointment.service.name,
                "resource": appointment.resource.name if appointment.resource else None,
                "status": appointment.status,
                "start_at": timezone.localtime(appointment.start_at, zone).isoformat(),
            }
            for appointment in appointments
        ],
    }
    # Provider prose should not have to calculate local business dates or offsets.
    for task in context["tasks"]:
        if task["due_at"] is not None:
            task["due_at"] = timezone.localtime(task["due_at"], zone).isoformat()
    for source, keys, counters in (
        ("clients", (), ("clients_count",)),
        ("leads", ("latest_leads",), ("new_leads_count",)),
        ("appointments", ("upcoming_appointments", "services"), ("open_appointments_count",)),
        ("tasks", ("tasks",), ("overdue_tasks_count",)),
        ("deals", ("deals",), ()),
    ):
        if source not in config["sources"]:
            for key in keys:
                context.pop(key, None)
            for key in counters:
                context["summary"].pop(key, None)
    context["disabled_sources"] = sorted(set(("clients", "leads", "appointments", "tasks", "deals", "knowledge")) - set(config["sources"]))
    return json.loads(json.dumps(context, cls=DjangoJSONEncoder))


def assert_business_access(user, business):
    if not user_can_access_business(user, business):
        raise PermissionError("You do not have access to this business.")


def _scoped_queryset(queryset, *, user, business, resource):
    if not user or not user.is_authenticated:
        return queryset.none()
    return scope_queryset(queryset, user, business, resource, Actions.VIEW)
