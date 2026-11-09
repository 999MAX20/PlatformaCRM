from decimal import Decimal

from django.utils import timezone
from django.utils.dateparse import parse_datetime
from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from apps.core.custom_fields import validate_custom_field_value
from apps.core.models import CustomFieldDefinition
from apps.scheduling.availability import business_zone
from .schema import FIELDS


class ClientInput(serializers.Serializer):
    full_name = serializers.CharField(max_length=255, required=False, allow_blank=True)
    phone = serializers.CharField(max_length=32, required=False, allow_blank=True)
    email = serializers.EmailField(required=False, allow_blank=True)
    notes = serializers.CharField(max_length=20000, required=False, allow_blank=True)

    def validate(self, attrs):
        if not any(attrs.get(key) for key in ("full_name", "phone", "email")):
            raise ValidationError({"full_name": "Provide a name or contact."})
        return attrs


class ServiceInput(serializers.Serializer):
    name = serializers.CharField(max_length=255)
    description = serializers.CharField(max_length=20000, required=False, allow_blank=True)
    duration_minutes = serializers.IntegerField(min_value=1, max_value=1440)
    price_from = serializers.DecimalField(max_digits=10, decimal_places=2, min_value=Decimal("0"), required=False, allow_null=True)


class SpecialistInput(serializers.Serializer):
    name = serializers.CharField(max_length=255)
    profession = serializers.CharField(max_length=120, required=False, allow_blank=True)
    contact_phone = serializers.CharField(max_length=32, required=False, allow_blank=True)
    public_description = serializers.CharField(max_length=20000, required=False, allow_blank=True)


class AppointmentInput(serializers.Serializer):
    client_ref = serializers.CharField(max_length=255)
    service_ref = serializers.CharField(max_length=255)
    specialist_ref = serializers.CharField(max_length=255)
    start_at = serializers.CharField(max_length=100)
    status = serializers.ChoiceField(choices=["created", "confirmed", "completed", "cancelled", "no_show"], default="created")
    notes = serializers.CharField(max_length=20000, required=False, allow_blank=True)
    reason = serializers.CharField(max_length=2000, required=False, allow_blank=True)


INPUTS = {"clients": ClientInput, "services": ServiceInput, "specialists": SpecialistInput, "appointments": AppointmentInput}


def mapped_values(source, row, business):
    mapped = {field: row.get(header, "").strip() for field, header in source.mapping_json.items()}
    fields = {key: value for key, value in mapped.items() if key in FIELDS[source.entity_type] and key != "external_id"}
    if fields.get("price_from") == "":
        fields["price_from"] = None
    if source.entity_type == "appointments" and fields.get("status") == "":
        fields.pop("status")
    serializer = INPUTS[source.entity_type](data=fields)
    serializer.is_valid(raise_exception=True)
    values = dict(serializer.validated_data)
    if source.entity_type == "appointments":
        try:
            start_at = parse_datetime(values["start_at"])
        except (ValueError, TypeError):
            start_at = None
        if start_at is None:
            raise ValidationError({"start_at": "Use an ISO date and time, including the timezone where possible."})
        if timezone.is_naive(start_at):
            start_at = timezone.make_aware(start_at, business_zone(business))
        values["start_at"] = start_at
    custom = {}
    for field in source.fields_json:
        value = mapped.get("custom." + field["key"], "")
        if field["field_type"] == "boolean" and value:
            normalized = value.lower()
            if normalized not in {"true", "false", "1", "0", "да", "нет", "иә", "жоқ"}:
                raise ValidationError({"custom." + field["key"]: "Choose a boolean value."})
            value = normalized in {"true", "1", "да", "иә"}
        definition = CustomFieldDefinition(field_type=field["field_type"], options_json={"options": field["options"]})
        custom[field["key"]] = validate_custom_field_value(definition=definition, value_json={"value": value})
    external_id = mapped.get("external_id", "")
    if len(external_id) > 255 or external_id.startswith(("crm:", "row:")):
        raise ValidationError({"external_id": "Use a source identifier without a reserved prefix."})
    return values, custom, external_id
