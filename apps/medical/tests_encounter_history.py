from unittest.mock import patch

from django.db import DatabaseError
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from apps.clients.models import Client
from apps.scheduling.models import Appointment
from . import tests_encounter_content as fixtures
from . import tests_patient_services as crypto_fixtures
from .models import DentalMedicalRecord, MedicalAuditEvent, MedicalEncounter, PatientProfile


@override_settings(MEDICAL_DATA_KEYS={"test": crypto_fixtures.key(7)}, MEDICAL_DATA_ACTIVE_KEY_ID="test")
class EncounterHistoryAPITests(TestCase):
    @classmethod
    def setUpTestData(cls):
        fixtures.EncounterContentTests.setUpTestData.__func__(cls)

    append = fixtures.EncounterContentTests.append
    advance = fixtures.EncounterContentTests.advance

    def setUp(self):
        self.first_version = self.append()
        self.advance()
        self.second_version = self.append(author=self.owner, content={"plan": "New synthetic plan"})
        self.api = APIClient()
        self.api.force_authenticate(self.doctor)
        self.scope = {"business_id": self.business.pk, "patient_id": self.patient.pk, "appointment_id": self.appointment.pk}
        self.url = f"/api/medical/encounters/{self.encounter_record.pk}/revisions/"

    def read(self, **overrides):
        return self.api.get(self.url, self.scope | overrides)

    def test_history_lists_exact_authors_and_can_read_selected_old_version(self):
        self.doctor.full_name = "Original clinician"
        self.doctor.save(update_fields=["full_name"])
        self.owner.full_name = "Later author"
        self.owner.save(update_fields=["full_name"])
        with patch("apps.medical.encounter_reads.read_encounter_revision") as decrypt:
            response = self.read()
            decrypt.assert_not_called()
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response["Cache-Control"], "no-store, private")
        self.assertEqual([row["revision"] for row in response.data["versions"]], [2, 1])
        self.assertEqual([row["author_id"] for row in response.data["versions"]], [self.owner.pk, self.doctor.pk])
        self.assertEqual([row["author_name"] for row in response.data["versions"]], ["Later author", "Original clinician"])
        self.assertNotIn("New synthetic plan", response.content.decode())
        self.assertEqual(MedicalAuditEvent.objects.count(), 2)
        old_id = response.data["versions"][1]["version_id"]
        old = self.api.get(f"/api/medical/encounters/versions/{old_id}/", self.scope)
        self.assertEqual(old.status_code, 200, old.data)
        self.assertEqual(old.data["author_name"], "Original clinician")
        self.assertEqual(old.data["content"]["plan"], "Оқу жоспары")

    def test_cursor_survives_new_revision_without_repeating_previous_page(self):
        first = self.read(limit=1)
        self.assertEqual(first.data["next_before_revision"], 2)
        self.advance()
        self.append(content={"plan": "Newest"})
        second = self.read(limit=1, before_revision=first.data["next_before_revision"])
        self.assertEqual(second.data["current_revision"], 3)
        self.assertEqual([row["revision"] for row in second.data["versions"]], [1])
        self.assertIsNone(second.data["next_before_revision"])
        empty = self.read(before_revision=1)
        self.assertEqual(empty.data["versions"], [])
        self.assertIsNone(empty.data["next_before_revision"])

    def test_existing_other_patient_encounter_cannot_be_read(self):
        client = Client.objects.create(business=self.business, full_name="Other synthetic patient")
        patient = PatientProfile.objects.create(business=self.business, client=client, created_by=self.owner)
        record = DentalMedicalRecord.objects.create(business=self.business, patient=patient, number="OTHER", opened_by=self.owner)
        appointment = Appointment.objects.create(business=self.business, client=client, branch=self.first,
            resource=self.staff, service=self.service, start_at=self.appointment.start_at, end_at=self.appointment.end_at)
        encounter = MedicalEncounter.objects.create(business=self.business, patient=patient, record=record,
            appointment=appointment, branch=self.first, primary_clinician=self.member)
        self.append(encounter=encounter)
        response = self.api.get(f"/api/medical/encounters/{encounter.pk}/revisions/", self.scope)
        self.assertEqual(response.status_code, 403, response.data)
        self.assertFalse(MedicalAuditEvent.objects.exists())

    def test_revocation_and_invalid_cursor_fail_without_history(self):
        for values in ({"limit": 51}, {"before_revision": 0}, {"content": "secret"}):
            response = self.read(**values)
            self.assertEqual(response.status_code, 400, response.data)
        self.assignment.revoked_at = timezone.now()
        self.assignment.save(update_fields=["revoked_at"])
        denied = self.read()
        self.assertEqual(denied.status_code, 403, denied.data)
        self.assertEqual(denied["Cache-Control"], "no-store, private")

    def test_second_audit_failure_rolls_back_first_audit_and_returns_no_page(self):
        create = MedicalAuditEvent.objects.create
        count = 0

        def fail_second(*args, **kwargs):
            nonlocal count
            count += 1
            if count == 2:
                raise DatabaseError("synthetic")
            return create(*args, **kwargs)

        with patch("apps.medical.audit.MedicalAuditEvent.objects.create", side_effect=fail_second):
            response = self.read()
        self.assertEqual(response.status_code, 503, response.data)
        self.assertFalse(MedicalAuditEvent.objects.exists())
        self.assertNotIn("versions", response.data)

    def test_missing_current_revision_is_unavailable_not_partial_history(self):
        self.advance()
        response = self.read()
        self.assertEqual(response.status_code, 503, response.data)
        self.assertFalse(MedicalAuditEvent.objects.exists())
