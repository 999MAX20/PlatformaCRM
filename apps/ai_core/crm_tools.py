"""Staff AI commands over the existing CRM validation and domain services.

Provider output is untrusted. This layer accepts a bounded entity/field contract,
never an ORM expression, and prepares the same command that staff later approves.
"""
import hashlib
import json
from dataclasses import dataclass
from types import SimpleNamespace

from django.core.serializers.json import DjangoJSONEncoder
from django.db import transaction
from django.db.models import Q
from rest_framework.exceptions import PermissionDenied, ValidationError

from apps.activities.services import write_activity_event
from apps.ai_core.workflows import assert_employee_tool, assert_workflow_enabled
from apps.businesses.access import Actions, Resources, assert_can, can, can_view_sensitive_field, scope_queryset
from apps.businesses.capabilities import assert_resource_enabled
from apps.clients.models import Client
from apps.clients.serializers import ClientSerializer
from apps.core.archive import archive_instance, can_hard_delete, restore_instance
from apps.core.audit import write_audit_log
from apps.core.models import AuditLog
from apps.crm.models import Deal
from apps.crm.serializers import DealSerializer
from apps.leads.models import Lead
from apps.leads.serializers import LeadSerializer
from apps.scheduling.models import Appointment
from apps.scheduling.serializers import AppointmentSerializer
from apps.tasks.models import Task
from apps.tasks.serializers import TaskSerializer


@dataclass(frozen=True)
class Entity:
    model: type
    serializer: type
    fields: tuple
    search_fields: tuple


ENTITIES = {
    "clients": Entity(Client, ClientSerializer,
        ("full_name", "phone", "email", "source", "notes"), ("full_name", "phone", "email")),
    "leads": Entity(Lead, LeadSerializer,
        ("client", "service", "source", "message", "responsible_user"), ("message", "client__full_name")),
    "deals": Entity(Deal, DealSerializer,
        ("client", "lead", "pipeline", "stage", "title", "amount", "currency", "expected_close_at", "owner", "next_action_at", "notes"), ("title", "client__full_name")),
    "tasks": Entity(Task, TaskSerializer,
        ("title", "description", "client", "lead", "deal", "appointment", "conversation", "assignee", "priority", "due_at", "reminder_at"), ("title", "description")),
    "appointments": Entity(Appointment, AppointmentSerializer,
        ("client", "lead", "service", "resource", "start_at", "notes", "source"), ("client__full_name", "service__name")),
}
MUTATIONS = {"crm_create", "crm_update", "crm_archive", "crm_restore", "crm_transition"}


def request_context(user):
    return SimpleNamespace(user=user, META={}, data={}, query_params={})


def serialize_record(spec, target, user):
    data = spec.serializer(target, context={"request": request_context(user)}).data
    visible = set(spec.fields) | {"id", "status", "is_archived", "created_at", "updated_at"}
    data = {key: value for key, value in data.items() if key in visible}
    resource = next(key for key, value in ENTITIES.items() if value.model == spec.model)
    for field in ("notes", "amount"):
        if field in data and not can_view_sensitive_field(user, target.business, resource, field):
            data.pop(field, None)
            if field == "amount":
                data.pop("currency", None)
    config = assert_workflow_enabled(target.business, "employee")
    for field in spec.fields:
        related = getattr(target, field, None)
        related_resource = next((key for key, value in ENTITIES.items() if isinstance(related, value.model)), None)
        if related_resource and (related_resource not in config["sources"] or not can(user, target.business, related_resource, Actions.VIEW, obj=related).allowed):
            data.pop(field, None)
    return data


def entity_spec(entity):
    if entity not in ENTITIES:
        raise ValidationError({"entity": "Unsupported CRM entity."})
    return ENTITIES[entity]


def scoped_entities(business, user, entity, *, include_archived=False):
    spec = entity_spec(entity)
    config = assert_workflow_enabled(business, "employee")
    if entity not in config["sources"]:
        raise PermissionDenied("This CRM source is disabled for the assistant.")
    assert_resource_enabled(business, entity)
    assert_can(user, business, entity, Actions.VIEW)
    queryset = scope_queryset(spec.model.objects.filter(business=business), user, business, entity, Actions.VIEW)
    return queryset if include_archived else queryset.filter(is_archived=False)


def read_entities(*, business, user, entity, query="", entity_id=None, offset=0, limit=20, include_archived=False):
    assert_employee_tool(business, "crm_read")
    spec = entity_spec(entity)
    queryset = scoped_entities(business, user, entity, include_archived=include_archived)
    if entity_id is not None:
        queryset = queryset.filter(pk=entity_id)
    if query:
        condition = Q()
        for field in spec.search_fields:
            condition |= Q(**{f"{field}__icontains": query})
        queryset = queryset.filter(condition)
    total = queryset.count()
    rows = list(queryset.order_by("pk")[offset:offset + limit])
    return {"entity": entity, "count": total, "offset": offset, "limit": limit,
        "has_more": offset + len(rows) < total,
        "results": [serialize_record(spec, row, user) for row in rows]}


def target_for_command(business, user, entity, entity_id, *, lock=False):
    if type(entity_id) is not int or entity_id <= 0:
        raise ValidationError({"entity_id": "Select a CRM record."})
    queryset = scoped_entities(business, user, entity, include_archived=True)
    if lock:
        # OWN/TEAM selectors may use DISTINCT; lock the base row instead, then
        # recheck object scope under the lock (PostgreSQL rejects FOR UPDATE DISTINCT).
        queryset = entity_spec(entity).model.objects.select_for_update().filter(business=business)
    target = queryset.filter(pk=entity_id).first()
    if target is None:
        raise PermissionDenied("CRM record is not available.")
    assert_can(user, business, entity, Actions.VIEW, obj=target)
    return target


def target_fingerprint(target):
    values = {field.attname: getattr(target, field.attname) for field in target._meta.concrete_fields}
    return hashlib.sha256(json.dumps(values, cls=DjangoJSONEncoder, sort_keys=True).encode()).hexdigest()


def permission_for_tool(tool):
    return Actions.CREATE if tool == "crm_create" else Actions.DELETE if tool in {"crm_archive", "crm_restore"} else Actions.UPDATE


def assert_command_allowed(*, business, user, tool, payload, lock=False, replay=False):
    assert_employee_tool(business, tool)
    entity = payload.get("entity")
    spec = entity_spec(entity)
    # Source availability and VIEW are necessary even for a mutation preview.
    scoped_entities(business, user, entity)
    target = None if tool == "crm_create" else target_for_command(business, user, entity, payload.get("entity_id"), lock=lock)
    assert_can(user, business, entity, permission_for_tool(tool), obj=target)
    if target and target.is_archived and tool != "crm_restore" and not replay:
        raise ValidationError("Restore this record before changing it.")
    if tool == "crm_restore" and not can_hard_delete(user, business, entity):
        raise PermissionDenied("Only authorized administrators may restore records.")
    return spec, target


def validated_details(*, business, user, spec, entity, tool, target, values):
    if not isinstance(values, dict) or set(values) - set(spec.fields):
        raise ValidationError({"values": "Unsupported or protected CRM fields."})
    for field in {"notes", "amount"}.intersection(values):
        if not can_view_sensitive_field(user, business, entity, field):
            raise PermissionDenied("This field is not available to your role.")
    if not values:
        raise ValidationError({"values": "Provide the fields to save."})
    data = {**values, "business": business.pk}
    if target is None:
        if entity == "leads":
            data.setdefault("responsible_user", user.pk)
        if entity == "tasks":
            data.setdefault("assignee", user.pk)
    serializer = spec.serializer(target, data=data, partial=target is not None, context={"request": request_context(user)})
    serializer.is_valid(raise_exception=True)
    candidate = spec.model()
    for field in spec.model._meta.concrete_fields:
        if field.name in serializer.validated_data:
            setattr(candidate, field.name, serializer.validated_data[field.name])
        elif target is not None:
            setattr(candidate, field.attname, getattr(target, field.attname))
    assert_can(user, business, entity, permission_for_tool(tool), obj=candidate)
    for field, related in serializer.validated_data.items():
        if field == "business" or related is None or not hasattr(related, "_meta"):
            continue
        if hasattr(related, "business_id") and related.business_id != business.pk:
            raise ValidationError({field: "Related record must belong to this business."})
        related_entity = next((key for key, value in ENTITIES.items() if isinstance(related, value.model)), None)
        if related_entity:
            if related.is_archived:
                raise ValidationError({field: "An archived record cannot be linked."})
            assert_can(user, business, related_entity, Actions.VIEW, obj=related)
        if field in {"assignee", "owner", "responsible_user"}:
            from apps.businesses.assignment_policy import assert_assignment_allowed
            assert_assignment_allowed(actor=user, business=business, target_user=related, resource=entity)
    if target is None and entity == "deals":
        stage = serializer.validated_data.get("stage")
        if stage is None or stage.is_won or stage.is_lost:
            raise ValidationError({"stage": "Select an open pipeline stage."})
    return serializer


def prepare_command(*, business, user, tool, payload):
    if tool not in MUTATIONS or not isinstance(payload, dict):
        raise ValidationError("Unsupported CRM command.")
    if set(payload) - {"entity", "entity_id", "values", "action", "reason"}:
        raise ValidationError("Unsupported CRM command arguments.")
    spec, target = assert_command_allowed(business=business, user=user, tool=tool, payload=payload)
    if tool in {"crm_create", "crm_update"}:
        validated_details(business=business, user=user, spec=spec, entity=payload["entity"], tool=tool, target=target, values=payload.get("values"))
    if tool == "crm_transition":
        from apps.ai_core.crm_transitions import validate_transition
        validate_transition(payload)
    prepared = {**payload, "requires_confirmation": True}
    if target:
        prepared["expected_version"] = target_fingerprint(target)
        record = serialize_record(spec, target, user)
        preview_fields = set(payload.get("values", {}))
        if tool == "crm_transition":
            preview_fields.update({"status", "stage", "owner", "assignee", "responsible_user", "start_at", "resource"})
        prepared["before"] = {key: value for key, value in record.items() if key in preview_fields}
    return json.loads(json.dumps(prepared, cls=DjangoJSONEncoder))


@transaction.atomic
def execute_command(log, user):
    spec, target = assert_command_allowed(business=log.business, user=user, tool=log.tool_name, payload=log.input_json, lock=True)
    payload = log.input_json
    if target and payload.get("expected_version") != target_fingerprint(target):
        raise ValidationError("CRM record changed. Prepare and confirm a new proposal.")
    request = request_context(user)
    if log.tool_name in {"crm_create", "crm_update"}:
        serializer = validated_details(business=log.business, user=user, spec=spec, entity=payload["entity"], tool=log.tool_name, target=target, values=payload.get("values"))
        from apps.ai_core.crm_writes import save_details
        target = save_details(serializer, entity=payload["entity"], actor=user, request=request)
    elif log.tool_name == "crm_archive":
        if isinstance(target, Client):
            from apps.clients.lifecycle import archive_client
            target = archive_client(request=request, client=target, reason=payload.get("reason", ""))
        else:
            target = archive_instance(request, target, reason=payload.get("reason", ""))
    elif log.tool_name == "crm_restore":
        target = restore_instance(request, target)
    else:
        from apps.ai_core.crm_transitions import execute_transition
        target = execute_transition(target, payload, user, request)
    write_audit_log(request, AuditLog.Actions.UPDATE, target, metadata={"kind": "ai_crm_command", "tool_call_id": log.pk, "tool": log.tool_name})
    return {"entity": payload["entity"], "entity_id": target.pk,
        "record": serialize_record(spec, target, user)}
