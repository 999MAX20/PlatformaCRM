from django.test import TestCase, override_settings
from unittest.mock import patch
from rest_framework.test import APIClient

from . import tests_patient_services as crypto_fixtures
from . import tests_correction_access as fixtures
from .models import MedicalCorrectionAccess


@override_settings(MEDICAL_DATA_KEYS={"test": crypto_fixtures.key(7)}, MEDICAL_DATA_ACTIVE_KEY_ID="test",
                   MEDICAL_IDENTITY_INDEX_KEY=crypto_fixtures.key(8))
class CorrectionAccessAPITests(TestCase):
    @classmethod
    def setUpTestData(cls):
        fixtures.CorrectionAccessTests.setUpTestData.__func__(cls)

    def setUp(self):
        self.api = APIClient()
        self.api.force_authenticate(self.doctor)
        self.url = "/api/medical/correction-access/"
        self.body = dict(business_id=self.business.pk, encounter_id=self.encounter_record.pk,
            expected_patient_revision=self.patient.revision, expected_target_revision=1, reason="Synthetic request")

    def test_request_review_list_and_close_round_trip(self):
        response = self.api.post(self.url, self.body, format="json", HTTP_IDEMPOTENCY_KEY="request")
        self.assertEqual(response.status_code, 201, response.data)
        request_id = response.data["id"]
        self.assertEqual(response["Cache-Control"], "no-store, private")
        scope = dict(business_id=self.business.pk, branch_id=self.first.pk, client_id=self.patient.client_id)
        response = self.api.get(self.url, scope)
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data["results"][0]["id"], request_id)
        self.api.force_authenticate(self.head)
        response = self.api.post(f"{self.url}{request_id}/review/", dict(business_id=self.business.pk,
            expected_revision=1, decision="approve", reason="Synthetic decision"), format="json", HTTP_IDEMPOTENCY_KEY="review")
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data["state"], "active")
        self.api.force_authenticate(self.doctor)
        response = self.api.post(f"{self.url}{request_id}/close/", dict(business_id=self.business.pk,
            expected_revision=2, decision="complete", reason="Synthetic completed"), format="json", HTTP_IDEMPOTENCY_KEY="close")
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data["state"], "completed")

    def test_strict_body_idempotency_and_owner_denial(self):
        for body in (self.body | {"expires_at": "2099-01-01"}, self.body | {"reason": ""}):
            response = self.api.post(self.url, body, format="json", HTTP_IDEMPOTENCY_KEY="invalid")
            self.assertEqual(response.status_code, 400, response.data)
        self.assertEqual(self.api.post(self.url, self.body, format="json").status_code, 400)
        self.api.force_authenticate(self.owner)
        response = self.api.post(self.url, self.body, format="json", HTTP_IDEMPOTENCY_KEY="owner")
        self.assertEqual(response.status_code, 403, response.data)
        self.assertEqual(response["Cache-Control"], "no-store, private")
        self.assertFalse(MedicalCorrectionAccess.objects.exists())

    def test_target_metadata_never_contains_clinical_text_and_revocation_denies(self):
        scope = dict(business_id=self.business.pk, branch_id=self.first.pk, client_id=self.patient.client_id)
        response = self.api.get(self.url + "targets/", scope)
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data["results"][0]["encounter_id"], self.encounter_record.pk)
        self.assertNotIn("clinical", str(response.data))
        self.assignment.branches.clear()
        response = self.api.get(self.url + "targets/", scope)
        self.assertEqual(response.status_code, 403, response.data)

    def test_expired_target_is_denied_and_expiry_audit_survives_denied_response(self):
        item = fixtures.CorrectionAccessTests.request(self)[0]
        item = fixtures.CorrectionAccessTests.review(self, item)[0]
        with patch("apps.medical.correction_access_context.timezone.now", return_value=item.expires_at):
            response = self.api.get(f"{self.url}{item.pk}/target/", {"business_id": self.business.pk})
        self.assertEqual(response.status_code, 403, response.data)
        item.refresh_from_db()
        self.assertEqual(item.state, "expired")

    def test_save_route_reuses_existing_draft_writer_and_rejects_extra_fields(self):
        from .tests_encounter_services import PrimaryEncounterDraftTests
        PrimaryEncounterDraftTests.setUp(self)
        item = fixtures.CorrectionAccessTests.request(self)[0]
        item = fixtures.CorrectionAccessTests.review(self, item)[0]
        body = dict(business_id=self.business.pk, expected_revision=1, reason="Synthetic API correction", content={"plan": "Synthetic plan"})
        response = self.api.post(f"{self.url}{item.pk}/save-draft/", body | {"expires_at": "2099"}, format="json", HTTP_IDEMPOTENCY_KEY="save")
        self.assertEqual(response.status_code, 400, response.data)
        response = self.api.post(f"{self.url}{item.pk}/save-draft/", body, format="json", HTTP_IDEMPOTENCY_KEY="save")
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data["revision"], 2)
