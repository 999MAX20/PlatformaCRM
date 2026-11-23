import uuid

from django.db import models


class GoogleCalendarBinding(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    connection = models.ForeignKey("integrations.GoogleConnection", on_delete=models.PROTECT,
                                   related_name="calendar_bindings")
    resource = models.OneToOneField("scheduling.Resource", on_delete=models.PROTECT,
                                    related_name="google_calendar_binding")
    calendar_id = models.CharField(max_length=1024, unique=True)
    calendar_name = models.CharField(max_length=255)
    timezone = models.CharField(max_length=128)
    enabled = models.BooleanField(default=True)
    last_sync_at = models.DateTimeField(null=True)
    coverage_start = models.DateTimeField(null=True)
    coverage_end = models.DateTimeField(null=True)
    error_code = models.CharField(max_length=64, blank=True)
    next_sync_at = models.DateTimeField(null=True)
    failures = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["connection", "calendar_id"],
                                               name="unique_google_calendar_binding")]


class GoogleCalendarBusy(models.Model):
    binding = models.ForeignKey(GoogleCalendarBinding, on_delete=models.CASCADE, related_name="busy")
    start_at = models.DateTimeField()
    end_at = models.DateTimeField()

    class Meta:
        constraints = [models.CheckConstraint(condition=models.Q(start_at__lt=models.F("end_at")),
                                               name="google_busy_time_order")]
        indexes = [models.Index(fields=["binding", "start_at", "end_at"], name="google_busy_interval_idx")]


class GoogleCalendarMirror(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    binding = models.ForeignKey(GoogleCalendarBinding, on_delete=models.PROTECT, related_name="mirrors")
    appointment = models.ForeignKey("scheduling.Appointment", on_delete=models.PROTECT)
    event_id = models.CharField(max_length=128, default="")
    generation = models.PositiveIntegerField(default=0)
    state = models.CharField(max_length=16, default="pending")
    synced_at = models.DateTimeField(null=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["binding", "appointment"],
                                               name="unique_google_appointment_mirror")]
