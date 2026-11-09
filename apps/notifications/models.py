from django.conf import settings
from django.db import models, transaction
from django.utils import timezone

from apps.businesses.models import Business, TimeStampedModel
from apps.core.sanitization import SanitizedErrorFieldsMixin
from apps.clients.models import Client
from apps.scheduling.models import Appointment


class NotificationQuerySet(models.QuerySet):
    def bulk_create(self, objs, **kwargs):
        from apps.notifications.recipients import create_recipient_states

        if kwargs.get("ignore_conflicts") or kwargs.get("update_conflicts"):
            raise ValueError("Notification bulk conflicts require an explicit idempotent producer.")
        with transaction.atomic(using=self.db):
            rows = super().bulk_create(objs, **kwargs)
            create_recipient_states(rows, using=self.db)
            return rows


class Notification(SanitizedErrorFieldsMixin, TimeStampedModel):
    sanitized_text_fields = ("last_error",)
    class Channels(models.TextChoices):
        TELEGRAM = "telegram", "Telegram"
        WHATSAPP = "whatsapp", "WhatsApp"
        EMAIL = "email", "Email"
        SMS = "sms", "SMS"
        SYSTEM = "system", "System"

    class Statuses(models.TextChoices):
        PENDING = "pending", "Pending"
        SENDING = "sending", "Sending"
        RETRY_SCHEDULED = "retry_scheduled", "Retry scheduled"
        SENT = "sent", "Sent"
        FAILED = "failed", "Failed"
        CANCELLED = "cancelled", "Cancelled"

    class Categories(models.TextChoices):
        SALES = "sales", "Sales"
        FINANCE = "finance", "Finance"
        SYSTEM = "system", "System"
        AI_ALERTS = "ai_alerts", "AI alerts"
        OUTREACH = "outreach", "Outreach"
        TASKS = "tasks", "Tasks"

    class Priorities(models.TextChoices):
        LOW = "low", "Low"
        NORMAL = "normal", "Normal"
        HIGH = "high", "High"
        URGENT = "urgent", "Urgent"

    class Kinds(models.TextChoices):
        WORK = "work", "Work"
        ANNOUNCEMENT = "announcement", "Announcement"

    objects = NotificationQuerySet.as_manager()

    business = models.ForeignKey(Business, on_delete=models.CASCADE, related_name="notifications")
    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="notifications",
        help_text="Empty recipient means a business-wide notification.",
    )
    client = models.ForeignKey(Client, on_delete=models.PROTECT, null=True, blank=True, related_name="notifications")
    appointment = models.ForeignKey(Appointment, on_delete=models.CASCADE, null=True, blank=True, related_name="notifications")
    channel = models.CharField(max_length=32, choices=Channels.choices, default=Channels.SYSTEM)
    category = models.CharField(max_length=32, choices=Categories.choices, default=Categories.SYSTEM)
    priority = models.CharField(max_length=32, choices=Priorities.choices, default=Priorities.NORMAL)
    text = models.TextField()
    send_at = models.DateTimeField()
    status = models.CharField(max_length=32, choices=Statuses.choices, default=Statuses.PENDING)
    action_url = models.CharField(max_length=255, blank=True)
    action_label = models.CharField(max_length=64, blank=True)
    read_at = models.DateTimeField(null=True, blank=True)
    kind = models.CharField(max_length=24, choices=Kinds.choices, default=Kinds.WORK)
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
                               related_name="authored_notifications")
    revoked_at = models.DateTimeField(null=True, blank=True)
    publication_key = models.UUIDField(null=True, blank=True, editable=False)
    audience_fixed_at = models.DateTimeField(null=True, blank=True, editable=False)
    attempts = models.PositiveSmallIntegerField(default=0)
    max_attempts = models.PositiveSmallIntegerField(default=3)
    next_retry_at = models.DateTimeField(null=True, blank=True)
    locked_at = models.DateTimeField(null=True, blank=True)
    last_attempt_at = models.DateTimeField(null=True, blank=True)
    delivered_at = models.DateTimeField(null=True, blank=True)
    failed_at = models.DateTimeField(null=True, blank=True)
    last_error = models.TextField(blank=True)
    provider_reference = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ["read_at", "-send_at"]
        constraints = [
            models.UniqueConstraint(fields=["business", "publication_key"], name="unique_notification_publication"),
        ]
        indexes = [
            models.Index(fields=["business", "status", "read_at", "send_at"]),
            models.Index(fields=["business", "category", "priority"]),
            models.Index(fields=["business", "recipient", "read_at"]),
            models.Index(fields=["status", "send_at", "next_retry_at"]),
        ]

    def __str__(self):
        return f"{self.channel} notification for {self.client or self.business}"

    def save(self, *args, **kwargs):
        from apps.notifications.recipients import create_recipient_states

        adding = self._state.adding
        using = kwargs.get("using") or self._state.db or "default"
        with transaction.atomic(using=using):
            super().save(*args, **kwargs)
            if adding:
                create_recipient_states([self], using=using)

    @property
    def is_read(self):
        return self.read_at is not None

    def mark_read(self):
        if self.read_at is None:
            self.read_at = timezone.now()
            self.save(update_fields=["read_at", "updated_at"])

    def mark_unread(self):
        if self.read_at is not None:
            self.read_at = None
            self.save(update_fields=["read_at", "updated_at"])


class NotificationRecipient(models.Model):
    """Fixed audience and private state; Business is derived through notification."""

    notification = models.ForeignKey(Notification, on_delete=models.CASCADE, related_name="recipient_states")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="notification_states")
    received_at = models.DateTimeField(default=timezone.now, editable=False)
    opened_at = models.DateTimeField(null=True, blank=True)
    read_at = models.DateTimeField(null=True, blank=True)
    acknowledged_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["notification", "user"], name="unique_notification_recipient"),
        ]
        indexes = [models.Index(fields=["user", "read_at", "received_at"], name="notif_recipient_unread_idx")]


class NotificationPreference(TimeStampedModel):
    business = models.ForeignKey(Business, on_delete=models.CASCADE, related_name="notification_preferences")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="notification_preferences")
    category = models.CharField(max_length=32, choices=Notification.Categories.choices)
    in_app_enabled = models.BooleanField(default=True)

    class Meta:
        ordering = ["category"]
        constraints = [
            models.UniqueConstraint(fields=["business", "user", "category"], name="unique_notification_preference_per_user_category"),
        ]
        indexes = [
            models.Index(fields=["business", "user", "category"]),
        ]

    def __str__(self):
        return f"{self.user} {self.category} notifications for {self.business}"
