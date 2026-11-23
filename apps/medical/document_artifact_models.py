from django.core.exceptions import ValidationError
from django.db import models


class MedicalDocumentArtifact(models.Model):
    version = models.ForeignKey("medical.MedicalDocumentRevision", on_delete=models.PROTECT,
                                related_name="artifacts")
    attachment = models.OneToOneField("core.FileAttachment", on_delete=models.PROTECT,
                                     related_name="medical_document_artifact")
    format = models.CharField(max_length=8, choices=[("pdf", "PDF"), ("docx", "DOCX")])
    language = models.CharField(max_length=2, choices=[("ru", "RU"), ("kk", "KK"), ("en", "EN")])
    rendition = models.CharField(max_length=8, default="draft", choices=[("draft", "Draft"), ("signing", "For signing")])
    sha256 = models.CharField(max_length=64, editable=False)
    size = models.PositiveBigIntegerField(editable=False)
    manifest_encrypted = models.TextField(editable=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["version", "format", "language", "rendition"], name="medical_artifact_version_unique"),
            models.CheckConstraint(condition=models.Q(rendition="draft") | models.Q(rendition="signing", format="pdf"), name="medical_artifact_rendition"),
            models.CheckConstraint(condition=models.Q(format__in=["pdf", "docx"]), name="medical_artifact_format"),
            models.CheckConstraint(condition=models.Q(language__in=["ru", "kk", "en"]), name="medical_artifact_language"),
            models.CheckConstraint(condition=models.Q(size__gt=0, size__lte=10485760), name="medical_artifact_size"),
            models.CheckConstraint(condition=~models.Q(manifest_encrypted=""), name="medical_artifact_manifest"),
        ]

    def clean(self):
        super().clean()
        if not self.version_id or not self.attachment_id:
            raise ValidationError("A document artifact requires a revision and private attachment.")
        document = self.version.document
        document.clean()
        blob = self.attachment
        if (blob.business_id != document.business_id or blob.visibility != "private"
                or blob.entity_type != "medical_document_artifact"
                or blob.entity_id != str(self.version_id) or blob.size != self.size
                or self.version.revision > document.revision):
            raise ValidationError("Document artifact links must match the saved revision and business.")
        mime = {"pdf": "application/pdf", "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document"}
        if blob.content_type != mime.get(self.format):
            raise ValidationError("Document artifact format must match its attachment.")
