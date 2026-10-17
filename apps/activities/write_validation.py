"""Validate caller-supplied history links; internal event producers stay separate."""
from django.apps import apps
from rest_framework.exceptions import ValidationError

from apps.businesses.access import Actions, assert_can
from apps.businesses.capabilities import assert_resource_enabled


CLIENT_LINK_ERROR = "Client is not available in this business."


ENTITY_TARGETS = {
    "client": ("clients.Client", "clients"),
    "lead": ("leads.Lead", "leads"),
    "deal": ("crm.Deal", "deals"),
    "appointment": ("scheduling.Appointment", "appointments"),
    "task": ("tasks.Task", "tasks"),
    "conversation": ("conversations.Conversation", "conversations"),
    "botconversation": ("bots.BotConversation", "conversations"),
    "bot_conversation": ("bots.BotConversation", "conversations"),
    "message": ("conversations.Message", "conversations"),
    "botmessage": ("bots.BotMessage", "conversations"),
    "bot_message": ("bots.BotMessage", "conversations"),
    "payment": ("payments.Payment", "payments"),
}


def validate_history_links(*, business, client, entity_type, entity_id, actor):
    def check_access(entity, resource):
        assert_resource_enabled(business, resource)
        assert_can(actor, business, resource, Actions.VIEW, obj=entity)
        assert_can(actor, business, resource, Actions.UPDATE, obj=entity)

    if client is not None:
        if client.business_id != business.pk:
            raise ValidationError({"client": [CLIENT_LINK_ERROR]})
        check_access(client, "clients")
    if not entity_type and not entity_id:
        return
    target = ENTITY_TARGETS.get((entity_type or "").lower())
    if not target or not entity_id:
        raise ValidationError({"entity_type": "Select a supported CRM entity and its identifier."})
    model_name, resource = target
    model = apps.get_model(model_name)
    parent_link = model_name in {"conversations.Message", "bots.BotMessage"}
    lookup = "conversation__business" if parent_link else "business"
    try:
        entity = model.objects.filter(**{lookup: business, "pk": entity_id}).first()
    except (ValueError, TypeError, OverflowError):
        entity = None
    if entity is None:
        raise ValidationError({"entity_id": "Entity is not available in this business."})
    check_access(entity.conversation if parent_link else entity, resource)
    return entity


class HistoryWriteValidationMixin:
    attribution_field = None

    def validate(self, attrs):
        attrs = super().validate(attrs)
        actor = self.context["request"].user
        # Relinking must not turn a forbidden existing record into an allowed one.
        if self.instance is not None:
            validate_history_links(
                business=self.instance.business, client=self.instance.client,
                entity_type=self.instance.entity_type, entity_id=self.instance.entity_id,
                actor=actor,
            )
        values = {key: attrs.get(key, getattr(self.instance, key, None))
                  for key in ("business", "client", "entity_type", "entity_id")}
        entity = validate_history_links(**values, actor=actor)
        if entity is not None and ("entity_type" in attrs or "entity_id" in attrs):
            # Store the same identity that was authorized, including aliases/IDs
            # accepted by Django, so history lookups cannot diverge from validation.
            attrs["entity_type"] = entity.__class__.__name__
            attrs["entity_id"] = str(entity.pk)
        return attrs

    def create(self, validated_data):
        validated_data[self.attribution_field] = self.context["request"].user
        return super().create(validated_data)
