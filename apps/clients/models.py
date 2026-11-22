from django.conf import settings
from django.db import models, transaction

from apps.businesses.models import Business, TimeStampedModel
from apps.clients.identity import normalize_client_identity


class Client(TimeStampedModel):
    class Sources(models.TextChoices):
        WEBSITE = "website", "Website"
        TELEGRAM = "telegram", "Telegram"
        WHATSAPP = "whatsapp", "WhatsApp"
        INSTAGRAM = "instagram", "Instagram"
        MANUAL = "manual", "Manual"
        PARSER = "parser", "Parser"
        OTHER = "other", "Other"

    business = models.ForeignKey(Business, on_delete=models.CASCADE, related_name="clients")
    full_name = models.CharField(max_length=255)
    phone = models.CharField(max_length=32, blank=True)
    email = models.EmailField(blank=True)
    normalized_phone = models.CharField(max_length=32, blank=True, editable=False)
    normalized_email = models.EmailField(blank=True, editable=False)
    whatsapp_id = models.CharField(max_length=128, blank=True)
    telegram_id = models.CharField(max_length=128, blank=True)
    instagram_id = models.CharField(max_length=128, blank=True)
    source = models.CharField(max_length=32, choices=Sources.choices, default=Sources.MANUAL)
    source_detail = models.CharField(max_length=255, blank=True)
    source_context_json = models.JSONField(default=dict, blank=True)
    notes = models.TextField(blank=True)
    is_archived = models.BooleanField(default=False)
    archived_at = models.DateTimeField(null=True, blank=True)
    archived_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="archived_clients",
    )
    archive_reason = models.TextField(blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["business", "phone"]),
            models.Index(fields=["business", "normalized_phone"]),
            models.Index(fields=["business", "normalized_email"]),
            models.Index(fields=["business", "is_archived", "created_at"]),
        ]

    def save(self, *args, **kwargs):
        identity = normalize_client_identity(phone=self.phone, email=self.email)
        self.normalized_phone = identity["normalized_phone"]
        self.normalized_email = identity["normalized_email"]
        if update_fields := kwargs.get("update_fields"):
            update_fields = set(update_fields)
            if "phone" in update_fields:
                update_fields.add("normalized_phone")
            if "email" in update_fields:
                update_fields.add("normalized_email")
            kwargs["update_fields"] = update_fields
        fields = kwargs.get("update_fields")
        if self.pk and (fields is None or {"full_name", "business", "business_id"} & set(fields)):
            from apps.medical.client_guards import assert_client_identity_write_allowed

            with transaction.atomic(using=kwargs.get("using") or self._state.db):
                current = type(self).objects.using(kwargs.get("using") or self._state.db).select_for_update().filter(pk=self.pk).first()
                changes = {}
                if fields is None or "full_name" in fields:
                    changes["full_name"] = self.full_name
                if fields is None or {"business", "business_id"} & set(fields):
                    changes["business_id"] = self.business_id
                if current is not None:
                    assert_client_identity_write_allowed(current, changes)
                    if fields is not None and changes.get("full_name", current.full_name) != current.full_name:
                        kwargs["update_fields"] = {*fields, "updated_at"}
                super().save(*args, **kwargs)
        else:
            super().save(*args, **kwargs)

    def __str__(self):
        return self.full_name


class ClientMergeLog(models.Model):
    business = models.ForeignKey(Business, on_delete=models.CASCADE, related_name="client_merge_logs")
    target_client = models.ForeignKey(Client, on_delete=models.CASCADE, related_name="merge_logs_as_target")
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="client_merge_logs")
    duplicate_snapshot = models.JSONField(default=dict)
    transferred_counts = models.JSONField(default=dict)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["business", "target_client", "created_at"]),
            models.Index(fields=["business", "created_at"]),
        ]

    def __str__(self):
        duplicate_id = self.duplicate_snapshot.get("id", "unknown")
        return f"Client merge {duplicate_id} -> {self.target_client_id}"
