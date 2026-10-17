"""Authenticated intake may add incoming text, never rewrite delivery history."""
from django.db import transaction
from rest_framework import serializers
from rest_framework.exceptions import PermissionDenied

from apps.businesses.access import Actions, Resources, assert_can
from apps.businesses.models import Business


class InboundMessageSerializerMixin:
    # Explicitly reject unknown delivery keys too, rather than silently accepting
    # a request that appears to have changed provider state.
    input_fields = {"conversation", "text", "sender_type"}

    def assert_parent_access(self, conversation):
        actor = getattr(self.context.get("request"), "user", None)
        if actor is None:
            raise PermissionDenied("A user is required for message intake.")
        for action in (Actions.VIEW, Actions.UPDATE):
            assert_can(actor, conversation.business, Resources.CONVERSATIONS, action, obj=conversation)

    def validate(self, attrs):
        attrs = super().validate(attrs)
        if self.instance is not None:
            raise serializers.ValidationError("Message history cannot be edited. Use Inbox send/retry actions.")
        forbidden = sorted(set(self.initial_data or {}) - self.input_fields)
        if forbidden:
            raise serializers.ValidationError({field: "This message field is managed by the server." for field in forbidden})
        if attrs.get("sender_type", "client") != "client":
            raise serializers.ValidationError({"sender_type": "Use Inbox to send a staff reply."})
        self.assert_parent_access(attrs["conversation"])
        attrs["sender_type"] = "client"
        return attrs

    @transaction.atomic
    def create(self, validated_data):
        original = validated_data["conversation"]
        Business.objects.select_for_update().get(pk=original.business_id)
        conversation = original.__class__.objects.select_for_update().get(pk=original.pk)
        self.assert_parent_access(conversation)
        return super().create({**validated_data, "conversation": conversation})
