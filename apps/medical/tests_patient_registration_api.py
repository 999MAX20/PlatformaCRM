from unittest.mock import patch

from django.db import DatabaseError
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from apps.clients.models import Client
from apps.medical.models import MedicalAuditEvent, PatientProfile
from . import tests_patient_registration as registration_fixtures
from . import tests_patient_services as fixtures


@override_settings(MEDICAL_DATA_KEYS={"test": fixtures.key(7)}, MEDICAL_DATA_ACTIVE_KEY_ID="test",
                   MEDICAL_IDENTITY_INDEX_KEY=fixtures.key(8))
class PatientRegistrationAPITests(TestCase):
    @classmethod
    def setUpTestData(cls):
        registration_fixtures.PatientRegistrationTests.setUpTestData.__func__(cls)

    def setUp(self):
        registration_fixtures.PatientRegistrationTests.setUp(self)
        self.api = APIClient(); self.api.force_authenticate(self.reception)
        self.url = "/api/medical/patients/register/"
        self.payload = {"business_id": self.business.pk, "branch_id": self.branch.pk,
            "full_name": "Synthetic registered person", "phone": "+77000000009", "email": "",
            "demographics": {}, "iin": None}

    def register(self, **data):
        return self.api.post(self.url, {**self.payload, **data}, format="json", HTTP_IDEMPOTENCY_KEY="api-registration")

    def test_register_and_replay_return_existing_ids_without_private_payload(self):
        response = self.register()
        self.assertEqual(response.status_code, 201, response.data)
        self.assertIn("no-store", response["Cache-Control"])
        self.assertNotIn("full_name", response.data)
        replay = self.register()
        self.assertEqual(replay.status_code, 200)
        self.assertTrue(replay.data["replayed"])
        self.assertEqual(replay.data["id"], response.data["id"])
        self.assertEqual(Client.objects.filter(full_name=self.payload["full_name"]).count(), 1)

    def test_possible_contact_match_requires_confirmed_choice(self):
        response = self.register(phone=self.patient_client.phone)
        self.assertEqual(response.status_code, 409, response.data)
        self.assertEqual(response.data["code"], "patient_matches_require_review")
        self.assertNotIn(self.patient_client.full_name, str(response.data))
        self.assertEqual(self.register(phone=self.patient_client.phone, confirmed_separate_person=True).status_code, 201)

    def test_medical_and_core_role_denial_record_no_person_data(self):
        self.api.force_authenticate(self.owner)
        self.assertEqual(self.register().status_code, 403)
        self.assertTrue(MedicalAuditEvent.objects.filter(actor=self.owner, patient__isnull=True, action="access_denied").exists())
        self.api.force_authenticate(self.reception)
        self.member.role = "specialist"; self.member.save(update_fields=["role"])
        self.assertEqual(self.register().status_code, 403)

    def test_audit_failure_and_bad_fields_do_not_create_half_a_patient(self):
        before = (Client.objects.count(), PatientProfile.objects.count())
        self.assertEqual(self.register(verified_by=self.owner.pk).status_code, 400)
        with patch("apps.medical.audit.MedicalAuditEvent.objects.create", side_effect=DatabaseError("synthetic")):
            self.assertEqual(self.register().status_code, 503)
        self.assertEqual((Client.objects.count(), PatientProfile.objects.count()), before)
