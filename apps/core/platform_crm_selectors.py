"""Explicit platform read projections; never reuse serializers with merchant writes."""
from django.db.models import Q
from django.shortcuts import get_object_or_404
from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from apps.bots.models import BotChannel, BotConversation
from apps.businesses.models import Business, BusinessMember
from apps.clients.models import Client
from apps.crm.models import Deal
from apps.integrations.models import BusinessConnector
from apps.leads.models import Lead
from apps.payments.models import Payment
from apps.scheduling.models import Appointment
from apps.support.access import assert_platform_actor
from apps.tasks.models import Task


MODELS = {"clients": Client, "leads": Lead, "deals": Deal, "tasks": Task,
          "appointments": Appointment, "conversations": BotConversation,
          "payments": Payment, "connectors": BusinessConnector, "channels": BotChannel}
FIELDS = {
    "clients": ("full_name", "phone", "email", "source", "source_detail", "notes"),
    "leads": ("source", "message", "lost_reason", "lost_at"),
    "deals": ("title", "amount", "currency", "probability", "expected_close_at", "source", "notes", "lost_reason", "won_at", "lost_at", "next_action_at", "stage_entered_at"),
    "tasks": ("title", "description", "priority", "due_at", "reminder_at", "waiting_reason", "waiting_until", "completed_at", "cancelled_at", "cancel_reason"),
    "appointments": ("start_at", "end_at", "source", "notes", "booked_price", "booked_duration_minutes", "branch_name", "branch_address"),
    "conversations": ("channel", "priority", "bot_enabled", "handoff_required", "handoff_reason", "ai_resume_at", "close_reason", "last_message_at", "unread_count"),
    "payments": ("kind", "amount", "refunded_amount", "currency", "occurred_at", "method", "source", "note", "reason"),
    "connectors": ("name", "provider", "capability", "connected_at", "last_sync_at", "next_sync_at"),
    "channels": ("channel",),
}
LINKS = {
    "clients": {}, "leads": {"client": "clients", "service": None},
    "deals": {"client": "clients", "lead": "leads", "pipeline": None, "stage": None},
    "tasks": {"client": "clients", "lead": "leads", "deal": "deals", "appointment": "appointments", "conversation": "conversations", "parent_task": "tasks", "specialist": None},
    "appointments": {"client": "clients", "lead": "leads", "service": None, "resource": None},
    "conversations": {"client": "clients", "lead": "leads", "deal": "deals", "bot": None},
    "payments": {"client": "clients", "deal": "deals", "appointment": "appointments", "original": "payments"},
    "connectors": {}, "channels": {"bot": None},
}
USERS = {"clients": (), "leads": ("responsible_user",), "deals": ("owner",),
         "tasks": ("assignee", "created_by", "completed_by", "cancelled_by"), "appointments": (),
         "conversations": ("assigned_to",), "payments": ("created_by",), "connectors": ("created_by",), "channels": ()}
SEARCH = {"clients": ("full_name", "phone", "email"), "leads": (), "deals": ("title",),
          "tasks": ("title",), "appointments": (), "conversations": (), "payments": (), "connectors": ("name", "provider"), "channels": ("channel", "bot__name")}


class ClinicReadFilters(serializers.Serializer):
    search = serializers.CharField(default="", allow_blank=True, max_length=200)
    status = serializers.CharField(required=False, max_length=32)
    archive = serializers.ChoiceField(choices=("active", "archived", "all"), default="active")
    client = serializers.IntegerField(required=False, min_value=1, max_value=9223372036854775807)
    page = serializers.IntegerField(default=1, min_value=1)
    page_size = serializers.IntegerField(default=20, min_value=1, max_value=50)


def clinic_access(actor, business_id):
    # Database role check also rejects a stale authenticated User instance.
    assert_platform_actor(actor)
    return get_object_or_404(Business, pk=business_id)


def clinic_kind(kind):
    if kind not in MODELS:
        raise ValidationError({"kind": "Unsupported clinic record type."})
    return MODELS[kind]


def clinic_queryset(business, kind):
    model = clinic_kind(kind)
    rows = model.objects.filter(**{"bot__business" if kind == "channels" else "business": business})
    related = [*LINKS[kind], *USERS[kind]]
    return rows.select_related(*related) if related else rows


def clinic_records(business, kind, params):
    model = clinic_kind(kind)
    rows = clinic_queryset(business, kind)
    has_archive = any(field.name == "is_archived" for field in model._meta.fields)
    if has_archive and params["archive"] != "all":
        rows = rows.filter(is_archived=params["archive"] == "archived")
    elif not has_archive and params["archive"] == "archived":
        raise ValidationError({"archive": "This record type has no archive."})
    if params.get("status"):
        field = "kind" if kind == "payments" else "status"
        if field not in {item.name for item in model._meta.fields}:
            raise ValidationError({"status": "This record type has no status."})
        if params["status"] not in dict(model._meta.get_field(field).choices):
            raise ValidationError({"status": "Invalid status."})
        rows = rows.filter(**{field: params["status"]})
    if params.get("client"):
        if "client" not in LINKS[kind]:
            raise ValidationError({"client": "This record type has no client."})
        get_object_or_404(Client, business=business, pk=params["client"])
        rows = rows.filter(client_id=params["client"])
    needle = params["search"]
    if needle:
        condition = Q(pk__in=[])
        for field in SEARCH[kind]:
            condition |= Q(**{f"{field}__icontains": needle})
        if "client" in LINKS[kind]:
            condition |= Q(client__business=business, client__full_name__icontains=needle)
            condition |= Q(client__business=business, client__phone__icontains=needle)
        if needle.isascii() and needle.isdecimal() and len(needle) < 19:
            condition |= Q(pk=int(needle))
        rows = rows.filter(condition)
    ordering = "occurred_at" if kind == "payments" else "start_at" if kind == "appointments" else "created_at" if kind == "clients" else "updated_at"
    return rows.order_by(f"-{ordering}", "-pk")


def clinic_user_ids(business):
    # Inactive members remain valid historical names. Foreign users do not.
    return {business.owner_id, *BusinessMember.objects.filter(business=business).values_list("user_id", flat=True)}


def relation_label(row):
    return getattr(row, "full_name", None) or getattr(row, "title", None) or getattr(row, "name", None) or f"#{row.pk}"


def record_projection(row, kind, user_ids, *, detail=False):
    business_id = row.bot.business_id if kind == "channels" else row.business_id
    relations = []
    for field, target in LINKS[kind].items():
        related = getattr(row, field, None)
        if related is not None and related.business_id == business_id:
            relations.append({"field": field, "kind": target, "id": related.pk, "label": relation_label(related)})
    people = [{"field": field, "id": user.pk, "name": user.full_name or user.email, "active": user.is_active}
              for field in USERS[kind] if (user := getattr(row, field, None)) is not None and user.pk in user_ids]
    title = getattr(row, "full_name", None) or getattr(row, "title", None) or getattr(row, "name", None) or (row.channel if kind == "channels" else None)
    if not title:
        title = next((item["label"] for item in relations if item["field"] == "client"), f"#{row.pk}")
    data = {"id": row.pk, "kind": kind, "business_id": business_id, "title": title,
            "status": getattr(row, "status", None) or (row.kind if kind == "payments" else None),
            "is_archived": getattr(row, "is_archived", False), "created_at": row.created_at,
            "updated_at": getattr(row, "updated_at", row.created_at), "relations": relations, "people": people,
            "fields": {}}
    if detail:
        fields = list(FIELDS[kind])
        if hasattr(row, "is_archived"):
            fields.extend(("archived_at", "archive_reason"))
        data["fields"] = {field: getattr(row, field) for field in fields}
    else:
        preview = {"clients": ("phone", "email"), "leads": ("source",), "deals": ("amount", "currency"),
                   "tasks": ("due_at", "priority"), "appointments": ("start_at", "end_at"),
                   "conversations": ("channel", "last_message_at", "unread_count"),
                   "payments": ("amount", "currency", "occurred_at"), "connectors": ("provider", "last_sync_at"), "channels": ("channel",)}
        data["fields"] = {field: getattr(row, field) for field in preview[kind]}
    return data
