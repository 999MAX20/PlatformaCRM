from copy import deepcopy

from rest_framework.exceptions import APIException

from apps.businesses.access import Actions, Resources, assert_can, can_view_sensitive_field
from apps.core.custom_fields import custom_field_role_allowed
from apps.core.models import CustomFieldDefinition
from .entities import RESOURCES, accessible_entity


def visible_report(workspace, report, actor):
    if not report:
        return report
    try:
        for source in workspace.sources.all():
            assert_can(actor, workspace.business, RESOURCES[source.entity_type], Actions.VIEW)
            for field in source.fields_json:
                definition = CustomFieldDefinition.objects.filter(business=workspace.business,
                    entity_type={"clients": "client", "services": "service", "specialists": "specialist", "appointments": "appointment"}[source.entity_type],
                    key=field["key"]).first()
                if definition and not custom_field_role_allowed(definition, actor, "view"):
                    return {"ready": False, "access_changed": True}
        for row in [*report.get("rows", []), *report.get("errors", [])]:
            if row.get("id"):
                obj = accessible_entity(business=workspace.business, actor=actor, entity_type=row["entity_type"], pk=row["id"])
                if row["entity_type"] == "appointments":
                    assert_can(actor, workspace.business, Resources.CLIENTS, Actions.VIEW, obj=obj.client)
            for key, kind in (("client_ref", "clients"), ("service_ref", "services"), ("specialist_ref", "specialists")):
                reference = row.get("values", {}).get(key, "")
                if isinstance(reference, str) and reference.startswith("crm:") and reference[4:].isdigit():
                    accessible_entity(business=workspace.business, actor=actor, entity_type=kind, pk=int(reference[4:]))
    except APIException:
        return {"ready": False, "access_changed": True}
    result = deepcopy(report)
    if not can_view_sensitive_field(actor, workspace.business, Resources.CLIENTS, "notes"):
        for row in [*result.get("rows", []), *result.get("errors", [])]:
            if row["entity_type"] == "clients":
                row.get("values", {}).pop("notes", None)
                row.get("before", {}).pop("notes", None)
    return result
