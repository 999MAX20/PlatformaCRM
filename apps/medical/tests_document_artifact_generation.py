from io import BytesIO
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from django.test import TestCase, override_settings
from django.utils import timezone
from pypdf import PdfReader
from PIL import Image
import base64
from rest_framework.exceptions import PermissionDenied, ValidationError

from apps.core.models import FileAttachment
from . import tests_document_template_source as fixtures
from . import tests_patient_services as crypto
from .audit import MedicalAuditUnavailable
from .document_artifact_services import prepare_document_draft_pdf, DocumentPDFUnavailable
from .document_pdf import DocumentRenderUnavailable
from .document_artifact_content import read_document_artifact_manifest
from .file_services import MedicalFileStorageUnavailable
from .identity_crypto import MedicalDataUnavailable
from .models import MedicalDocumentArtifact, MedicalRoleAssignment


@override_settings(MEDICAL_DATA_KEYS={"test": crypto.key(7)}, MEDICAL_DATA_ACTIVE_KEY_ID="test",
                   MEDICAL_IDENTITY_INDEX_KEY=crypto.key(8), USE_S3=False)
class DocumentArtifactGenerationTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        fixtures.DocumentTemplateSourceTests.setUpTestData.__func__(cls)

    def setUp(self):
        self.directory = TemporaryDirectory(prefix="document-pdf-test-")
        self.addCleanup(self.directory.cleanup)
        settings = override_settings(MEDIA_ROOT=self.directory.name)
        settings.enable()
        self.addCleanup(settings.disable)
        fixtures.DocumentTemplateSourceTests.setUp(self)
        fixtures.DocumentTemplateSourceTests.approve(self)
        self.version = fixtures.DocumentTemplateSourceTests.save(self)[0]

    def prepare(self, **changes):
        return prepare_document_draft_pdf(**({"actor": self.doctor, "business_id": self.business.pk,
            "patient_id": self.patient.pk, "version_id": self.version.pk, "language": "ru",
            "appointment_id": self.appointment.pk} | changes))

    def files(self):
        return [path for path in Path(self.directory.name).rglob("*") if path.is_file()]

    def test_review_transition_preserves_existing_pdf_and_allows_first_render(self):
        from .document_review_services import transition_document_review
        first, _ = self.prepare()
        transition_document_review(actor=self.doctor, business_id=self.business.pk, patient_id=self.patient.pk,
            version_id=self.version.pk, appointment_id=self.appointment.pk, expected_state_revision=1,
            target="ready_for_review", reason="", idempotency_key="review-render")
        transition_document_review(actor=self.doctor, business_id=self.business.pk, patient_id=self.patient.pk,
            version_id=self.version.pk, appointment_id=self.appointment.pk, expected_state_revision=2,
            target="reviewed", reason="", idempotency_key="confirm-render")
        with patch("apps.medical.document_artifact_services.render_draft_pdf", side_effect=AssertionError("Immutable PDF")):
            replay, replayed = self.prepare()
        self.assertEqual(replay.pk, first.pk)
        self.assertTrue(replayed)
        second, replayed = self.prepare(language="kk")
        self.assertFalse(replayed)
        self.assertEqual(second.version_id, self.version.pk)

    def test_generation_persists_exact_saved_text_in_quarantine_and_reuses_bytes(self):
        first, replayed = self.prepare()
        self.assertFalse(replayed)
        with first.attachment.file.open("rb") as source:
            body = source.read()
        self.assertIn("Doctor edited synthetic text", PdfReader(BytesIO(body)).pages[0].extract_text())
        self.assertEqual(first.attachment.scan_status, "pending")
        self.assertEqual(first.attachment.original_name, "document.pdf")
        with patch("apps.medical.document_artifact_services.render_draft_pdf", side_effect=AssertionError("Do not regenerate")):
            second, replayed = self.prepare()
        self.assertTrue(replayed)
        self.assertEqual(second.pk, first.pk)
        self.assertEqual((len(self.files()), MedicalDocumentArtifact.objects.count(), FileAttachment.objects.count()), (1, 1, 1))

    def test_revoked_access_blocks_replay_before_artifact_read(self):
        self.prepare()
        MedicalRoleAssignment.objects.filter(pk=self.assignment.pk).update(revoked_at=timezone.now())
        with patch("apps.medical.document_artifact_services.read_document_artifact_manifest", side_effect=AssertionError("Do not read")):
            with self.assertRaises(PermissionDenied):
                self.prepare()
        self.assertEqual(len(self.files()), 1)

    def test_audit_failure_removes_new_blob_and_database_rows(self):
        with patch("apps.medical.document_artifact_services.write_patient_audit", side_effect=MedicalAuditUnavailable):
            with self.assertRaises(MedicalAuditUnavailable):
                self.prepare()
        self.assertEqual(self.files(), [])
        self.assertFalse(MedicalDocumentArtifact.objects.exists())
        self.assertFalse(FileAttachment.objects.exists())

    def test_audit_failure_on_replay_preserves_existing_file(self):
        first, _ = self.prepare()
        with patch("apps.medical.document_artifact_services.write_patient_audit", side_effect=MedicalAuditUnavailable):
            with self.assertRaises(MedicalAuditUnavailable):
                self.prepare()
        self.assertEqual(len(self.files()), 1)
        self.assertTrue(MedicalDocumentArtifact.objects.filter(pk=first.pk).exists())

    def test_renderer_failure_and_storage_quota_leave_no_partial_artifact(self):
        with patch("apps.medical.document_artifact_services.render_draft_pdf", side_effect=DocumentRenderUnavailable):
            with self.assertRaises(DocumentPDFUnavailable):
                self.prepare()
        with patch("apps.medical.document_artifact_services.get_storage_limit_mb", return_value=0):
            with self.assertRaises(ValidationError):
                self.prepare()
        self.assertEqual(self.files(), [])
        self.assertFalse(MedicalDocumentArtifact.objects.exists())

    def test_unsafe_saved_logo_fails_without_partial_artifact(self):
        self.business.brand_logo_url = "http://127.0.0.1/private"
        self.business.save(update_fields=["brand_logo_url"])
        self.version = fixtures.DocumentTemplateSourceTests.save(self, idempotency_key="logo-document")[0]
        with patch("urllib.request.urlopen", side_effect=AssertionError("No fetch")):
            with self.assertRaises(DocumentPDFUnavailable):
                self.prepare()
        self.assertEqual(self.files(), [])
        self.assertFalse(MedicalDocumentArtifact.objects.exists())

    def test_storage_error_exposes_no_provider_details_or_partial_database_rows(self):
        storage = FileAttachment._meta.get_field("file").storage
        with patch.object(storage, "save", side_effect=RuntimeError("Synthetic private provider credentials")):
            with self.assertRaises(MedicalFileStorageUnavailable) as error:
                self.prepare()
        self.assertNotIn("credentials", str(error.exception))
        self.assertEqual(self.files(), [])
        self.assertFalse(MedicalDocumentArtifact.objects.exists())
        self.assertFalse(FileAttachment.objects.exists())

    def test_captured_logo_is_embedded_and_replay_never_refetches_later_brand(self):
        self.business.brand_logo_url = "https://clinic.example.test/original.png"
        self.business.save(update_fields=["brand_logo_url"])
        self.version = fixtures.DocumentTemplateSourceTests.save(self, idempotency_key="logo-document")[0]
        output = BytesIO()
        Image.new("RGB", (80, 40), "#006450").save(output, format="PNG")
        logo = output.getvalue()
        with patch("apps.medical.document_artifact_services.capture_document_logo", return_value=logo) as capture:
            item, _ = self.prepare()
            capture.assert_called_once_with("https://clinic.example.test/original.png")
        self.business.brand_logo_url = "https://clinic.example.test/replacement.png"
        self.business.save(update_fields=["brand_logo_url"])
        with patch("apps.medical.document_artifact_services.capture_document_logo", side_effect=AssertionError("No refetch")):
            replay, repeated = self.prepare()
            other_language, repeated_language = self.prepare(language="kk")
        self.assertTrue(repeated)
        self.assertFalse(repeated_language)
        self.assertEqual(read_document_artifact_manifest(other_language)["logo"], read_document_artifact_manifest(item)["logo"])
        self.assertEqual(replay.pk, item.pk)
        self.assertEqual(base64.b64decode(read_document_artifact_manifest(item)["logo"]), logo)
        with item.attachment.file.open("rb") as source:
            pdf = PdfReader(BytesIO(source.read()))
        self.assertEqual(pdf.pages[0].images[0].image.size, (80, 40))
        self.assertEqual(pdf.pages[0].images[0].image.getpixel((0, 0)), (0, 100, 80))

    def test_corrupt_captured_manifest_blocks_new_language_without_refetch_or_partial_file(self):
        item, _ = self.prepare()
        MedicalDocumentArtifact.objects.filter(pk=item.pk).update(manifest_encrypted="corrupt")
        with patch("apps.medical.document_artifact_services.capture_document_logo", side_effect=AssertionError("No refetch")):
            with self.assertRaises(MedicalDataUnavailable):
                self.prepare(language="kk")
        self.assertEqual(MedicalDocumentArtifact.objects.count(), 1)
        self.assertEqual(FileAttachment.objects.count(), 1)
        self.assertEqual(len(self.files()), 1)
