import hashlib
from unittest.mock import patch

from django.core.exceptions import ValidationError
from django.db import transaction
from django.test import TestCase, override_settings

from apps.core.models import FileAttachment
from apps.businesses.models import Business
from . import tests_document_content as fixtures
from . import tests_patient_services as crypto_fixtures
from .document_artifact_content import register_document_artifact, read_document_artifact_manifest, verify_document_artifact_bytes
from .identity_crypto import MedicalDataUnavailable
from .models import MedicalDocumentArtifact


@override_settings(MEDICAL_DATA_KEYS={"test": crypto_fixtures.key(7)}, MEDICAL_DATA_ACTIVE_KEY_ID="test",
                   MEDICAL_IDENTITY_INDEX_KEY=crypto_fixtures.key(8))
class DocumentArtifactTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        fixtures.DocumentContentTests.setUpTestData.__func__(cls)

    def setUp(self):
        self.version = fixtures.DocumentContentTests.append(self)
        self.body = b"%PDF-synthetic artifact bytes"
        self.blob = FileAttachment.objects.create(business=self.business, uploaded_by=self.doctor,
            file="private/attachments/synthetic-artifact.pdf", original_name="document.pdf",
            content_type="application/pdf", size=len(self.body), entity_type="medical_document_artifact",
            entity_id=str(self.version.pk))

    def register(self, **changes):
        return register_document_artifact(**({"version": self.version, "attachment": self.blob, "format": "pdf",
            "language": "ru", "sha256": hashlib.sha256(self.body).hexdigest(), "renderer": "draft-pdf-v1"} | changes))

    def test_roundtrip_binds_revision_and_bytes_without_plaintext_manifest(self):
        item = self.register()
        manifest = read_document_artifact_manifest(item)
        self.assertEqual(manifest["version_id"], self.version.pk)
        self.assertEqual(manifest["storage_name"], self.blob.file.name)
        self.assertNotIn("storage_name", item.manifest_encrypted)
        self.assertNotIn("Учебный", item.manifest_encrypted)
        self.assertEqual(verify_document_artifact_bytes(item, self.body), self.body)
        self.assertEqual(self.blob.scan_status, "pending")

    def test_altered_bytes_fail_even_if_attachment_scan_is_marked_clean_again(self):
        item = self.register()
        changed = self.body[:-1] + b"!"
        FileAttachment.objects.filter(pk=self.blob.pk).update(scan_status="clean",
            scan_sha256=hashlib.sha256(changed).hexdigest())
        with self.assertRaises(MedicalDataUnavailable):
            verify_document_artifact_bytes(item, changed)

    def test_second_registration_cannot_replace_first_artifact(self):
        first = self.register()
        before = first.manifest_encrypted
        with self.assertRaises(ValidationError):
            self.register()
        first.refresh_from_db()
        self.assertEqual(first.manifest_encrypted, before)
        self.assertEqual(MedicalDocumentArtifact.objects.count(), 1)

    def test_later_document_revision_and_clinic_changes_preserve_old_artifact(self):
        item = self.register()
        before = read_document_artifact_manifest(item)
        self.business.legal_name = "Later clinic name"
        self.business.save(update_fields=["legal_name"])
        self.document.refresh_from_db()
        later = fixtures.DocumentContentTests.append(self, template={"code": "synthetic_form", "version": 2,
            "title": "Later document", "text": "Later text"})
        self.assertNotEqual(later.pk, self.version.pk)
        self.assertEqual(read_document_artifact_manifest(item), before)
        self.assertEqual(verify_document_artifact_bytes(item, self.body), self.body)

    def test_mismatched_revision_or_generic_storage_is_rejected(self):
        for field, value in (("entity_id", "wrong-version"), ("entity_type", "client"), ("content_type", "image/png")):
            original = getattr(self.blob, field)
            FileAttachment.objects.filter(pk=self.blob.pk).update(**{field: value})
            with self.subTest(field=field), self.assertRaises(ValidationError):
                self.register()
            FileAttachment.objects.filter(pk=self.blob.pk).update(**{field: original})
        self.assertFalse(MedicalDocumentArtifact.objects.exists())

    def test_relinked_blob_or_artifact_checksum_cannot_bypass_manifest(self):
        item = self.register()
        FileAttachment.objects.filter(pk=self.blob.pk).update(file="private/attachments/replaced.pdf")
        with self.assertRaises(MedicalDataUnavailable):
            read_document_artifact_manifest(item)
        FileAttachment.objects.filter(pk=self.blob.pk).update(file=self.blob.file.name)
        MedicalDocumentArtifact.objects.filter(pk=item.pk).update(sha256="a" * 64)
        with self.assertRaises(MedicalDataUnavailable):
            read_document_artifact_manifest(item)

    def test_manifest_cannot_be_copied_between_languages(self):
        first = self.register()
        other_blob = FileAttachment.objects.create(business=self.business, uploaded_by=self.doctor,
            file="private/attachments/second.pdf", original_name="document.pdf", content_type="application/pdf",
            size=len(self.body), entity_type="medical_document_artifact", entity_id=str(self.version.pk))
        second = self.register(attachment=other_blob, language="kk")
        MedicalDocumentArtifact.objects.filter(pk=second.pk).update(manifest_encrypted=first.manifest_encrypted)
        with self.assertRaises(MedicalDataUnavailable):
            read_document_artifact_manifest(second)

    def test_invalid_metadata_and_missing_logo_do_not_create_artifact(self):
        for changes in ({"format": "html"}, {"language": "xx"}, {"sha256": "bad"},
                        {"renderer": ""}, {"captured_logo": b"unexpected"}):
            with self.subTest(changes=changes), self.assertRaises(ValidationError):
                self.register(**changes)
        self.assertFalse(MedicalDocumentArtifact.objects.exists())

    def test_manifest_encryption_failure_rolls_back_registration(self):
        from .document_artifact_content import encrypt_medical_value

        def fail_manifest(*args, **kwargs):
            if kwargs["purpose"] == "document_artifact_manifest":
                raise MedicalDataUnavailable()
            return encrypt_medical_value(*args, **kwargs)

        with patch("apps.medical.document_artifact_content.encrypt_medical_value", side_effect=fail_manifest):
            with self.assertRaises(MedicalDataUnavailable):
                self.register()
        self.assertFalse(MedicalDocumentArtifact.objects.exists())

    def test_outer_rollback_does_not_leave_artifact_registration(self):
        with self.assertRaises(RuntimeError):
            with transaction.atomic():
                self.register()
                raise RuntimeError("Synthetic rollback")
        self.assertFalse(MedicalDocumentArtifact.objects.exists())

    def test_foreign_business_attachment_is_not_registered_or_read(self):
        other = Business.objects.create(owner=self.owner, name="Other synthetic clinic", slug="artifact-other")
        FileAttachment.objects.filter(pk=self.blob.pk).update(business=other)
        with self.assertRaises(FileAttachment.DoesNotExist):
            self.register()
        self.assertFalse(MedicalDocumentArtifact.objects.exists())
        FileAttachment.objects.filter(pk=self.blob.pk).update(business=self.business)
        item = self.register()
        FileAttachment.objects.filter(pk=self.blob.pk).update(business=other)
        with self.assertRaises(MedicalDataUnavailable):
            read_document_artifact_manifest(item)
