from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models

from apps.businesses.models import TimeStampedModel


class MedicalAttachment(TimeStampedModel):
    business = models.ForeignKey("businesses.Business", on_delete=models.PROTECT)
    patient = models.ForeignKey("medical.PatientProfile", on_delete=models.PROTECT, related_name="medical_files")
    record = models.ForeignKey("medical.DentalMedicalRecord", on_delete=models.PROTECT, related_name="medical_files")
    branch = models.ForeignKey("branches.Branch", on_delete=models.PROTECT)
    encounter = models.ForeignKey("medical.MedicalEncounter", on_delete=models.PROTECT,
                                  null=True, blank=True, related_name="medical_files")
    attachment = models.OneToOneField("core.FileAttachment", on_delete=models.PROTECT,
                                      related_name="medical_file")
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    revision = models.PositiveIntegerField(default=1)

    class Meta:
        indexes = [models.Index(fields=["business", "patient", "id"], name="medical_file_patient_idx")]
        constraints = [models.CheckConstraint(condition=models.Q(revision__gte=1),
                                             name="medical_file_revision_positive")]

    def clean(self):
        if not all((self.business_id, self.patient_id, self.record_id, self.branch_id, self.attachment_id)):
            raise ValidationError("Medical file requires complete clinical and storage links.")
        if (self.patient.business_id != self.business_id or self.patient.client.business_id != self.business_id
                or self.record.business_id != self.business_id or self.record.patient_id != self.patient_id
                or self.branch.business_id != self.business_id or self.attachment.business_id != self.business_id
                or self.attachment.entity_type != "medical_attachment" or self.attachment.visibility != "private"):
            raise ValidationError("Medical file links must belong to the same patient and business.")
        if self.encounter_id and (self.encounter.business_id != self.business_id
                or self.encounter.patient_id != self.patient_id or self.encounter.record_id != self.record_id
                or self.encounter.branch_id != self.branch_id):
            raise ValidationError("Medical file encounter must match its record, patient and branch.")


class MedicalAttachmentRevision(models.Model):
    medical_file = models.ForeignKey(MedicalAttachment, on_delete=models.PROTECT, related_name="versions")
    revision = models.PositiveIntegerField()
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    metadata_encrypted = models.TextField(editable=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-revision"]
        constraints = [
            models.UniqueConstraint(fields=["medical_file", "revision"], name="medical_file_version_unique"),
            models.CheckConstraint(condition=models.Q(revision__gte=1), name="medical_file_version_positive"),
            models.CheckConstraint(condition=~models.Q(metadata_encrypted=""), name="medical_file_metadata_required"),
        ]

    def clean(self):
        if not self.medical_file_id or not self.author_id:
            raise ValidationError("Medical file version requires a file and author.")
        self.medical_file.clean()
        if self.revision > self.medical_file.revision:
            raise ValidationError("Medical file version exceeds its current revision.")
