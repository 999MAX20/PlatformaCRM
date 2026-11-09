import re

from django.db import transaction
from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from apps.core.models import CustomFieldDefinition, ImportWorkspaceSource
from apps.core.custom_fields import assert_custom_field_editable
from .drafts import invalidate_preview, lock_workspace


ENTITY_NAMES = {"clients": "client", "services": "service", "specialists": "specialist", "appointments": "appointment"}
FIELDS = {
    "clients": ["external_id", "full_name", "phone", "email", "notes"],
    "services": ["external_id", "name", "description", "duration_minutes", "price_from"],
    "specialists": ["external_id", "name", "profession", "contact_phone", "public_description"],
    "appointments": ["external_id", "client_ref", "service_ref", "specialist_ref", "start_at", "status", "notes", "reason"],
}


class DraftFieldSerializer(serializers.Serializer):
    key = serializers.RegexField(r"^[a-z][a-z0-9_]{0,63}$")
    label = serializers.CharField(max_length=128)
    field_type = serializers.ChoiceField(choices=["text", "number", "date", "boolean", "select"])
    options = serializers.ListField(child=serializers.CharField(max_length=128), max_length=100, default=list)
    definition_id = serializers.IntegerField(min_value=1, required=False)
    in_card = serializers.BooleanField(default=True)
    in_table = serializers.BooleanField(default=True)
    in_filters = serializers.BooleanField(default=False)
    in_calendar = serializers.BooleanField(default=False)

    def validate(self, attrs):
        if len(set(attrs["options"])) != len(attrs["options"]):
            raise ValidationError({"options": "Options must be unique."})
        if attrs["field_type"] == "select" and not attrs["options"]:
            raise ValidationError({"options": "Provide at least one option."})
        return attrs


def validate_fields(fields, *, business, actor, entity_type):
    if not isinstance(fields, list) or len(fields) > 40:
        raise ValidationError({"fields": "At most 40 additional fields are supported."})
    serializer = DraftFieldSerializer(data=fields, many=True)
    serializer.is_valid(raise_exception=True)
    fields = list(serializer.validated_data)
    if len({field["key"] for field in fields}) != len(fields):
        raise ValidationError({"fields": "Field keys must be unique."})
    for field in fields:
        existing = CustomFieldDefinition.objects.filter(business=business,
            entity_type=ENTITY_NAMES[entity_type], key=field["key"]).first()
        if field.get("definition_id"):
            if not existing or existing.pk != field["definition_id"]:
                raise ValidationError({"fields": "The selected field is not available."})
            assert_custom_field_editable(existing, actor)
            if existing.field_type != field["field_type"]:
                raise ValidationError({"fields": "An existing field cannot change type during import."})
            options = (existing.options_json or {}).get("options", [])
            field["options"] = [item.get("value", item.get("key", item.get("label"))) if isinstance(item, dict) else item for item in options]
            field["label"] = existing.label
            display = (existing.options_json or {}).get("display", {})
            if not isinstance(display, dict):
                display = {}
            for key in ("in_card", "in_table", "in_filters", "in_calendar"):
                field[key] = bool(display.get(key, key == "in_card"))
        elif existing:
            raise ValidationError({"fields": "Select the existing field instead of creating the same key."})
    return fields


@transaction.atomic
def configure_source(*, workspace_id, source_id, actor, version, entity_type, mapping, fields, columns, resolutions):
    workspace = lock_workspace(workspace_id, actor, version)
    source = workspace.sources.filter(pk=source_id).first()
    if source is None:
        raise ValidationError("Source is not available in this draft.")
    if entity_type not in ImportWorkspaceSource.Entities.values:
        raise ValidationError({"entity_type": "Unsupported import entity."})
    fields = validate_fields(fields, business=workspace.business, actor=actor, entity_type=entity_type)
    allowed = set(FIELDS[entity_type]) | {"custom." + field["key"] for field in fields}
    if not isinstance(mapping, dict) or set(mapping) - allowed:
        raise ValidationError({"mapping": "Map supported fields only."})
    if any(not isinstance(header, str) or header not in source.rows_json[0] for header in mapping.values()):
        raise ValidationError({"mapping": "Source column is not available."})
    if not isinstance(columns, list) or any(not isinstance(key, str) or key not in allowed for key in columns) or len(set(columns)) != len(columns):
        raise ValidationError({"columns": "Select unique supported columns."})
    if not isinstance(resolutions, dict) or len(resolutions) > len(source.rows_json):
        raise ValidationError({"resolutions": "Invalid row decisions."})
    for number, decision in resolutions.items():
        if not isinstance(number, str) or not re.fullmatch(r"[1-9][0-9]*", number) or int(number) > len(source.rows_json):
            raise ValidationError({"resolutions": "Invalid row number."})
        if not isinstance(decision, dict) or set(decision) - {"action", "target_id", "update_fields"}:
            raise ValidationError({"resolutions": "Invalid row decision."})
        if decision.get("action") not in {"create", "fill", "update", "skip"}:
            raise ValidationError({"resolutions": "Choose a supported duplicate decision."})
        if "target_id" in decision and (type(decision["target_id"]) is not int or decision["target_id"] < 1):
            raise ValidationError({"resolutions": "Invalid target record."})
        selected = decision.get("update_fields", [])
        if not isinstance(selected, list) or any(not isinstance(key, str) or key not in allowed - {"external_id"} for key in selected):
            raise ValidationError({"resolutions": "Select supported fields to update."})
    if source.entity_type != entity_type:
        source.profile = None
    source.entity_type = entity_type
    source.mapping_json = mapping
    source.fields_json = fields
    source.columns_json = columns
    source.resolutions_json = resolutions
    source.save(update_fields=["profile", "entity_type", "mapping_json", "fields_json", "columns_json", "resolutions_json"])
    invalidate_preview(workspace)
    return workspace, source
