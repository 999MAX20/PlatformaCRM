from io import BytesIO
from unittest.mock import patch

from django.test import TestCase, override_settings
from django.utils import timezone
from pypdf import PdfReader
from rest_framework.test import APIClient

from apps.core.models import FileAttachment
from apps.businesses.models import RolePermission
from . import tests_document_artifact_generation as fixtures
from . import tests_patient_services as crypto
from .audit import MedicalAuditUnavailable
from .models import MedicalAuditEvent, MedicalRoleAssignment


@override_settings(MEDICAL_DATA_KEYS={"test": crypto.key(7)}, MEDICAL_DATA_ACTIVE_KEY_ID="test",
                   MEDICAL_IDENTITY_INDEX_KEY=crypto.key(8), USE_S3=False)
class DocumentArtifactAPITests(TestCase):
    @classmethod
    def setUpTestData(cls):
        fixtures.DocumentArtifactGenerationTests.setUpTestData.__func__(cls)

    def setUp(self):
        fixtures.DocumentArtifactGenerationTests.setUp(self)
        self.api = APIClient()
        self.api.force_authenticate(self.doctor)
        self.path = f"/api/medical/documents/versions/{self.version.pk}/"
        self.scope = {"business_id": self.business.pk, "patient_id": self.patient.pk,
                      "appointment_id": self.appointment.pk, "language": "ru"}

    def prepare(self, **changes):
        return self.api.post(self.path + "pdf-prepare/", self.scope | changes, format="json")

    def test_export_and_print_are_explicit_private_operations_with_current_export_right(self):
        created = self.prepare()
        from .models import MedicalDocumentArtifact
        item = MedicalDocumentArtifact.objects.get(pk=created.data["artifact_id"])
        RolePermission.objects.update_or_create(business_role=self.role, resource="medical_documents", action="export",
            defaults={"scope": "business", "is_allowed": True})
        for endpoint in ("pdf-download/", "pdf-print/"):
            self.assertEqual(self.api.post(self.path + endpoint, self.scope, format="json").status_code, 423)
        FileAttachment.objects.filter(pk=item.attachment_id).update(scan_status="clean", scan_sha256=item.sha256)
        expected = self.api.get(self.path + "pdf/", self.scope).content
        for endpoint, disposition, event in (("pdf-download/", "attachment", "document_exported"),
                                             ("pdf-print/", "inline", "document_print_requested")):
            response = self.api.post(self.path + endpoint, self.scope, format="json")
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.content, expected)
            self.assertEqual(response["Cache-Control"], "no-store, private")
            self.assertTrue(response["Content-Disposition"].startswith(disposition))
            self.assertTrue(MedicalAuditEvent.objects.filter(action=event, document_version=self.version).exists())
        RolePermission.objects.filter(business_role=self.role, resource="medical_documents", action="export").update(is_allowed=False)
        self.assertFalse(self.prepare().data["can_export"])
        for endpoint in ("pdf-download/", "pdf-print/"):
            self.assertEqual(self.api.post(self.path + endpoint, self.scope, format="json").status_code, 403)
        self.assertEqual(self.api.get(self.path + "pdf/", self.scope).status_code, 200)

    def test_prepare_retry_quarantine_and_private_pdf_response(self):
        created = self.prepare()
        self.assertEqual(created.status_code, 201, created.data)
        self.assertEqual(created.data["scan_status"], "pending")
        replay = self.prepare()
        self.assertEqual(replay.status_code, 200, replay.data)
        self.assertTrue(replay.data["replayed"])
        self.assertEqual(self.api.get(self.path + "pdf/", self.scope).status_code, 423)
        from .models import MedicalDocumentArtifact
        item = MedicalDocumentArtifact.objects.get(pk=created.data["artifact_id"])
        FileAttachment.objects.filter(pk=item.attachment_id).update(scan_status="clean", scan_sha256=item.sha256)
        response = self.api.get(self.path + "pdf/", self.scope)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/pdf")
        self.assertEqual(response["Cache-Control"], "no-store, private")
        self.assertEqual(response["Pragma"], "no-cache")
        self.assertEqual(response["X-Content-Type-Options"], "nosniff")
        self.assertIn("sandbox", response["Content-Security-Policy"])
        self.assertEqual(response["Content-Disposition"], 'inline; filename="document.pdf"')
        self.assertIn("Doctor edited synthetic text", PdfReader(BytesIO(response.content)).pages[0].extract_text())
        self.assertNotIn("url", created.data)

    def test_unknown_fields_missing_language_and_ambiguous_basis_fail(self):
        for changes in ({"download": True}, {"language": "xx"}, {"head_branch_id": self.first.pk}, {"action": "export"}):
            with self.subTest(changes=changes):
                self.assertEqual(self.prepare(**changes).status_code, 400)
        scope = self.scope.copy()
        del scope["language"]
        self.assertEqual(self.api.post(self.path + "pdf-prepare/", scope, format="json").status_code, 400)
        self.assertFalse(FileAttachment.objects.exists())

    def test_revoked_role_blocks_generation_and_preview_and_records_denial(self):
        self.assertEqual(self.prepare().status_code, 201)
        MedicalRoleAssignment.objects.filter(pk=self.assignment.pk).update(revoked_at=timezone.now())
        with patch("apps.medical.document_artifact_services.open_clean_attachment", side_effect=AssertionError("No storage read")):
            self.assertEqual(self.prepare().status_code, 403)
            self.assertEqual(self.api.get(self.path + "pdf/", self.scope).status_code, 403)
        self.assertEqual(MedicalAuditEvent.objects.filter(action="access_denied", business=self.business).count(), 2)

    def test_audit_failure_is_safe_unavailable_and_cleans_generated_blob(self):
        with patch("apps.medical.document_artifact_services.write_patient_audit", side_effect=MedicalAuditUnavailable):
            response = self.prepare()
        self.assertEqual(response.status_code, 503, response.data)
        self.assertFalse(FileAttachment.objects.exists())
        self.assertNotIn("Doctor edited", str(response.data))
