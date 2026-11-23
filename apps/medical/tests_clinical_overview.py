import json
from datetime import timedelta
from unittest.mock import patch

from django.db import DatabaseError
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient
from apps.businesses.models import Business
from apps.clients.models import Client

from . import tests_encounter_open as fixtures
from . import tests_encounter_reads as reads
from . import tests_patient_services as crypto
from .identity_crypto import encrypt_medical_value
from .models import MedicalAuditEvent, MedicalEncounter, PatientProfile


@override_settings(MEDICAL_DATA_KEYS={"test": crypto.key(7)}, MEDICAL_DATA_ACTIVE_KEY_ID="test",
                   MEDICAL_IDENTITY_INDEX_KEY=crypto.key(8))
class ClinicalOverviewTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        fixtures.OpenPrimaryEncounterTests.setUpTestData.__func__(cls)

    open = fixtures.OpenPrimaryEncounterTests.open
    participation = reads.TreatingClinicianReadTests.participation

    def setUp(self):
        self.api = APIClient()
        self.api.force_authenticate(self.doctor)

    def read(self, **overrides):
        params = {"business_id": self.business.pk, "patient_id": self.patient.pk,
                  "appointment_id": self.appointment.pk} | overrides
        response = self.api.get("/api/medical/encounters/overview/",
                                {key: value for key, value in params.items() if value is not None})
        self.assertEqual(response["Cache-Control"], "no-store, private")
        return response

    def test_empty_overview_is_audited_and_does_not_create_encounter(self):
        response = self.read()
        self.assertEqual(response.status_code, 200, response.data)
        self.assertIsNone(response.data["date_of_birth"])
        self.assertIsNone(response.data["latest_encounter"])
        self.assertEqual(response.data["active_record"]["id"], self.record.pk)
        self.assertEqual(MedicalAuditEvent.objects.get().patient_id, self.patient.pk)
        self.assertFalse(MedicalEncounter.objects.exists())

    def test_only_birth_date_is_projected_from_encrypted_demographics(self):
        self.patient.demographics_encrypted = encrypt_medical_value(
            json.dumps({"date_of_birth": "2000-02-29", "sex": "female", "address": "Private address"}),
            business_id=self.business.pk, subject_id=self.patient.client_id, purpose="demographics")
        self.patient.save(update_fields=["demographics_encrypted"])
        response = self.read()
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data["date_of_birth"], "2000-02-29")
        self.assertNotIn("Private address", response.content.decode())
        self.assertNotIn("iin", response.data)
        self.assertNotIn("sex", response.data)

    def test_latest_encounter_uses_clinical_start_and_exact_current_revision(self):
        first, _ = self.open()
        booking = self.appointment
        booking.pk = None
        booking.save()
        second, _ = self.open(appointment_id=booking.pk, expected_appointment_updated_at=booking.updated_at,
                              idempotency_key="second")
        MedicalEncounter.objects.filter(pk=second.encounter_id).update(started_at=timezone.now() - timedelta(days=2))
        response = self.read(appointment_id=booking.pk)
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data["latest_encounter"]["version_id"], first.pk)
        self.assertNotIn("Private synthetic clinical text", response.content.decode())
        self.assertTrue(MedicalAuditEvent.objects.filter(action="read", encounter_version=first).exists())

    def test_current_participation_supports_read_after_booking_completion(self):
        version, _ = self.open()
        self.appointment.status = "completed"
        self.appointment.save(update_fields=["status"])
        participation = self.participation()
        response = self.read(appointment_id=None, participation_id=participation.pk)
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data["latest_encounter"]["version_id"], version.pk)
        participation.state = "ended"
        participation.closed_at = timezone.now()
        participation.closed_by = self.owner
        participation.save(update_fields=["state", "closed_at", "closed_by"])
        self.assertEqual(self.read(appointment_id=None, participation_id=participation.pk).status_code, 403)

    def test_owner_and_revoked_branch_cannot_read_demographics(self):
        self.api.force_authenticate(self.owner)
        self.assertEqual(self.read().status_code, 403)
        self.api.force_authenticate(self.doctor)
        self.assignment.branches.clear()
        self.assertEqual(self.read().status_code, 403)
        self.assertFalse(MedicalAuditEvent.objects.exists())

    def test_invalid_scope_and_foreign_patient_do_not_disclose_data(self):
        other_business = Business.objects.create(owner=self.owner, name="Other", slug="overview-other")
        other_client = Client.objects.create(business=other_business, full_name="Foreign patient")
        other_patient = PatientProfile.objects.create(business=other_business, client=other_client, created_by=self.owner)
        self.assertEqual(self.read(extra="value").status_code, 400)
        self.assertEqual(self.read(appointment_id=None).status_code, 400)
        self.assertEqual(self.read(patient_id=self.patient.pk + 1000).status_code, 404)
        self.assertEqual(self.read(business_id=self.business.pk + 1000).status_code, 404)
        self.assertEqual(self.read(patient_id=other_patient.pk).status_code, 404)
        self.assertFalse(MedicalAuditEvent.objects.exists())

    def test_corrupt_demographics_or_missing_revision_fail_without_audit_partial(self):
        PatientProfile.objects.filter(pk=self.patient.pk).update(demographics_encrypted="broken")
        self.assertEqual(self.read().status_code, 503)
        PatientProfile.objects.filter(pk=self.patient.pk).update(demographics_encrypted="")
        version, _ = self.open()
        MedicalEncounter.objects.filter(pk=version.encounter_id).update(revision=2)
        self.assertEqual(self.read().status_code, 503)
        self.assertFalse(MedicalAuditEvent.objects.filter(action="read").exists())

    def test_audit_failure_prevents_overview(self):
        with patch("apps.medical.audit.MedicalAuditEvent.objects.create", side_effect=DatabaseError("Synthetic")):
            response = self.read()
        self.assertEqual(response.status_code, 503)
        self.assertNotIn("full_name", response.data)
        self.assertFalse(MedicalAuditEvent.objects.exists())
