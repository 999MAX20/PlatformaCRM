import uuid

from django.conf import settings
from django.db import models


class MedicalSigningSession(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    artifact = models.ForeignKey("medical.MedicalDocumentArtifact", on_delete=models.PROTECT, related_name="signing_sessions")
    submission = models.ForeignKey("medical.MedicalDocumentReviewTransition", on_delete=models.PROTECT, related_name="signing_sessions")
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="medical_signing_sessions")
    state = models.CharField(max_length=12, default="pending", choices=[("pending", "Pending"), ("completed", "Completed"), ("cancelled", "Cancelled")])
    revision = models.PositiveIntegerField(default=1)
    adapter = models.CharField(max_length=32)
    created_at = models.DateTimeField(auto_now_add=True)
    ended_at = models.DateTimeField(null=True)

    class Meta:
        constraints = [
            models.CheckConstraint(condition=models.Q(revision__gte=1), name="medical_signing_revision"),
            models.CheckConstraint(condition=(models.Q(state="pending", ended_at__isnull=True)
                | models.Q(state__in=["completed", "cancelled"], ended_at__isnull=False)), name="medical_signing_state"),
            models.UniqueConstraint(fields=["submission"], condition=models.Q(state="pending"), name="medical_signing_pending_unique"),
        ]


class MedicalSigningEvent(models.Model):
    session = models.ForeignKey(MedicalSigningSession, on_delete=models.PROTECT, related_name="events")
    revision = models.PositiveIntegerField()
    action = models.CharField(max_length=12, choices=[("created", "Created"), ("signed", "Signed"), ("cancelled", "Cancelled")])
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="medical_signing_events")
    signer = models.CharField(max_length=32, blank=True)
    position = models.PositiveSmallIntegerField(null=True)
    proof_encrypted = models.TextField(editable=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["session", "revision"], name="medical_signing_event_revision"),
            models.UniqueConstraint(fields=["session", "position"], condition=models.Q(action="signed"), name="medical_signing_position_unique"),
            models.CheckConstraint(condition=models.Q(revision__gte=1) & ~models.Q(proof_encrypted=""), name="medical_signing_event_content"),
            models.CheckConstraint(condition=(models.Q(action__in=["created", "cancelled"], position__isnull=True, signer="") |
                models.Q(action="signed", position__gte=1, position__isnull=False, signer__in=["primary_clinician", "medical_head", "patient_or_representative"])),
                name="medical_signing_event_action"),
        ]
