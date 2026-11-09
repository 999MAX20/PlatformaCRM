import json

from django.db.models import CharField, DecimalField, Func, Subquery
from django.db.models.functions import Cast
from django.db.models.fields.json import KeyTextTransform
from rest_framework import serializers
from rest_framework.exceptions import PermissionDenied, ValidationError

from apps.core.custom_fields import custom_field_role_allowed, validate_custom_field_value
from apps.core.models import CustomFieldDefinition, CustomFieldValue
from apps.core.permissions import user_can_access_business
from apps.businesses.access import Actions, Resources, assert_can


def filter_custom_field(queryset, *, actor, entity_type, params):
    reference = params.get("custom_field")
    if not reference:
        return queryset
    pk = serializers.IntegerField(min_value=1).run_validation(reference)
    field = CustomFieldDefinition.objects.select_related("business").filter(pk=pk, entity_type=entity_type, is_active=True).first()
    if not field or not user_can_access_business(actor, field.business) or not custom_field_role_allowed(field, actor, "view"):
        raise PermissionDenied("This custom field is not available.")
    assert_can(actor, field.business, Resources.SETTINGS, Actions.VIEW)
    display = (field.options_json or {}).get("display", {})
    if not isinstance(display, dict) or display.get("in_filters") is not True:
        raise ValidationError({"custom_field": "Filtering is not enabled for this field."})
    operation = serializers.ChoiceField(choices=["equals", "contains", "gte", "lte", "is_empty"]).run_validation(params.get("custom_operator", "equals"))
    values = CustomFieldValue.objects.filter(business=field.business, definition=field, entity_type=entity_type)
    if operation == "is_empty":
        values = values.exclude(value_json__value__isnull=True).exclude(value_json__value__in=["", None, []])
    else:
        raw = serializers.CharField(max_length=20000, allow_blank=True).run_validation(params.get("custom_value", ""))
        if operation in {"gte", "lte"} and not raw:
            raise ValidationError({"custom_value": "A comparison value is required."})
        if field.field_type == "multiselect":
            try:
                raw = json.loads(raw) if raw.startswith("[") else [raw]
            except (TypeError, ValueError):
                raise ValidationError({"custom_value": "Value must be a list of string options."})
            if not isinstance(raw, list):
                raise ValidationError({"custom_value": "Value must be a list of string options."})
        if field.field_type == "boolean":
            raw = serializers.BooleanField().run_validation(raw)
        normalized = validate_custom_field_value(definition=field, value_json={"value": raw})["value"]
        if operation == "contains":
            if field.field_type not in {"text", "textarea", "phone", "email", "url"}:
                raise ValidationError({"custom_operator": "Contains requires a text field."})
            values = values.filter(value_json__value__icontains=normalized)
        elif operation in {"gte", "lte"}:
            if field.field_type in {"number", "money"}:
                values = values.exclude(value_json__value__in=["", None]).annotate(comparable=Func(KeyTextTransform("value", "value_json"), template="CAST(%(expressions)s AS NUMERIC)", output_field=DecimalField()))
                values = values.filter(**{f"comparable__{operation}": normalized})
            elif field.field_type == "date":
                values = values.filter(**{f"value_json__value__{operation}": normalized})
            else:
                raise ValidationError({"custom_operator": "Ordering requires a number or date field."})
        else:
            if field.field_type in {"number", "money"} and normalized not in (None, ""):
                values = values.exclude(value_json__value__in=["", None]).annotate(comparable=Func(KeyTextTransform("value", "value_json"), template="CAST(%(expressions)s AS NUMERIC)", output_field=DecimalField())).filter(comparable=normalized)
            else:
                values = values.filter(value_json__value=normalized)
    queryset = queryset.filter(business=field.business).alias(custom_entity_id=Cast("pk", CharField()))
    match = {"custom_entity_id__in": Subquery(values.order_by().values("entity_id"))}
    return queryset.exclude(**match) if operation == "is_empty" else queryset.filter(**match)
