import uuid

from django.conf import settings
from django.db import models


class GoogleConnection(models.Model):
    business = models.ForeignKey("businesses.Business", on_delete=models.CASCADE)
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    provider = models.CharField(max_length=32, default="google_sheets")
    subject = models.CharField(max_length=255, blank=True)
    disconnected_at = models.DateTimeField(null=True, blank=True)
    email = models.EmailField(blank=True)
    encrypted_refresh = models.TextField(blank=True)
    encrypted_access = models.TextField(blank=True)
    access_expires_at = models.DateTimeField(null=True)
    scopes = models.JSONField(default=list)
    revision = models.UUIDField(default=uuid.uuid4)
    status = models.CharField(max_length=32, default="disconnected")
    last_sync_at = models.DateTimeField(null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["business", "actor", "provider"], name="unique_google_actor_provider")]
        indexes = [models.Index(fields=["status", "disconnected_at"], name="google_retention_due_idx")]


class GoogleOAuthAttempt(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    connection = models.ForeignKey(GoogleConnection, on_delete=models.CASCADE)
    revision = models.UUIDField()
    encrypted_verifier = models.TextField()
    redirect_uri = models.URLField()
    created_at = models.DateTimeField(auto_now_add=True)
    consumed_at = models.DateTimeField(null=True)

    class Meta:
        indexes = [models.Index(fields=["created_at"], name="google_attempt_age_idx")]


class GoogleSheetTransfer(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    connection = models.ForeignKey(GoogleConnection, on_delete=models.CASCADE)
    request_key = models.UUIDField()
    kind = models.CharField(max_length=16)
    spreadsheet_id = models.CharField(max_length=255, blank=True)
    sheet_id = models.PositiveIntegerField(default=0)
    import_job = models.ForeignKey("core.ImportJob", null=True, on_delete=models.SET_NULL)
    status = models.CharField(max_length=32, default="pending")
    row_count = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["connection", "request_key"], name="unique_google_transfer_request")]


class GoogleRetentionFile(models.Model):
    business = models.ForeignKey("businesses.Business", on_delete=models.PROTECT)
    storage_name = models.CharField(max_length=1024, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    attempts = models.PositiveIntegerField(default=0)
    error_code = models.CharField(max_length=32, blank=True)
    next_attempt_at = models.DateTimeField(null=True, blank=True, db_index=True)


class GoogleRetentionState(models.Model):
    key = models.CharField(max_length=32, primary_key=True, default="google")
    last_started_at = models.DateTimeField(null=True)
    last_finished_at = models.DateTimeField(null=True)
    last_success_at = models.DateTimeField(null=True)
    counts = models.JSONField(default=dict)
