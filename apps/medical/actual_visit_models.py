from django.conf import settings
from django.db import models


class MedicalActualVisit(models.Model):
    appointment = models.OneToOneField("scheduling.Appointment", on_delete=models.PROTECT,
        related_name="medical_actual_visit")
    patient = models.ForeignKey("medical.PatientProfile", on_delete=models.PROTECT, related_name="actual_visits")
    recorded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="recorded_actual_visits")
    recorded_at = models.DateTimeField(auto_now_add=True)
    started_at = models.DateTimeField()
    evidence_encrypted = models.TextField(editable=False)

    class Meta:
        constraints = [models.CheckConstraint(condition=~models.Q(evidence_encrypted=""), name="medical_actual_visit_evidence"),
            models.CheckConstraint(condition=models.Q(recorded_at__gte=models.F("started_at")), name="medical_actual_visit_time")]
