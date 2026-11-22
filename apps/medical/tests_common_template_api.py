from unittest.mock import patch

from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from apps.businesses.models import RolePermission
from . import tests_common_templates as fixtures
from . import tests_patient_services as crypto_fixtures
from .audit import MedicalAuditUnavailable
from .models import MedicalDocumentTemplateRevision


@override_settings(MEDICAL_DATA_KEYS={"test": crypto_fixtures.key(7)}, MEDICAL_DATA_ACTIVE_KEY_ID="test",
                   MEDICAL_IDENTITY_INDEX_KEY=crypto_fixtures.key(8))
class CommonTemplateAPITests(TestCase):
    @classmethod
    def setUpTestData(cls):
        fixtures.CommonTemplateTests.setUpTestData.__func__(cls)

    def setUp(self):
        self.api = APIClient()
        self.api.force_authenticate(self.head)
        self.root = "/api/medical/document-templates/"
        self.scope = {"business_id": self.business.pk}

    def request(self, path, payload=None, key="command"):
        if payload is None:
            response = self.api.get(self.root + path, self.scope)
        else:
            response = self.api.post(self.root + path, self.scope | payload,
                                     format="json", HTTP_IDEMPOTENCY_KEY=key)
        self.assertEqual(response["Cache-Control"], "no-store, private")
        self.assertEqual(response["Pragma"], "no-cache")
        return response

    def create(self):
        response = self.request("common/", {"title": "Synthetic common", "text": "Synthetic text"})
        self.assertEqual(response.status_code, 201, response.data)
        return response.data

    def test_head_management_and_explicit_approval_for_doctor(self):
        access = self.request("common/workspace-access/")
        self.assertEqual(access.status_code, 200, access.data)
        self.assertEqual(access.data["actions"], dict(view=True, create=True, update=True, approve=True))
        draft = self.create()
        version = draft["version_id"]
        self.assertEqual(self.request("common/").data["results"][0]["version_id"], version)
        self.assertEqual(self.request(f"common/{draft['id']}/revisions/").status_code, 200)
        self.assertEqual(self.request(f"common/versions/{version}/").data["template"]["text"], "Synthetic text")
        self.api.force_authenticate(self.doctor)
        self.assertEqual(self.request("approved/").data["results"], [])
        self.assertEqual(self.request(f"approved/versions/{version}/").status_code, 403)
        self.api.force_authenticate(self.head)
        self.assertEqual(self.request(f"common/versions/{version}/submit/", {}, "submit").status_code, 200)
        self.assertEqual(self.request(f"versions/{version}/decision/", {"decision": "approved"}, "approve").status_code, 200)
        self.api.force_authenticate(self.doctor)
        self.assertEqual(self.request("approved/").data["results"][0]["version_id"], version)
        self.assertEqual(self.request(f"approved/versions/{version}/").data["review"]["state"], "approved")
        self.assertEqual(self.request(f"common/versions/{version}/").status_code, 403)

    def test_draft_update_replay_stale_and_history(self):
        draft = self.create()
        payload = {"title": "Changed", "text": "New text", "expected_revision": 1}
        path = f"common/{draft['id']}/draft/"
        response = self.request(path, payload, "update")
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data["revision"], 2)
        self.assertTrue(self.request(path, payload, "update").data["replayed"])
        self.assertEqual(self.request(path, payload, "stale").status_code, 409)
        self.assertEqual(self.request(path, payload | {"text": "Other"}, "update").status_code, 409)
        history = self.request(f"common/{draft['id']}/revisions/")
        self.assertEqual([row["revision"] for row in history.data["results"]], [2, 1])

    def test_owner_and_doctor_cannot_manage_common(self):
        draft = self.create()
        for actor in (self.owner, self.doctor):
            self.api.force_authenticate(actor)
            for path in ("common/", "common/workspace-access/",
                         f"common/{draft['id']}/revisions/", f"common/versions/{draft['version_id']}/"):
                self.assertEqual(self.request(path).status_code, 403)
            self.assertEqual(self.request("common/", {"title": "Forbidden", "text": ""}, "denied").status_code, 403)
            self.assertEqual(self.request(f"common/versions/{draft['version_id']}/submit/", {}).status_code, 403)

    def test_strict_commands_and_current_permissions(self):
        for field in ("owner_member_id", "state", "approved"):
            response = self.request("common/", {"title": "Invalid", "text": "", field: "approved"})
            self.assertEqual(response.status_code, 400)
        self.assertEqual(self.request("common/", {"title": "Invalid", "text": ""}, "").status_code, 400)
        draft = self.create()
        RolePermission.objects.filter(business_role=self.head_role, resource="medical_documents",
                                      action="update").update(is_allowed=False)
        self.assertFalse(self.request("common/workspace-access/").data["actions"]["update"])
        self.assertEqual(self.request(f"common/{draft['id']}/draft/",
            {"title": "Denied", "text": "", "expected_revision": 1}, "update").status_code, 403)

    def test_audit_failure_rolls_back_creation(self):
        with patch("apps.medical.template_services.write_template_audit", side_effect=MedicalAuditUnavailable):
            response = self.request("common/", {"title": "Synthetic", "text": ""})
        self.assertEqual(response.status_code, 503)
        self.assertFalse(MedicalDocumentTemplateRevision.objects.exists())
        self.create()
