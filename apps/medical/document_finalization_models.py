from django.conf import settings
from django.db import models


class MedicalDocumentFinalization(models.Model):
    version = models.OneToOneField("medical.MedicalDocumentRevision", on_delete=models.PROTECT, related_name="finalization")
    submission = models.OneToOneField("medical.MedicalDocumentReviewTransition", on_delete=models.PROTECT, related_name="finalization")
    artifact = models.ForeignKey("medical.MedicalDocumentArtifact", on_delete=models.PROTECT, related_name="finalizations")
    signing_session = models.ForeignKey("medical.MedicalSigningSession", on_delete=models.PROTECT, null=True, related_name="finalizations")
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="medical_document_finalizations")
    created_at = models.DateTimeField(auto_now_add=True)
    evidence_encrypted = models.TextField(editable=False)

    class Meta:
        constraints = [models.CheckConstraint(condition=~models.Q(evidence_encrypted=""), name="medical_finalization_evidence")]
