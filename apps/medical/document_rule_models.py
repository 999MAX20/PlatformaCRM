from django.conf import settings
from django.db import models


class MedicalDocumentKind(models.Model):
    business = models.ForeignKey("businesses.Business", on_delete=models.PROTECT,
        related_name="medical_document_kinds")
    revision = models.PositiveIntegerField(default=0)


class MedicalDocumentRuleRevision(models.Model):
    kind = models.ForeignKey(MedicalDocumentKind, on_delete=models.PROTECT, related_name="versions")
    revision = models.PositiveIntegerField()
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT,
        related_name="medical_document_rule_versions")
    created_at = models.DateTimeField(auto_now_add=True)
    snapshot_encrypted = models.TextField(editable=False)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["kind", "revision"], name="medical_doc_rule_version_unique"),
            models.CheckConstraint(condition=models.Q(revision__gte=1), name="medical_doc_rule_ver_positive"),
            models.CheckConstraint(condition=~models.Q(snapshot_encrypted=""), name="medical_doc_rule_content"),
        ]
