import hashlib
from unittest.mock import patch

from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied

from apps.core.file_scanning import FileQuarantined
from apps.core.models import FileAttachment
from apps.businesses.models import RolePermission
from . import tests_document_artifact_generation as fixtures
from . import tests_patient_services as crypto
from .audit import MedicalAuditUnavailable
from .document_artifact_services import read_document_draft_pdf
from .models import MedicalAuditEvent, MedicalRoleAssignment


@override_settings(MEDICAL_DATA_KEYS={"test": crypto.key(7)}, MEDICAL_DATA_ACTIVE_KEY_ID="test",
                   MEDICAL_IDENTITY_INDEX_KEY=crypto.key(8), USE_S3=False)
class DocumentArtifactPreviewTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        fixtures.DocumentArtifactGenerationTests.setUpTestData.__func__(cls)

    def setUp(self):
        fixtures.DocumentArtifactGenerationTests.setUp(self)
        self.item = fixtures.DocumentArtifactGenerationTests.prepare(self)[0]

    def read(self, **changes):
        return read_document_draft_pdf(actor=self.doctor, business_id=self.business.pk,
            patient_id=self.patient.pk, version_id=self.version.pk, language="ru",
            appointment_id=self.appointment.pk, **changes)

    def test_export_and_print_require_export_permission_before_open_and_record_exact_version(self):
        body = self.mark_clean_fixture()
        RolePermission.objects.update_or_create(business_role=self.role, resource="medical_documents",
            action="export", defaults={"scope": "business", "is_allowed": False})
        for purpose in ("download", "print"):
            with patch("apps.medical.document_artifact_services.open_clean_attachment", side_effect=AssertionError("Do not open")):
                with self.assertRaises(PermissionDenied):
                    self.read(purpose=purpose)
        self.assertEqual(self.read(), body)
        RolePermission.objects.filter(business_role=self.role, resource="medical_documents", action="export").update(is_allowed=True)
        for purpose, action in (("download", "document_exported"), ("print", "document_print_requested")):
            self.assertEqual(self.read(purpose=purpose), body)
            self.assertTrue(MedicalAuditEvent.objects.filter(action=action, document_version=self.version,
                patient=self.patient, actor=self.doctor).exists())

    def test_export_quarantine_and_audit_failure_never_release_bytes(self):
        RolePermission.objects.update_or_create(business_role=self.role, resource="medical_documents",
            action="export", defaults={"scope": "business", "is_allowed": True})
        with self.assertRaises(FileQuarantined):
            self.read(purpose="download")
        self.mark_clean_fixture()
        with patch("apps.medical.document_artifact_services.write_patient_audit", side_effect=MedicalAuditUnavailable):
            with self.assertRaises(MedicalAuditUnavailable):
                self.read(purpose="print")
        self.assertFalse(MedicalAuditEvent.objects.filter(action__in=["document_exported", "document_print_requested"]).exists())

    def mark_clean_fixture(self):
        with self.item.attachment.file.open("rb") as source:
            body = source.read()
        # Synthetic scan result, not evidence of a real antivirus provider.
        FileAttachment.objects.filter(pk=self.item.attachment_id).update(scan_status="clean",
            scan_sha256=hashlib.sha256(body).hexdigest(), scanned_at=timezone.now())
        return body

    def test_quarantine_blocks_preview_then_exact_bytes_require_read_audit(self):
        before = MedicalAuditEvent.objects.count()
        with self.assertRaises(FileQuarantined):
            self.read()
        self.assertEqual(MedicalAuditEvent.objects.count(), before)
        body = self.mark_clean_fixture()
        self.assertEqual(self.read(), body)
        self.assertEqual(MedicalAuditEvent.objects.filter(action="read", document_version=self.version).count(), 2)

    def test_revocation_prevents_storage_open_even_for_previously_clean_pdf(self):
        self.mark_clean_fixture()
        MedicalRoleAssignment.objects.filter(pk=self.assignment.pk).update(revoked_at=timezone.now())
        with patch("apps.medical.document_artifact_services.open_clean_attachment", side_effect=AssertionError("Do not open")):
            with self.assertRaises(PermissionDenied):
                self.read()

    def test_storage_replacement_is_quarantined_and_quarantine_persists(self):
        self.mark_clean_fixture()
        with self.item.attachment.file.open("wb") as target:
            target.write(b"changed")
        with self.assertRaises(FileQuarantined):
            self.read()
        blob = FileAttachment.objects.get(pk=self.item.attachment_id)
        self.assertEqual(blob.scan_status, "error")
        self.assertEqual(blob.scan_sha256, "")

    def test_audit_failure_returns_no_pdf_and_preserves_saved_file(self):
        body = self.mark_clean_fixture()
        with patch("apps.medical.document_artifact_services.write_patient_audit", side_effect=MedicalAuditUnavailable):
            with self.assertRaises(MedicalAuditUnavailable):
                self.read()
        self.assertEqual(self.read(), body)
