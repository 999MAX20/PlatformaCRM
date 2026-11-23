from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from apps.businesses.models import RolePermission
from .document_artifact_services import DOCX_CONTENT_TYPE
from .models import MedicalDocumentArtifact
from . import tests_document_docx_export as fixtures
from .tests_patient_services import key


@override_settings(MEDICAL_DATA_KEYS={"test": key(7)}, MEDICAL_DATA_ACTIVE_KEY_ID="test",
                   MEDICAL_IDENTITY_INDEX_KEY=key(8), USE_S3=False)
class DocumentDOCXAPITests(TestCase):
    @classmethod
    def setUpTestData(cls):
        fixtures.DocumentDOCXExportTests.setUpTestData.__func__(cls)

    def setUp(self):
        fixtures.DocumentDOCXExportTests.setUp(self)
        self.api = APIClient()
        self.api.force_authenticate(self.doctor)
        self.path = f"/api/medical/documents/versions/{self.version.pk}/"
        self.body = {k: v for k, v in self.scope.items() if k not in {"actor", "version_id"}}

    def test_private_prepare_quarantine_download_and_current_permission(self):
        pdf = self.api.post(self.path + "pdf-prepare/", self.body, format="json")
        self.assertEqual(pdf.status_code, 201, pdf.data)
        self.assertTrue(pdf.data["can_docx"])
        created = self.api.post(self.path + "docx-prepare/", self.body, format="json")
        self.assertEqual(created.status_code, 201, created.data)
        self.assertEqual(self.api.post(self.path + "docx-prepare/", self.body, format="json").status_code, 200)
        self.assertEqual(self.api.post(self.path + "docx-download/", self.body, format="json").status_code, 423)
        item = MedicalDocumentArtifact.objects.get(pk=created.data["artifact_id"])
        expected = fixtures.DocumentDOCXExportTests.clean(self, item)
        response = self.api.post(self.path + "docx-download/", self.body, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, expected)
        self.assertEqual(response["Content-Type"], DOCX_CONTENT_TYPE)
        self.assertEqual(response["Content-Disposition"], 'attachment; filename="document.docx"')
        self.assertEqual(response["Cache-Control"], "no-store, private")
        self.assertEqual(response["X-Content-Type-Options"], "nosniff")
        RolePermission.objects.filter(business_role=self.role, resource="medical_documents", action="export").update(is_allowed=False)
        for endpoint in ("docx-prepare/", "docx-download/"):
            denied = self.api.post(self.path + endpoint, self.body, format="json")
            self.assertEqual(denied.status_code, 403)
            self.assertEqual(denied["Cache-Control"], "no-store, private")
        self.assertFalse(self.api.post(self.path + "pdf-prepare/", self.body, format="json").data["can_docx"])

    def test_strict_requests_no_get_download_and_no_legacy_permission(self):
        self.assertEqual(self.api.post(self.path + "docx-prepare/", self.body | {"unknown": True}, format="json").status_code, 400)
        self.assertEqual(self.api.get(self.path + "docx-download/", self.body).status_code, 405)
        legacy = f"/api/medical/documents/versions/{self.legacy.pk}/"
        self.assertFalse(self.api.post(legacy + "pdf-prepare/", self.body, format="json").data["can_docx"])
        self.assertEqual(self.api.post(legacy + "docx-prepare/", self.body, format="json").status_code, 403)
        self.api.force_authenticate(None)
        self.assertEqual(self.api.post(self.path + "docx-prepare/", self.body, format="json").status_code, 401)
