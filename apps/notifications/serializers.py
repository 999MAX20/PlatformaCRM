from rest_framework import serializers
from apps.core.client_projection import ClientProjectionMixin

from apps.notifications.models import Notification, NotificationPreference, NotificationRecipient
from apps.notifications.personal_selectors import notification_subject
from apps.notifications.service_messages import service_message_key
from apps.notifications.module_sources import source_projection


class NotificationSerializer(ClientProjectionMixin, serializers.ModelSerializer):
    client_private_copies = ("text", "last_error", "provider_reference")
    client_name = serializers.CharField(source="client.full_name", read_only=True)
    recipient_email = serializers.EmailField(source="recipient.email", read_only=True)
    recipient_name = serializers.CharField(source="recipient.full_name", read_only=True)
    is_read = serializers.BooleanField(read_only=True)
    protected_state_fields = {"status", "read_at", "opened_at", "acknowledged_at", "kind", "author", "revoked_at", "publication_key", "audience_fixed_at"}

    class Meta:
        model = Notification
        fields = [
            "id",
            "business",
            "recipient",
            "recipient_email",
            "recipient_name",
            "client",
            "client_name",
            "appointment",
            "channel",
            "category",
            "priority",
            "text",
            "send_at",
            "status",
            "action_url",
            "action_label",
            "read_at",
            "is_read",
            "attempts",
            "max_attempts",
            "next_retry_at",
            "last_attempt_at",
            "delivered_at",
            "failed_at",
            "last_error",
            "provider_reference",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "status", "read_at", "is_read", "attempts", "max_attempts", "next_retry_at",
            "last_attempt_at", "delivered_at", "failed_at", "last_error", "provider_reference",
            "created_at", "updated_at",
        ]

    def validate(self, attrs):
        attempted_state_fields = sorted(self.protected_state_fields.intersection((self.initial_data or {}).keys()))
        if attempted_state_fields:
            raise serializers.ValidationError(
                {
                    "detail": "Use notification action endpoints for delivery/read state changes.",
                    "fields": attempted_state_fields,
                }
            )
        channel = attrs.get("channel") or getattr(self.instance, "channel", Notification.Channels.SYSTEM)
        if channel == Notification.Channels.SYSTEM or (self.instance and self.instance.channel == Notification.Channels.SYSTEM):
            raise serializers.ValidationError("Publish internal announcements through the announcement action; work events are server-owned.")
        business = attrs.get("business") or getattr(self.instance, "business", None)
        client = attrs.get("client") or getattr(self.instance, "client", None)
        appointment = attrs.get("appointment") or getattr(self.instance, "appointment", None)
        recipient = attrs.get("recipient") or getattr(self.instance, "recipient", None)
        if client and business and client.business_id != business.id:
            raise serializers.ValidationError("Client must belong to the selected business.")
        if appointment and business and appointment.business_id != business.id:
            raise serializers.ValidationError("Appointment must belong to the selected business.")
        if recipient and business and not business.members.filter(user=recipient, is_active=True).exists():
            raise serializers.ValidationError("Recipient must be an active member of the selected business.")
        return attrs

    def to_representation(self, instance):
        data = super().to_representation(instance)
        if instance.channel != Notification.Channels.SYSTEM or not self.context.get("personal_feed"):
            return data
        actor = getattr(self.context.get("request"), "user", None)
        state = self.context.get("recipient_state")
        if state is None and not hasattr(instance, "personal_read_at"):
            state = NotificationRecipient.objects.filter(notification=instance, user=actor).first()
            if state is None:
                return {"id": None, "read_restricted": True}
        date = serializers.DateTimeField()
        for field in ("read_at", "opened_at", "acknowledged_at"):
            value = getattr(state, field) if state else getattr(instance, "personal_" + field)
            data[field] = date.to_representation(value) if value else None
        data["is_read"] = data["read_at"] is not None
        data["kind"] = instance.kind
        data["author_name"] = instance.author.full_name if instance.author_id else ""
        # Stored work text/labels may contain fields whose rights changed later.
        # The personal feed identifies the accessible source without replaying a
        # private historical snapshot. Full detail remains in its authorized UI.
        subject = notification_subject(instance.action_url)
        data["message_key"] = "" if instance.kind == Notification.Kinds.ANNOUNCEMENT else "notification.work." + (subject[0] if subject else "notifications")
        safe_service_key = service_message_key(instance, self.context)
        if safe_service_key:
            data["message_key"] = safe_service_key
        if instance.kind != Notification.Kinds.ANNOUNCEMENT:
            data["text"] = ""
        data["action_url"] = subject[2] if subject and instance.kind != Notification.Kinds.ANNOUNCEMENT else ""
        data["action_label"] = ""
        data["last_error"] = ""
        data["provider_reference"] = ""
        projection = source_projection(instance)
        if projection is not None and instance.kind != Notification.Kinds.ANNOUNCEMENT:
            data.update(projection)
        return data


class NotificationPreferenceSerializer(serializers.ModelSerializer):
    user_email = serializers.EmailField(source="user.email", read_only=True)
    user_name = serializers.CharField(source="user.full_name", read_only=True)

    class Meta:
        model = NotificationPreference
        fields = [
            "id",
            "business",
            "user",
            "user_email",
            "user_name",
            "category",
            "in_app_enabled",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["created_at", "updated_at"]

    def validate(self, attrs):
        business = attrs.get("business") or getattr(self.instance, "business", None)
        user = attrs.get("user") or getattr(self.instance, "user", None)
        if user and business and not business.members.filter(user=user, is_active=True).exists() and business.owner_id != user.id:
            raise serializers.ValidationError("User must be an active member of the selected business.")
        return attrs
