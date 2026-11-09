"""Inbox write acknowledgements never substitute for current CRM read rights."""
from apps.businesses.access import Resources
from apps.clients.models import Client
from apps.core.crm_read_scope import readable_link
from apps.crm.models import Deal
from apps.leads.models import Lead
from apps.scheduling.models import Appointment
from apps.tasks.models import Task


REFERENCE_MODELS = {"client": Client, "lead": Lead, "deal": Deal, "task": Task, "appointment": Appointment}
REFERENCE_RESOURCES = {"client": Resources.CLIENTS, "lead": Resources.LEADS, "deal": Resources.DEALS,
                       "task": Resources.TASKS, "appointment": Resources.APPOINTMENTS}
METADATA_REFERENCES = {
    "conversation_pipeline": {"client_id": "client", "lead_id": "lead", "deal_id": "deal", "task_id": "task"},
    "auto_booking": {"appointment_id": "appointment"},
}


def reference_id(value):
    if isinstance(value, bool) or not isinstance(value, (int, str)):
        return None
    if isinstance(value, str) and not value.isdecimal():
        return None
    try:
        pk = int(value)
    except (ValueError, OverflowError):
        return None
    return pk if 0 < pk <= 2**63-1 else None


def readable_entity_data(entity, *, resource, serializer_class, business, request):
    entity = readable_link(entity, actor=getattr(request, "user", None), business=business, resource=resource)
    return serializer_class(entity, context={"request": request}).data if entity is not None else None


def create_result_data(entity, *, resource, serializer_class, business, request):
    data = readable_entity_data(entity, resource=resource, serializer_class=serializer_class, business=business, request=request)
    return data if data is not None else {"read_restricted": True}


def command_result_data(command, *, model, resource, serializer_class, business, request):
    entity = command.resource
    if command.replayed:
        pk = reference_id(command.resource_id)
        entity = (model.objects.filter(business=business, pk=pk).first()
                  if pk is not None and command.resource_type == model._meta.label_lower else None)
    if entity is not None and not isinstance(entity, model):
        entity = None
    # Never fall back to a historical response body if current target is unavailable.
    return create_result_data(entity, resource=resource, serializer_class=serializer_class, business=business, request=request)


def metadata_reference_ids(conversation, kind):
    metadata = conversation.metadata_json or {}
    if not isinstance(metadata, dict):
        return set()
    ids = set()
    for section, fields in METADATA_REFERENCES.items():
        value = metadata.get(section)
        if isinstance(value, dict):
            ids.update(pk for field, target in fields.items() if target == kind
                       and (pk := reference_id(value.get(field))) is not None)
    return ids


def project_inbox_metadata(metadata, *, business_id, visibility):
    data = dict(metadata)
    for section, fields in METADATA_REFERENCES.items():
        if section not in data:
            continue
        original = data[section]
        if not isinstance(original, dict):
            data[section] = {}
            continue
        value = dict(original)
        for field, target in fields.items():
            if value.get(field) is None:
                # An offered slot without a saved appointment is parent workflow
                # data, not a read of an existing Appointment record.
                continue
            if field in value and reference_id(value[field]) not in visibility.get((business_id, target), set()):
                value[field] = None
                if section == "auto_booking":
                    value["selected_slot"] = None
                    value["reason"] = ""
        data[section] = value
    return data
