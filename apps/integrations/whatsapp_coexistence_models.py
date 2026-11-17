from django.db import models


class WhatsAppCoexistenceSync(models.Model):
    channel = models.ForeignKey("bots.BotChannel", on_delete=models.CASCADE, related_name="coexistence_syncs")
    setup_revision = models.CharField(max_length=64)
    phone_number_id = models.CharField(max_length=255)
    waba_id = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)
    state = models.CharField(max_length=32, default="pending")
    contacts_request_id = models.CharField(max_length=255, blank=True)
    history_request_id = models.CharField(max_length=255, blank=True)
    requesting = models.CharField(max_length=32, blank=True)
    progress = models.PositiveSmallIntegerField(default=0)
    error_code = models.CharField(max_length=64, blank=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["channel", "setup_revision"], name="unique_wa_coexistence_revision")]


class WhatsAppCoexistenceEvent(models.Model):
    sync = models.ForeignKey(WhatsAppCoexistenceSync, on_delete=models.CASCADE, related_name="events")
    digest = models.CharField(max_length=64)
    field = models.CharField(max_length=32)
    payload = models.JSONField(default=dict)
    status = models.CharField(max_length=32, default="received")
    created_at = models.DateTimeField(auto_now_add=True)
    processed_at = models.DateTimeField(null=True)
    error_code = models.CharField(max_length=64, blank=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["sync", "digest"], name="unique_wa_coexistence_event")]
        indexes = [models.Index(fields=["status", "created_at"], name="wa_coexist_event_due")]
