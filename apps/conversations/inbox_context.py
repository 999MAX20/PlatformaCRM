"""Small, independently authorized read projection for the Inbox inspector."""
from django.db.models import CharField, F, Q, Subquery
from django.db.models.functions import Cast
from django.utils import timezone

from apps.activities.models import ActivityEvent
from apps.activities.taxonomy import ActivityEvents
from apps.businesses.access import Actions, Resources, can, can_view_sensitive_field
from apps.businesses.capabilities import resource_is_enabled
from apps.core.crm_read_scope import readable_link, readable_queryset
from apps.scheduling.models import Appointment
from apps.tasks.models import Task
from apps.clients.models import Client
from apps.leads.models import Lead
from apps.crm.models import Deal
from rest_framework.exceptions import PermissionDenied, ValidationError


LINK_RESOURCES = {"client": Resources.CLIENTS, "lead": Resources.LEADS, "deal": Resources.DEALS}
APPOINTMENT_LIMIT = 3


def inbox_link_candidates(conversation, *, actor, kind, search=""):
    """Scope before searching/limiting; never mix a member's businesses."""
    models = {"client": (Client, ("full_name", "phone", "email")),
              "lead": (Lead, ("message",)), "deal": (Deal, ("title",))}
    if kind not in models:
        raise ValidationError({"kind": "Choose client, lead or deal."})
    business = conversation.business
    if not _allowed(actor, business, LINK_RESOURCES[kind]):
        raise PermissionDenied()
    model, fields = models[kind]
    queryset = readable_queryset(model.objects.filter(is_archived=False), actor=actor,
                                 business=business, resource=LINK_RESOURCES[kind])
    if search.strip():
        condition = Q()
        for field in fields:
            condition |= Q(**{f"{field}__icontains": search.strip()[:200]})
        queryset = queryset.filter(condition)
    return [{"id": entity.id, "title": getattr(entity, fields[0]),
             "detail": (entity.phone or entity.email) if kind == "client" else entity.status}
            for entity in queryset.order_by("-id")[:8]]


def readable_inbox_links(conversation, actor):
    return {
        key: readable_link(getattr(conversation, key), actor=actor,
                           business=conversation.business, resource=resource)
        for key, resource in LINK_RESOURCES.items()
    }


def inbox_list_link_visibility(conversations, *, actor):
    """Batch linked-record authorization for a page, rather than per row."""
    businesses = {item.business_id: item.business for item in conversations}
    result = {}
    for business_id, business in businesses.items():
        for key, model in (("client", Client), ("lead", Lead), ("deal", Deal)):
            ids = {getattr(item, f"{key}_id") for item in conversations if item.business_id == business_id}
            visible = readable_queryset(model.objects.filter(pk__in=ids), actor=actor,
                                        business=business, resource=LINK_RESOURCES[key])
            result[(business_id, key)] = set(visible.values_list("pk", flat=True))
    return result


def _allowed(actor, business, resource, action=Actions.VIEW, obj=None):
    return resource_is_enabled(business, resource) and can(actor, business, resource, action, obj=obj).allowed


def _section(entity, *, original, actor, business, resource):
    if not _allowed(actor, business, resource) or (original is not None and entity is None):
        return {"state": "forbidden", "data": None}
    return {"state": "available" if entity else "empty", "data": None}


def _appointment_payload(appointment, *, actor, business):
    # A visible appointment does not grant access to configuration from another
    # business or a hidden specialist/service resource.
    service = readable_link(appointment.service, actor=actor, business=business, resource=Resources.SETTINGS)
    resource = readable_link(appointment.resource, actor=actor, business=business, resource=Resources.SETTINGS)
    return {
        "id": appointment.id,
        "start_at": appointment.start_at.isoformat(),
        "end_at": appointment.end_at.isoformat(),
        "status": appointment.status,
        "service_name": service.name if service else "",
        "resource_name": resource.name if resource else "",
        "href": f"/app/calendar/{appointment.id}",
    }


def _appointments(conversation, client, *, actor, now):
    business = conversation.business
    empty = {"state": "empty", "kind": "client", "items": [], "has_more": False}
    if not _allowed(actor, business, Resources.APPOINTMENTS) or (conversation.client_id and not client):
        return {**empty, "state": "forbidden"}
    if client is None:
        return empty
    upcoming = readable_queryset(
        Appointment.objects.select_related("service", "resource").filter(
            client=client, is_archived=False, start_at__gte=now,
            status__in=[Appointment.Statuses.CREATED, Appointment.Statuses.CONFIRMED, Appointment.Statuses.RESCHEDULED],
        ), actor=actor, business=business, resource=Resources.APPOINTMENTS,
    ).order_by("start_at", "id")
    # Staff and automatic booking both write this existing provenance event.
    # A shared client or lead alone is not evidence of a conversation booking.
    provenance = ActivityEvent.objects.filter(
        business=business, entity_type="Appointment", event_type=ActivityEvents.APPOINTMENT_CREATED,
        metadata__conversation_id=conversation.id,
    ).values("entity_id")
    linked = upcoming.annotate(_context_id=Cast("pk", CharField())).filter(_context_id__in=Subquery(provenance))
    rows = list(linked[:APPOINTMENT_LIMIT + 1])
    kind = "conversation" if rows else "client"
    if not rows:
        rows = list(upcoming[:APPOINTMENT_LIMIT + 1])
    return {
        "state": "available" if rows else "empty", "kind": kind,
        "items": [_appointment_payload(row, actor=actor, business=business) for row in rows[:APPOINTMENT_LIMIT]],
        "has_more": len(rows) > APPOINTMENT_LIMIT,
    }


def build_inbox_context(conversation, *, actor, now=None):
    business = conversation.business
    links = readable_inbox_links(conversation, actor)
    sections = {
        key: _section(links[key], original=getattr(conversation, key), actor=actor,
                      business=business, resource=resource)
        for key, resource in LINK_RESOURCES.items()
    }
    client, lead, deal = (links[key] for key in ("client", "lead", "deal"))
    if client:
        sections["client"]["data"] = {
            "id": client.id, "name": client.full_name, "phone": client.phone, "email": client.email,
            "notes": client.notes if can_view_sensitive_field(actor, business, Resources.CLIENTS, "notes") else "",
            "href": f"/app/clients/{client.id}", "is_archived": client.is_archived,
        }
    if lead:
        sections["lead"]["data"] = {
            "id": lead.id, "title": lead.message, "status": lead.status,
            "href": f"/app/leads/{lead.id}",
        }
    if deal:
        stage = readable_link(deal.stage, actor=actor, business=business, resource=Resources.DEALS)
        amount_allowed = can_view_sensitive_field(actor, business, Resources.DEALS, "amount")
        sections["deal"]["data"] = {
            "id": deal.id, "title": deal.title, "status": deal.status,
            "stage_name": stage.name if stage and stage.pipeline_id == deal.pipeline_id else "",
            "amount": str(deal.amount) if amount_allowed else None,
            "currency": deal.currency if amount_allowed else "", "href": f"/app/deals/{deal.id}",
        }
    task = readable_queryset(
        Task.objects.filter(conversation=conversation, is_archived=False,
                            status__in=[Task.Statuses.OPEN, Task.Statuses.IN_PROGRESS]),
        actor=actor, business=business, resource=Resources.TASKS,
    ).order_by(F("due_at").asc(nulls_last=True), "id").first()
    update = _allowed(actor, business, Resources.CONVERSATIONS, Actions.UPDATE, conversation)
    actions = {"update": update}
    for key, resource in LINK_RESOURCES.items():
        # Do not offer overwriting a hidden relation or creating its duplicate.
        actions[f"link_{key}"] = update and sections[key]["state"] != "forbidden" and _allowed(actor, business, resource)
        actions[f"create_{key}"] = update and getattr(conversation, f"{key}_id") is None and _allowed(actor, business, resource, Actions.CREATE)
    actions["create_task"] = update and _allowed(actor, business, Resources.TASKS, Actions.CREATE)
    actions["book"] = bool(client and not client.is_archived and _allowed(actor, business, Resources.APPOINTMENTS)
                           and _allowed(actor, business, Resources.APPOINTMENTS, Actions.CREATE))
    return {
        "conversation_id": conversation.id, "business": business.id, "timezone": business.timezone,
        **sections,
        "appointments": _appointments(conversation, client, actor=actor, now=now or timezone.now()),
        "task": {"id": task.id, "title": task.title, "due_at": task.due_at.isoformat() if task.due_at else None,
                 "href": f"/app/tasks?task={task.id}"} if task else None,
        "actions": actions,
    }
