"""Paginated child records with explicit parent/Business ownership and projections."""
from django.db.models import Q
from rest_framework.exceptions import ValidationError

from apps.activities.models import ActivityEvent, Note, TaggedObject
from apps.bots.models import BotMessage
from apps.core.models import CustomFieldValue
from apps.tasks.models import TaskComment


ENTITY_TYPES = {"clients": "client", "leads": "lead", "deals": "deal", "tasks": "task",
                "appointments": "appointment", "conversations": "conversation"}


def child_sections(kind):
    result = ["notes", "activity", "tags"] if kind in ENTITY_TYPES else []
    if kind in ("clients", "leads", "deals", "appointments"):
        result.insert(0, "custom_fields")
    if kind == "tasks":
        result.insert(0, "comments")
    if kind == "conversations":
        result.insert(0, "messages")
    return result


def child_records(business, kind, record, section):
    if section not in child_sections(kind):
        raise ValidationError({"section": "Unsupported record section."})
    if section == "messages":
        return BotMessage.objects.filter(conversation=record, conversation__business=business).order_by("-created_at", "-pk")
    if section == "comments":
        return TaskComment.objects.filter(task=record, task__business=business).select_related("author").order_by("-created_at", "-pk")
    entity_type = ENTITY_TYPES[kind]
    if section == "custom_fields":
        return CustomFieldValue.objects.filter(business=business, entity_type=entity_type, entity_id=str(record.pk),
            definition__business=business, definition__entity_type=entity_type).select_related("definition").order_by("definition__sort_order", "pk")
    if section == "tags":
        return TaggedObject.objects.filter(business=business, entity_type=entity_type, entity_id=str(record.pk),
            tag__business=business).select_related("tag").order_by("tag__name", "pk")
    model = Note if section == "notes" else ActivityEvent
    parent = Q(entity_type=entity_type, entity_id=str(record.pk))
    if kind == "clients":
        parent |= Q(client=record)
    return model.objects.filter(parent, business=business).select_related("author" if section == "notes" else "actor").order_by("-created_at", "-pk")


def child_projection(row, section, users):
    data = {"id": row.pk, "created_at": row.created_at}
    if section == "messages":
        return {**data, "text": row.text, "direction": row.direction, "sender_type": row.sender_type,
                "status": row.status, "sent_at": row.sent_at, "delivered_at": row.delivered_at, "read_at": row.read_at}
    if section == "custom_fields":
        value = row.value_json.get("value") if isinstance(row.value_json, dict) else None
        if not isinstance(value, (str, int, float, bool, type(None))) and not (isinstance(value, list) and all(isinstance(item, str) for item in value)):
            value = None
        return {**data, "label": row.definition.label, "field_type": row.definition.field_type, "value": value}
    if section == "tags":
        return {**data, "label": row.tag.name}
    actor = getattr(row, "author", None) if section in ("comments", "notes") else row.actor
    return {**data, "text": row.text,
            "author": (actor.full_name or actor.email) if actor is not None and actor.pk in users else None,
            **({"event_type": row.event_type} if section == "activity" else {})}
