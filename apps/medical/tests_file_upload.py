from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from rest_framework.exceptions import PermissionDenied, ValidationError

from apps.businesses.models import RolePermission
from apps.billing.models import Subscription, SubscriptionPlan
from apps.core.domain_errors import InvalidTransition
from apps.core.idempotency import CRMCommandConflict
from apps.core.models import CRMCommandIdempotency, FileAttachment
from . import tests_encounter_services as fixtures
from . import tests_patient_services as crypto
from .audit import MedicalAuditUnavailable
from .file_content import read_file_metadata
from .file_services import MedicalFileStorageUnavailable, upload_medical_file
from .models import MedicalAttachment, MedicalAuditEvent


@override_settings(MEDICAL_DATA_KEYS={"test": crypto.key(7)}, MEDICAL_DATA_ACTIVE_KEY_ID="test",
                   MEDICAL_IDENTITY_INDEX_KEY=crypto.key(8), USE_S3=False)
class MedicalFileUploadTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        fixtures.PrimaryEncounterDraftTests.setUpTestData.__func__(cls)
        for action in ("view", "create", "export"):
            RolePermission.objects.create(business_role=cls.role, resource="medical_files", action=action,
                                          scope="business", is_allowed=True)

    def setUp(self):
        self.directory = TemporaryDirectory(prefix="medical-upload-test-")
        self.addCleanup(self.directory.cleanup)
        self.settings_override = override_settings(MEDIA_ROOT=self.directory.name)
        self.settings_override.enable()
        self.addCleanup(self.settings_override.disable)

    def upload(self, **overrides):
        return upload_medical_file(**({"actor": self.doctor, "business_id": self.business.pk,
            "patient_id": self.patient.pk, "record_id": self.record.pk,
            "appointment_id": self.appointment.pk, "encounter_id": self.encounter_record.pk,
            "expected_patient_revision": self.patient.revision, "idempotency_key": "synthetic-file-command",
            "description": "Synthetic private description", "teeth": [11],
            "uploaded_file": SimpleUploadedFile("Private-patient-name.pdf", b"%PDF-1.4\nSynthetic", "application/pdf")}
            | overrides))

    def stored_files(self):
        return [item for item in Path(self.directory.name).rglob("*") if item.is_file()]

    def test_upload_quarantines_opaque_blob_and_replay_does_not_duplicate_bytes(self):
        first, replay = self.upload()
        second, replay2 = self.upload()
        self.assertFalse(replay)
        self.assertTrue(replay2)
        self.assertEqual(first.pk, second.pk)
        self.assertEqual((MedicalAttachment.objects.count(), FileAttachment.objects.count(), len(self.stored_files())), (1, 1, 1))
        blob = first.medical_file.attachment
        self.assertEqual((blob.scan_status, blob.original_name), ("pending", "attachment.pdf"))
        self.assertNotIn("Private-patient", blob.file.name)
        self.assertEqual(read_file_metadata(first)["name"], "Private-patient-name.pdf")
        self.assertEqual(MedicalAuditEvent.objects.get(action="file_uploaded").file_version_id, first.pk)
        self.assertNotIn("Private-patient", str(list(CRMCommandIdempotency.objects.values())))

    def test_same_key_with_different_bytes_is_a_conflict(self):
        self.upload()
        with self.assertRaises(CRMCommandConflict):
            self.upload(uploaded_file=SimpleUploadedFile("Private-patient-name.pdf", b"%PDF-1.4\nOther", "application/pdf"))
        self.assertEqual(len(self.stored_files()), 1)

    def test_audit_failure_rolls_back_metadata_command_and_physical_blob(self):
        with patch("apps.medical.file_services.write_patient_audit", side_effect=MedicalAuditUnavailable()):
            with self.assertRaises(MedicalAuditUnavailable):
                self.upload()
        self.assertEqual((FileAttachment.objects.count(), MedicalAttachment.objects.count(),
                          CRMCommandIdempotency.objects.count(), len(self.stored_files())), (0, 0, 0, 0))

    def test_storage_error_does_not_expose_provider_details(self):
        with patch("django.db.models.fields.files.FieldFile.save", side_effect=OSError("secret-provider-url")):
            with self.assertRaises(MedicalFileStorageUnavailable) as caught:
                self.upload()
        self.assertNotIn("secret-provider", str(caught.exception))
        self.assertEqual(FileAttachment.objects.count(), 0)

    def test_storage_quota_uses_exact_bytes_near_display_rounding_boundary(self):
        plan = SubscriptionPlan.objects.create(name="Synthetic quota", code="medical-file-quota", limits_json={"storage_mb": 1})
        Subscription.objects.update_or_create(business=self.business, defaults={"plan": plan})
        FileAttachment.objects.create(business=self.business, uploaded_by=self.doctor,
            file="private/attachments/synthetic-quota.pdf", original_name="attachment.pdf", content_type="application/pdf",
            size=1042000, entity_type="medical_attachment", entity_id="synthetic")
        with self.assertRaises(ValidationError):
            self.upload(uploaded_file=SimpleUploadedFile("test.pdf", b"%PDF-1.4\n" + b"x" * 7000, "application/pdf"))
        self.assertEqual(MedicalAttachment.objects.count(), 0)
        self.assertEqual(len(self.stored_files()), 0)
        self.upload(uploaded_file=SimpleUploadedFile("test.pdf", b"%PDF-1.4\n" + b"x" * 6567, "application/pdf"))
        self.assertEqual(MedicalAttachment.objects.count(), 1)

    def test_denied_stale_or_invalid_upload_writes_nothing(self):
        with self.assertRaises(PermissionDenied):
            self.upload(actor=self.owner)
        with self.assertRaises(InvalidTransition):
            self.upload(expected_patient_revision=self.patient.revision + 1)
        for name, body, mime in (("file.pdf", b"not-pdf", "application/pdf"),
                                 ("file.pdf", b"%PDF-1.4", "image/png"),
                                 ("file.webp", b"RIFF1234WAVE", "image/webp"),
                                 ("file.html", b"<html>", "text/html")):
            with self.subTest(name=name, mime=mime), self.assertRaises(ValidationError):
                self.upload(uploaded_file=SimpleUploadedFile(name, body, mime))
        self.assertEqual((FileAttachment.objects.count(), len(self.stored_files())), (0, 0))
