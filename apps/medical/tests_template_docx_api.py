from unittest.mock import patch

from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from apps.core.antivirus import ScanUnavailable
from apps.core.models import AuditLog
from apps.businesses.models import RolePermission
from . import tests_template_docx as fixtures
from .tests_patient_services import key


@override_settings(MEDICAL_DATA_KEYS={"test": key(7)}, MEDICAL_DATA_ACTIVE_KEY_ID="test",
                   MEDICAL_IDENTITY_INDEX_KEY=key(8))
class TemplateDocxAPITests(TestCase):
    @classmethod
    def setUpTestData(cls):
        fixtures.TemplateDocxTests.setUpTestData.__func__(cls)

    save = fixtures.TemplateDocxTests.save
    configure = fixtures.TemplateDocxTests.configure

    def setUp(self):
        fixtures.TemplateDocxTests.setUp(self)
        self.api = APIClient()
        self.api.force_authenticate(self.head)
        self.url = f"/api/medical/document-templates/versions/{self.version.pk}/docx-download/"
        self.scope = {"business_id": self.business.pk, "language": "ru"}

    def post(self, **changes):
        response = self.api.post(self.url, self.scope | changes, format="json")
        self.assertEqual(response["Cache-Control"], "no-store, private")
        self.assertEqual(response["Pragma"], "no-cache")
        return response

    @patch("apps.medical.template_docx.scan_stream", side_effect=fixtures.clean)
    def test_download_is_private_attachment_and_strict_request(self, scanner):
        response = self.post()
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.content.startswith(b"PK"))
        self.assertIn("wordprocessingml.document", response["Content-Type"])
        self.assertEqual(response["Content-Disposition"], 'attachment; filename="template-draft.docx"')
        self.assertEqual(response["X-Content-Type-Options"], "nosniff")
        self.assertEqual(response["Content-Security-Policy"], "sandbox")
        for payload in ({"language": "bad"}, {"patient_id": 1}, {"business_id": 0}):
            self.assertEqual(self.post(**payload).status_code, 400)
        self.assertEqual(scanner.call_count, 1)

    def test_denial_and_scanner_recovery_never_return_unchecked_bytes(self):
        with patch("apps.medical.template_docx.scan_stream", side_effect=ScanUnavailable()):
            self.assertEqual(self.post().status_code, 503)
        self.assertFalse(AuditLog.objects.filter(entity_type="medical_template_version").exists())
        with patch("apps.medical.template_docx.scan_stream", side_effect=fixtures.clean) as scanner:
            for actor in (None, self.owner, self.doctor):
                self.api.force_authenticate(actor)
                self.assertIn(self.post().status_code, (401, 403))
            scanner.assert_not_called()
            self.api.force_authenticate(self.head)
            self.assertEqual(self.post().status_code, 200)

    @patch("apps.medical.template_docx.scan_stream")
    def test_access_distinguishes_no_export_from_no_view_without_rendering(self, scanner):
        url = self.url.replace("docx-download/", "docx-access/")
        scope = {"business_id": self.business.pk}
        def read():
            response = self.api.get(url, scope)
            self.assertEqual(response["Cache-Control"], "no-store, private")
            return response
        self.assertEqual(read().data, {"can_docx": True})
        RolePermission.objects.filter(business_role=self.head_role, action="export").update(is_allowed=False)
        self.assertEqual(read().data, {"can_docx": False})
        RolePermission.objects.filter(business_role=self.head_role, action="view").update(is_allowed=False)
        self.assertEqual(read().status_code, 403)
        self.api.force_authenticate(self.owner)
        self.assertEqual(read().status_code, 403)
        scanner.assert_not_called()
