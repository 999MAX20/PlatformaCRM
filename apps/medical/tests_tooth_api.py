from unittest.mock import patch

from django.db import DatabaseError
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from .tests_tooth_services import PrimaryToothObservationTests
from .tests_patient_services import key
from .models import DentalToothHistory, MedicalAuditEvent


@override_settings(MEDICAL_DATA_KEYS={"test": key(7)}, MEDICAL_DATA_ACTIVE_KEY_ID="test",
                   MEDICAL_IDENTITY_INDEX_KEY=key(8), MEDICAL_TOOTH_SURFACE_POLICIES="")
class ToothObservationAPITests(TestCase):
    @classmethod
    def setUpTestData(cls):
        PrimaryToothObservationTests.setUpTestData.__func__(cls)

    def setUp(self):
        self.api = APIClient()
        self.api.force_authenticate(self.doctor)
        self.url = "/api/medical/tooth-observations/"
        self.scope = {"business_id": self.business.pk, "patient_id": self.patient.pk}
        self.payload = {**self.scope, "encounter_id": self.encounter_record.pk, "tooth": 11,
            "expected_patient_revision": 1, "expected_encounter_revision": 1,
            "expected_tooth_revision": 0, "observation": "  Synthetic private observation\n"}

    def save(self, token="tooth-api", **overrides):
        return self.api.post(self.url, self.payload | overrides, format="json", HTTP_IDEMPOTENCY_KEY=token)

    def read(self, identifier, **overrides):
        return self.api.get(f"{self.url}{identifier}/", {**self.scope,
            "appointment_id": self.appointment.pk} | overrides)

    def private(self, response):
        self.assertEqual(response["Cache-Control"], "no-store, private")
        self.assertEqual(response["Pragma"], "no-cache")

    def test_create_replay_and_read_historical_content(self):
        saved = self.save()
        self.assertEqual(saved.status_code, 201, saved.data)
        self.private(saved)
        self.assertNotIn("observation", saved.data)
        replay = self.save()
        self.assertEqual(replay.status_code, 200, replay.data)
        self.assertTrue(replay.data["replayed"])
        second = self.save(token="next", expected_tooth_revision=1, observation="Later")
        self.assertEqual(second.status_code, 201, second.data)
        old = self.read(saved.data["history_id"])
        self.assertEqual(old.status_code, 200, old.data)
        self.private(old)
        self.assertEqual(old.data["observation"], self.payload["observation"])
        self.assertEqual(MedicalAuditEvent.objects.count(), 3)

    def test_stale_and_changed_payload_conflicts(self):
        self.save()
        for response in (self.save(observation="Changed"), self.save(token="stale")):
            self.assertEqual(response.status_code, 409, response.data)
            self.private(response)
        self.assertEqual(DentalToothHistory.objects.count(), 1)

    def test_state_only_save_and_historical_read(self):
        first = self.save(tooth_status="absent", observation="")
        self.assertEqual(first.status_code, 201, first.data)
        second = self.save(token="state-next", expected_tooth_revision=1,
            tooth_status="not_examined", observation="")
        self.assertEqual(second.status_code, 201, second.data)
        self.assertEqual(self.read(first.data["history_id"]).data["tooth_status"], "absent")
        snapshot = self.api.get(f"{self.url}snapshot/", {**self.scope, "appointment_id": self.appointment.pk})
        self.assertEqual(snapshot.data["observations"][0]["tooth_status"], "not_examined")
        self.assertEqual(self.save(token="invalid", tooth_status="healthy").status_code, 400)

    def test_strict_validation_and_missing_key(self):
        for change in ({"author_id": self.owner.pk}, {"tooth": 19}, {"observation": ""},
                       {"expected_tooth_revision": -1}):
            response = self.save(**change)
            self.assertEqual(response.status_code, 400, response.data)
            self.private(response)
        response = self.api.post(self.url, self.payload, format="json")
        self.assertEqual(response.status_code, 400, response.data)
        self.assertFalse(DentalToothHistory.objects.exists())

    def test_anonymous_and_owner_denied(self):
        saved = self.save()
        for actor in (None, self.owner):
            self.api.force_authenticate(actor)
            for response in (self.read(saved.data["history_id"]), self.save()):
                self.assertIn(response.status_code, (401, 403), response.data)
                self.private(response)

    def test_revocation_blocks_read_and_replay(self):
        saved = self.save()
        self.assignment.revoked_at = timezone.now()
        self.assignment.save(update_fields=["revoked_at"])
        for response in (self.read(saved.data["history_id"]), self.save()):
            self.assertEqual(response.status_code, 403, response.data)
            self.private(response)

    def test_unknown_history_and_foreign_scope_denied(self):
        response = self.read(999999)
        self.assertEqual(response.status_code, 403, response.data)
        response = self.read(999999, business_id=999999)
        self.assertIn(response.status_code, (403, 404), response.data)
        self.private(response)

    def test_audit_failure_rolls_back_write_and_prevents_read(self):
        with patch("apps.medical.audit.MedicalAuditEvent.objects.create", side_effect=DatabaseError):
            response = self.save()
        self.assertEqual(response.status_code, 503, response.data)
        self.private(response)
        self.assertFalse(DentalToothHistory.objects.exists())
        saved = self.save()
        with patch("apps.medical.audit.MedicalAuditEvent.objects.create", side_effect=DatabaseError):
            response = self.read(saved.data["history_id"])
        self.assertEqual(response.status_code, 503, response.data)
        self.private(response)
        self.assertNotIn("Synthetic private", response.content.decode())
