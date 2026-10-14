from django.conf import settings
from django.db import models


class SupportCase(models.Model):
    class Statuses(models.TextChoices):
        NEW = "new", "New"
        IN_PROGRESS = "in_progress", "In progress"
        WAITING_CLINIC = "waiting_clinic", "Waiting for clinic"
        WAITING_INTERNAL = "waiting_internal", "Waiting internally"
        RESOLVED = "resolved", "Resolved"

    class Sources(models.TextChoices):
        CLINIC = "clinic", "Clinic"
        PLATFORM = "platform", "Platform"

    business = models.ForeignKey("businesses.Business", on_delete=models.PROTECT, related_name="support_cases")
    subject = models.CharField(max_length=200)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="created_support_cases")
    requester = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="requested_support_cases")
    source = models.CharField(max_length=16, choices=Sources.choices)
    status = models.CharField(max_length=24, choices=Statuses.choices, default=Statuses.NEW)
    assigned_to = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, null=True, blank=True, related_name="assigned_support_cases")
    version = models.PositiveIntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now_add=True)
    last_public_message_at = models.DateTimeField(null=True, blank=True)
    resolved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-updated_at", "-id"]
        indexes = [
            models.Index(fields=["business", "status", "-updated_at"]),
            models.Index(fields=["status", "assigned_to", "-updated_at"]),
        ]
        constraints = [
            models.CheckConstraint(condition=models.Q(version__gte=1), name="support_case_positive_version"),
            models.CheckConstraint(condition=models.Q(status__in=["new", "in_progress", "waiting_clinic", "waiting_internal", "resolved"]), name="support_case_valid_status"),
            models.CheckConstraint(condition=models.Q(source__in=["clinic", "platform"]), name="support_case_valid_source"),
            models.CheckConstraint(condition=(models.Q(status="resolved", resolved_at__isnull=False) | (~models.Q(status="resolved") & models.Q(resolved_at__isnull=True))), name="support_case_resolved_timestamp"),
        ]


class PublicMessage(models.Model):
    case = models.ForeignKey(SupportCase, on_delete=models.PROTECT, related_name="public_messages")
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="support_messages")
    source = models.CharField(max_length=16, choices=SupportCase.Sources.choices)
    text = models.TextField(max_length=6000)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["id"]
        indexes = [models.Index(fields=["case", "id"])]


class InternalNote(models.Model):
    """Private platform content: deliberately not a flag on PublicMessage."""

    case = models.ForeignKey(SupportCase, on_delete=models.PROTECT, related_name="internal_notes")
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="internal_support_notes")
    text = models.TextField(max_length=6000)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-id"]
        indexes = [models.Index(fields=["case", "id"])]


class CaseEvent(models.Model):
    class Kinds(models.TextChoices):
        CREATED = "created", "Created"
        ASSIGNED = "assigned", "Assigned"
        TRANSITIONED = "transitioned", "Transitioned"
        REOPENED = "reopened", "Reopened"

    case = models.ForeignKey(SupportCase, on_delete=models.PROTECT, related_name="events")
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="support_case_events")
    kind = models.CharField(max_length=24, choices=Kinds.choices)
    old_value = models.CharField(max_length=64, blank=True)
    new_value = models.CharField(max_length=64, blank=True)
    reason = models.TextField(max_length=4000, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-id"]
        indexes = [models.Index(fields=["case", "id"])]


class ReadState(models.Model):
    case = models.ForeignKey(SupportCase, on_delete=models.CASCADE, related_name="read_states")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="support_read_states")
    last_read_message_id = models.PositiveBigIntegerField(default=0)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["case", "user"], name="support_read_state_user_case")]


class IncidentLink(models.Model):
    """Immutable diagnostic reference; never part of the clinic conversation."""

    case = models.ForeignKey(SupportCase, on_delete=models.PROTECT, related_name="incident_links")
    component = models.CharField(max_length=32)
    episode = models.PositiveIntegerField()
    started_at = models.DateTimeField()
    observed_at = models.DateTimeField()
    state = models.CharField(max_length=16)
    affected_count = models.PositiveIntegerField()
    recovered_at = models.DateTimeField(null=True)
    linked_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="support_incident_links")
    linked_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["case", "component", "episode"], name="support_case_incident_unique"),
            models.CheckConstraint(condition=models.Q(episode__gte=1), name="support_incident_positive_episode"),
        ]
        indexes = [models.Index(fields=["component", "episode", "case"])]
