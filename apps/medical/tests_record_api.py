from unittest.mock import patch

from django.db import DatabaseError
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from . import tests_record_services as fixtures
from . import tests_patient_services as crypto_fixtures
from .models import DentalMedicalRecord, MedicalAuditEvent


@override_settings(MEDICAL_DATA_KEYS={"test": crypto_fixtures.key(7)}, MEDICAL_DATA_ACTIVE_KEY_ID="test",
                   MEDICAL_IDENTITY_INDEX_KEY=crypto_fixtures.key(8))
class DentalRecordAPITests(TestCase):
    @classmethod
    def setUpTestData(cls):
        fixtures.DentalRecordOpeningTests.setUpTestData.__func__(cls)

    def setUp(self):
        self.api = APIClient()
        self.api.force_authenticate(self.doctor)
        self.url = "/api/medical/records/"
        self.payload = {"business_id": self.business.pk, "patient_id": self.patient.pk,
            "number": "API-LOCAL-001", "expected_patient_revision": 1, "appointment_id": self.appointment.pk}

    def post(self, **overrides):
        return self.api.post(self.url, self.payload | overrides, format="json", HTTP_IDEMPOTENCY_KEY="record-api")

    def test_record_then_first_encounter_reuses_same_patient_and_chart(self):
        record = self.post()
        self.assertEqual(record.status_code, 201, record.data)
        self.assertEqual(record["Cache-Control"], "no-store, private")
        replay = self.post()
        self.assertEqual(replay.status_code, 200, replay.data)
        self.assertTrue(replay.data["replayed"])
        self.assertEqual(replay.data["id"], record.data["id"])
        encounter = self.api.post("/api/medical/encounters/", {
            "business_id": self.business.pk, "patient_id": self.patient.pk, "record_id": record.data["id"],
            "appointment_id": self.appointment.pk, "expected_patient_revision": 1,
            "expected_appointment_updated_at": self.appointment.updated_at.isoformat()},
            format="json", HTTP_IDEMPOTENCY_KEY="first-encounter")
        self.assertEqual(encounter.status_code, 201, encounter.data)
        self.assertEqual(DentalMedicalRecord.objects.count(), 1)
        self.assertEqual(MedicalAuditEvent.objects.count(), 2)

    def test_errors_are_private_and_audit_failure_rolls_back(self):
        invalid = self.post(author_id=self.owner.pk)
        self.assertEqual(invalid.status_code, 400, invalid.data)
        self.assertEqual(invalid["Cache-Control"], "no-store, private")
        with patch("apps.medical.audit.MedicalAuditEvent.objects.create", side_effect=DatabaseError("synthetic")):
            failed = self.post()
        self.assertEqual(failed.status_code, 503, failed.data)
        self.assertEqual(failed["Cache-Control"], "no-store, private")
        self.assertFalse(DentalMedicalRecord.objects.exists())
        self.api.force_authenticate(self.owner)
        denied = self.post()
        self.assertEqual(denied.status_code, 403, denied.data)
        self.assertEqual(denied["Cache-Control"], "no-store, private")
