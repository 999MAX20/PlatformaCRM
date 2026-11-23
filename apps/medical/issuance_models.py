import uuid

from django.conf import settings
from django.db import models


class MedicalDocumentGrant(models.Model):
    patient = models.ForeignKey("medical.PatientProfile", on_delete=models.PROTECT, related_name="document_grants")
    encounter = models.ForeignKey("medical.MedicalEncounter", on_delete=models.PROTECT, related_name="document_grants")
    representative = models.ForeignKey("medical.PatientRepresentative", on_delete=models.PROTECT, null=True, blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    created_at = models.DateTimeField(auto_now_add=True)
    state = models.CharField(max_length=12, default="pending")
    revision = models.PositiveIntegerField(default=1)
    activated_at = models.DateTimeField(null=True, blank=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    revoked_at = models.DateTimeField(null=True, blank=True)
    code_hash = models.CharField(max_length=64, unique=True, editable=False)
    evidence_encrypted = models.TextField(editable=False)
    replaces = models.ForeignKey("self", on_delete=models.PROTECT, null=True, blank=True, related_name="reissues")

    class Meta:
        constraints = [
            models.CheckConstraint(condition=models.Q(state__in=["pending", "active", "revoked"], revision__gte=1)
                & ~models.Q(code_hash="") & ~models.Q(evidence_encrypted=""), name="medical_grant_valid"),
            models.CheckConstraint(condition=(models.Q(activated_at__isnull=True, expires_at__isnull=True)
                | models.Q(activated_at__isnull=False, expires_at__gt=models.F("activated_at"))), name="medical_grant_expiry"),
            models.CheckConstraint(condition=(models.Q(state="revoked", revoked_at__isnull=False)
                | models.Q(state__in=["pending", "active"], revoked_at__isnull=True)), name="medical_grant_revocation"),
        ]


class MedicalDocumentGrantItem(models.Model):
    public_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    grant = models.ForeignKey(MedicalDocumentGrant, on_delete=models.PROTECT, related_name="items")
    version = models.ForeignKey("medical.MedicalDocumentRevision", on_delete=models.PROTECT)
    finalization = models.ForeignKey("medical.MedicalDocumentFinalization", on_delete=models.PROTECT, null=True, blank=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["grant", "version"], name="medical_grant_version_unique")]


class MedicalDocumentGrantEvent(models.Model):
    grant = models.ForeignKey(MedicalDocumentGrant, on_delete=models.PROTECT, related_name="events")
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, null=True, blank=True)
    action = models.CharField(max_length=24)
    created_at = models.DateTimeField(auto_now_add=True)
    version = models.ForeignKey("medical.MedicalDocumentRevision", on_delete=models.PROTECT, null=True, blank=True)
    evidence_encrypted = models.TextField(editable=False)


class MedicalDocumentPortalSession(models.Model):
    grant = models.ForeignKey(MedicalDocumentGrant, on_delete=models.PROTECT, related_name="sessions")
    token_hash = models.CharField(max_length=64, unique=True, editable=False)
    expires_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)


class MedicalDocumentPortalAttempt(models.Model):
    bucket = models.CharField(max_length=64, primary_key=True)
    started_at = models.DateTimeField()
    count = models.PositiveIntegerField(default=0)
