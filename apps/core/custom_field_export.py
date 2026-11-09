from apps.businesses.access import Actions, Resources, can
from apps.core.custom_fields import custom_field_role_allowed
from apps.core.models import CustomFieldDefinition, CustomFieldValue


def export_custom_fields(business, entity_type, actor):
    if not actor or not can(actor, business, Resources.SETTINGS, Actions.VIEW).allowed:
        return []
    return [field for field in CustomFieldDefinition.objects.filter(business=business,
        entity_type=entity_type, is_active=True).order_by("sort_order", "pk")
        if custom_field_role_allowed(field, actor, "view")]


def export_custom_values(definitions, queryset):
    from django.db.models import CharField, F, Subquery
    from django.db.models.functions import Cast
    ids = queryset.order_by().annotate(entity_id_text=Cast("pk", CharField())).values("entity_id_text")
    return {(value.entity_id, value.definition_id): value.value_json.get("value", "")
        for value in CustomFieldValue.objects.filter(definition__in=definitions, business_id=F("definition__business_id"), entity_type=F("definition__entity_type"), entity_id__in=Subquery(ids)).iterator(chunk_size=1000)}
