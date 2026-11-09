from django.db.models import Q
from rest_framework.exceptions import ValidationError

from apps.businesses.access import Actions, Resources, assert_can, can_view_sensitive_field
from apps.businesses.capabilities import assert_resource_enabled
from apps.clients.field_policy import validate_client_write_fields
from apps.clients.identity import normalize_client_identity
from apps.clients.models import Client
from apps.core.audit import write_actor_audit_log
from apps.core.import_export import create_import_client
from apps.core.models import AuditLog
from apps.scheduling.models import Appointment, Resource
from apps.scheduling.resource_services import create_resource
from apps.services.models import Service


MODELS = {"clients": Client, "services": Service, "specialists": Resource, "appointments": Appointment}
RESOURCES = {"clients": Resources.CLIENTS, "services": Resources.SETTINGS,
             "specialists": Resources.SETTINGS, "appointments": Resources.APPOINTMENTS}


def accessible_entity(*, business, actor, entity_type, pk, action=Actions.VIEW, lock=False):
    queryset = MODELS[entity_type].objects.filter(business=business, pk=pk)
    obj = (queryset.select_for_update() if lock else queryset).first()
    if obj is None:
        raise ValidationError("The selected CRM record is not available.")
    if entity_type == "specialists" and obj.resource_type != Resource.ResourceTypes.STAFF:
        raise ValidationError("Select a specialist, not another resource type.")
    assert_resource_enabled(business, RESOURCES[entity_type])
    assert_can(actor, business, RESOURCES[entity_type], Actions.VIEW, obj=obj)
    assert_can(actor, business, RESOURCES[entity_type], action, obj=obj)
    if getattr(obj, "is_archived", False) or getattr(obj, "retired_at", None):
        raise ValidationError("Archived records cannot be changed by import.")
    return obj


def matching_entities(*, business, entity_type, values):
    model = MODELS[entity_type]
    query = model.objects.filter(business=business)
    if entity_type == "clients":
        identity = normalize_client_identity(phone=values.get("phone", ""), email=values.get("email", ""))
        filters = Q()
        if identity["normalized_phone"]:
            filters |= Q(normalized_phone=identity["normalized_phone"])
        if identity["normalized_email"]:
            filters |= Q(normalized_email=identity["normalized_email"])
        return list(query.filter(filters)[:3]) if filters else []
    if entity_type in {"services", "specialists"}:
        if entity_type == "specialists":
            query = query.filter(resource_type=Resource.ResourceTypes.STAFF)
        return list(query.filter(name__iexact=values["name"])[:3])
    return []


def write_basic_entity(*, business, actor, entity_type, values, decision, reference):
    resource = RESOURCES[entity_type]
    assert_resource_enabled(business, resource)
    target_id = decision.get("target_id")
    action = decision.get("action", "create")
    existing = accessible_entity(business=business, actor=actor, entity_type=entity_type,
        pk=target_id, action=Actions.UPDATE, lock=True) if target_id else None
    matches = matching_entities(business=business, entity_type=entity_type, values=values)
    if matches and (existing is None or len(matches) != 1 or matches[0].pk != existing.pk):
        # Do not expose matched records before object/field-scope checks.
        raise ValidationError({"duplicate": "A possible match requires an explicit existing-record decision."})
    if action in {"fill", "update"} and existing is None:
        raise ValidationError({"target_id": "Select the existing record to change."})
    if action == "create" and existing is not None:
        raise ValidationError({"target_id": "A new record cannot have an existing target."})
    if entity_type == "clients":
        values = validate_client_write_fields(dict(values),
            notes_allowed=can_view_sensitive_field(actor, business, Resources.CLIENTS, "notes"))
    before_version = existing.updated_at.isoformat() if existing else None
    before_values = {key: getattr(existing, key) for key in values} if existing else {}
    if existing:
        selected = decision.get("update_fields", [])
        changes = {key: value for key, value in values.items()
                   if (action == "fill" and getattr(existing, key, None) in (None, ""))
                   or (action == "update" and key in selected)}
        if action == "update" and not selected:
            raise ValidationError({"update_fields": "Select the fields to overwrite."})
        for key, value in changes.items():
            setattr(existing, key, value)
        existing.full_clean()
        if changes:
            existing.save(update_fields=[*changes, "updated_at"])
        obj, outcome = existing, "updated" if changes else "unchanged"
    else:
        candidate = MODELS[entity_type](business=business, **values)
        assert_can(actor, business, resource, Actions.CREATE if entity_type == "clients" else Actions.UPDATE, obj=candidate)
        if entity_type == "clients":
            obj = create_import_client(business, values, actor=actor)
        elif entity_type == "specialists":
            candidate.full_clean()
            obj = create_resource(business=business, resource_type=Resource.ResourceTypes.STAFF, **values)
        else:
            candidate.full_clean()
            obj = candidate
            obj.save()
        outcome = "created"
    write_actor_audit_log(actor=actor, action=AuditLog.Actions.CREATE if outcome == "created" else AuditLog.Actions.UPDATE,
        instance=obj, metadata={"kind": "import", "reference": reference, "fields": sorted(values)})
    return obj, outcome, before_version, {key: getattr(obj, key) for key in values}, before_values
