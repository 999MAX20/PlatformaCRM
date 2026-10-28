import uuid

from django.conf import settings
from django.db import models


class YCloudConnection(models.Model):
    channel = models.OneToOneField("bots.BotChannel", on_delete=models.CASCADE, related_name="ycloud_connection")
    customer_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    initiated_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    setup_revision = models.CharField(max_length=64)
    status = models.CharField(max_length=32, default="pending")
    expires_at = models.DateTimeField()
    waba_id = models.CharField(max_length=255, blank=True)
    phone_id = models.CharField(max_length=255, blank=True)
    phone_number = models.CharField(max_length=32, blank=True)
    last_error = models.CharField(max_length=64, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["waba_id"], condition=~models.Q(waba_id=""), name="unique_ycloud_waba"),
            models.UniqueConstraint(fields=["phone_id"], condition=~models.Q(phone_id=""), name="unique_ycloud_phone"),
            models.UniqueConstraint(fields=["phone_number"], condition=~models.Q(phone_number=""), name="unique_ycloud_number"),
        ]


class YCloudEvent(models.Model):
    connection = models.ForeignKey(YCloudConnection, on_delete=models.CASCADE, related_name="events")
    external_id = models.CharField(max_length=255, unique=True)
    kind = models.CharField(max_length=80)
    payload = models.JSONField()
    status = models.CharField(max_length=20, default="pending")
    attempts = models.PositiveIntegerField(default=0)
    next_attempt_at = models.DateTimeField()
    error_code = models.CharField(max_length=64, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [models.Index(fields=["status", "next_attempt_at"], name="ycloud_event_due")]


class YCloudDispatch(models.Model):
    """An irreversible HTTP attempt. Unknown outcomes must never be resent blindly."""
    message = models.ForeignKey("bots.BotMessage", on_delete=models.CASCADE, related_name="ycloud_dispatches")
    connection = models.ForeignKey(YCloudConnection, on_delete=models.PROTECT)
    correlation_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    provider_id = models.CharField(max_length=255, blank=True)
    wamid = models.CharField(max_length=255, blank=True)
    state = models.CharField(max_length=24, default="submitting")
    error_code = models.CharField(max_length=64, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["provider_id"], condition=~models.Q(provider_id=""), name="unique_ycloud_dispatch_id")]
