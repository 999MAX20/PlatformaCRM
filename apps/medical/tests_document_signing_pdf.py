from io import BytesIO
from tempfile import TemporaryDirectory
from unittest.mock import patch

from django.test import TestCase, override_settings
from pypdf import PdfReader
from rest_framework.exceptions import PermissionDenied

from apps.businesses.models import RolePermission
from apps.core.domain_errors import InvalidTransition
from . import tests_document_head_review as fixtures
from .audit import MedicalAuditUnavailable
from .document_artifact_content import read_document_artifact_manifest
from .document_artifact_services import prepare_document_draft_pdf, prepare_document_signing_pdf
from .identity_crypto import MedicalDataUnavailable
from .models import MedicalDocumentArtifact
from .tests_patient_services import key


@override_settings(MEDICAL_DATA_KEYS={"test": key(7)}, MEDICAL_DATA_ACTIVE_KEY_ID="test",
                   MEDICAL_IDENTITY_INDEX_KEY=key(8), USE_S3=False)
class DocumentSigningPDFTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        fixtures.DocumentHeadReviewTests.setUpTestData.__func__(cls)
        RolePermission.objects.create(business_role=cls.role, resource="medical_documents", action="sign",
            scope="own", is_allowed=True)

    def setUp(self):
        directory = TemporaryDirectory(prefix="signing-pdf-")
        self.addCleanup(directory.cleanup)
        settings = override_settings(MEDIA_ROOT=directory.name)
        settings.enable(); self.addCleanup(settings.disable)
        fixtures.DocumentHeadReviewTests.setUp(self)
        self.prepare()

    rules = fixtures.DocumentHeadReviewTests.rules
    save = fixtures.DocumentHeadReviewTests.save
    prepare = fixtures.DocumentHeadReviewTests.prepare
    change = fixtures.DocumentHeadReviewTests.change
    confirm = fixtures.DocumentHeadReviewTests.confirm

    def render(self, service=prepare_document_signing_pdf, **changes):
        return service(**(dict(actor=self.doctor, business_id=self.business.pk, patient_id=self.patient.pk,
            version_id=self.version.pk, appointment_id=self.appointment.pk, language="ru") | changes))

    def complete_reviews(self):
        self.confirm()
        self.change(target="reviewed", expected_state_revision=2, idempotency_key="primary")

    def test_signing_bytes_separate_from_immutable_draft_and_reused(self):
        draft, _ = self.render(prepare_document_draft_pdf)
        self.complete_reviews()
        signing, _ = self.render()
        with draft.attachment.file.open("rb") as source:
            draft_bytes = source.read()
        with signing.attachment.file.open("rb") as source:
            signing_bytes = source.read()
        self.assertIn("Черновик", PdfReader(BytesIO(draft_bytes)).pages[0].extract_text())
        text = PdfReader(BytesIO(signing_bytes)).pages[0].extract_text()
        self.assertNotIn("Черновик", text)
        self.assertIn("Doctor edited synthetic text", text)
        self.assertNotEqual(draft.sha256, signing.sha256)
        self.assertEqual(signing.attachment.scan_status, "pending")
        self.assertEqual(read_document_artifact_manifest(signing)["rendition"], "signing")
        self.assertEqual(read_document_artifact_manifest(draft)["schema"], 1)
        with patch("apps.medical.document_artifact_services.render_signing_pdf", side_effect=AssertionError("Immutable")):
            self.assertEqual(self.render()[0].pk, signing.pk)
        self.assertEqual(self.render(prepare_document_draft_pdf)[0].pk, draft.pk)

    def test_incomplete_review_and_revoked_sign_permission_deny(self):
        with self.assertRaises(InvalidTransition):
            self.render()
        self.complete_reviews(); self.render()
        RolePermission.objects.filter(business_role=self.role, resource="medical_documents", action="sign").update(is_allowed=False)
        with self.assertRaises(PermissionDenied):
            self.render()

    def test_manifest_prevents_relabeling_draft_as_signing(self):
        draft, _ = self.render(prepare_document_draft_pdf)
        MedicalDocumentArtifact.objects.filter(pk=draft.pk).update(rendition="signing")
        with self.assertRaises(MedicalDataUnavailable):
            read_document_artifact_manifest(draft)

    def test_audit_failure_rolls_back_signing_artifact(self):
        self.complete_reviews()
        with patch("apps.medical.document_artifact_services.write_patient_audit", side_effect=MedicalAuditUnavailable):
            with self.assertRaises(MedicalAuditUnavailable):
                self.render()
        self.assertFalse(MedicalDocumentArtifact.objects.exists())
