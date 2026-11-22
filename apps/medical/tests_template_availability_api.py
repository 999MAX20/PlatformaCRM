from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from . import tests_template_search as fixtures
from .tests_patient_services import key


@override_settings(MEDICAL_DATA_KEYS={"test": key(7)}, MEDICAL_DATA_ACTIVE_KEY_ID="test",
                   MEDICAL_IDENTITY_INDEX_KEY=key(8))
class TemplateAvailabilityAPITests(TestCase):
    @classmethod
    def setUpTestData(cls):
        fixtures.TemplateSearchTests.setUpTestData.__func__(cls)

    create = fixtures.TemplateSearchTests.create

    def setUp(self):
        self.version = self.create("availability-api")
        self.client = APIClient()
        self.client.force_authenticate(self.head)
        self.url = f"/api/medical/document-templates/{self.version.template_id}/availability/"
        self.payload = {"business_id": self.business.pk, "is_active": False,
                        "expected_revision": 0, "reason": "Synthetic private reason"}

    def post(self, payload=None, key="pause"):
        return self.client.post(self.url, payload or self.payload, format="json", HTTP_IDEMPOTENCY_KEY=key)

    def test_pause_history_resume_and_private_headers(self):
        result = self.post()
        self.assertEqual(result.status_code, 200, result.data)
        self.assertFalse(result.data["is_active"])
        self.assertEqual(result["Cache-Control"], "no-store, private")
        self.assertTrue(self.post().data["replayed"])
        history = self.client.get(self.url, {"business_id": self.business.pk})
        self.assertEqual(history.status_code, 200, history.data)
        self.assertEqual(history.data["results"][0]["reason"], self.payload["reason"])
        managed = self.client.get("/api/medical/document-templates/managed/",
            {"business_id": self.business.pk, "activity": "inactive", "q": "availability-api"})
        self.assertEqual(managed.status_code, 200, managed.data)
        self.assertEqual(managed.data["results"][0]["availability"], {"is_active": False, "revision": 1})
        self.client.force_authenticate(self.doctor)
        unavailable = self.client.get(f"/api/medical/document-templates/approved/versions/{self.version.pk}/",
            {"business_id": self.business.pk})
        self.assertEqual(unavailable.status_code, 409, unavailable.data)
        self.client.force_authenticate(self.head)
        resumed = self.post(self.payload | {"is_active": True, "expected_revision": 1}, key="resume")
        self.assertEqual(resumed.status_code, 200, resumed.data)
        self.assertTrue(resumed.data["is_active"])

    def test_denial_on_command_history_and_management(self):
        for actor in (self.doctor, self.owner):
            self.client.force_authenticate(actor)
            for result in (self.post(), self.client.get(self.url, {"business_id": self.business.pk}),
                self.client.get("/api/medical/document-templates/managed/", {"business_id": self.business.pk})):
                self.assertEqual(result.status_code, 403, result.data)
                self.assertEqual(result["Cache-Control"], "no-store, private")

    def test_validation_and_conflicts_do_not_change_history(self):
        for override in ({"reason": " "}, {"patient_id": 1}, {"expected_revision": -1}, {"is_active": "invalid"}):
            result = self.post(self.payload | override)
            self.assertEqual(result.status_code, 400, result.data)
        self.assertEqual(self.post(key="").status_code, 400)
        self.assertEqual(self.post().status_code, 200)
        self.assertEqual(self.post(key="stale").status_code, 409)
        self.assertEqual(self.post(self.payload | {"reason": "Different"}).status_code, 409)
        history = self.client.get(self.url, {"business_id": self.business.pk})
        self.assertEqual(history.data["revision"], 1)
        self.assertEqual(len(history.data["results"]), 1)
