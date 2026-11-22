from unittest.mock import patch

from django.db import DatabaseError
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from apps.businesses.models import RolePermission
from . import tests_encounter_open as fixtures
from . import tests_patient_services as crypto_fixtures
from .models import MedicalAuditEvent, MedicalEncounter, PatientProfile


@override_settings(MEDICAL_DATA_KEYS={"test": crypto_fixtures.key(7)}, MEDICAL_DATA_ACTIVE_KEY_ID="test",
                   MEDICAL_IDENTITY_INDEX_KEY=crypto_fixtures.key(8))
class AppointmentClinicalContextTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        fixtures.OpenPrimaryEncounterTests.setUpTestData.__func__(cls)

    def setUp(self):
        self.api = APIClient()
        self.api.force_authenticate(self.doctor)

    def read(self, **overrides):
        response = self.api.get("/api/medical/encounters/appointment-context/",
            {"business_id": self.business.pk, "appointment_id": self.appointment.pk} | overrides)
        self.assertEqual(response["Cache-Control"], "no-store, private")
        self.assertEqual(response["Pragma"], "no-cache")
        return response

    def test_resolves_patient_and_audits_metadata_without_decrypting(self):
        with patch("apps.medical.encounter_content.read_encounter_revision", side_effect=AssertionError("No content read")):
            response = self.read()
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data["patient"]["id"], self.patient.pk)
        self.assertEqual(response.data["appointment"]["updated_at"], self.appointment.updated_at)
        self.assertEqual(response.data["active_record"]["id"], self.record.pk)
        self.assertEqual(response.data["actions"], {"create_record": False, "open_encounter": True, "save_draft": False})
        self.assertEqual(MedicalAuditEvent.objects.get().record_id, self.record.pk)
        self.assertFalse(MedicalEncounter.objects.exists())

    def test_no_chart_offers_creation_without_creating_it(self):
        self.record.delete()
        response = self.read()
        self.assertEqual(response.status_code, 200, response.data)
        self.assertIsNone(response.data["active_record"])
        self.assertEqual(response.data["actions"], {"create_record": True, "open_encounter": False, "save_draft": False})
        self.assertIsNone(MedicalAuditEvent.objects.get().record_id)

    def test_unverified_identity_keeps_read_but_disables_writes(self):
        PatientProfile.objects.filter(pk=self.patient.pk).update(identity_status="unverified",
            verified_at=None, verified_by=None, verification_evidence_encrypted="")
        response = self.read()
        self.assertEqual(response.status_code, 200, response.data)
        self.assertFalse(any(response.data["actions"].values()))

    def test_read_permission_does_not_imply_write_permissions(self):
        RolePermission.objects.filter(business_role=self.role, resource="medical_records",
            action__in=["create", "update"]).update(is_allowed=False)
        response = self.read()
        self.assertEqual(response.status_code, 200, response.data)
        self.assertFalse(any(response.data["actions"].values()))

    def test_opened_encounter_exposes_current_version_and_save_action(self):
        version, _ = fixtures.OpenPrimaryEncounterTests.open(self)
        response = self.read()
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data["encounter"]["version_id"], version.pk)
        self.assertEqual(response.data["actions"], {"create_record": False, "open_encounter": False, "save_draft": True})
        self.assertNotIn("Private synthetic", response.content.decode())
        self.assertEqual(MedicalAuditEvent.objects.filter(action="read").count(), 2)

    def test_missing_profile_is_not_disclosed_to_unauthorized_actor(self):
        self.record.delete()
        self.patient.delete()
        self.api.force_authenticate(self.owner)
        self.assertEqual(self.read().status_code, 403)
        self.api.force_authenticate(self.doctor)
        self.assertEqual(self.read().status_code, 404)
        self.assertFalse(MedicalAuditEvent.objects.exists())

    def test_current_branch_role_and_booking_are_required(self):
        self.assignment.branches.clear()
        self.assertEqual(self.read().status_code, 403)
        self.assignment.branches.add(self.first)
        self.assignment.revoked_at = timezone.now()
        self.assignment.save(update_fields=["revoked_at"])
        self.assertEqual(self.read().status_code, 403)
        self.assignment.revoked_at = None
        self.assignment.save(update_fields=["revoked_at"])
        self.appointment.status = "cancelled"
        self.appointment.save(update_fields=["status"])
        self.assertEqual(self.read().status_code, 403)
        self.assertFalse(MedicalAuditEvent.objects.exists())

    def test_wrong_booking_and_extra_patient_id_fail_closed(self):
        self.assertEqual(self.read(appointment_id=self.appointment.pk + 999).status_code, 403)
        self.assertEqual(self.read(patient_id=self.patient.pk).status_code, 400)
        self.assertFalse(MedicalAuditEvent.objects.exists())

    def test_audit_failure_returns_no_context(self):
        with patch("apps.medical.audit.MedicalAuditEvent.objects.create", side_effect=DatabaseError("Synthetic failure")):
            response = self.read()
        self.assertEqual(response.status_code, 503)
        self.assertNotIn("patient", response.data)
        self.assertFalse(MedicalAuditEvent.objects.exists())

    def test_missing_current_revision_rolls_back_metadata_audit(self):
        version, _ = fixtures.OpenPrimaryEncounterTests.open(self)
        MedicalEncounter.objects.filter(pk=version.encounter_id).update(revision=2)
        response = self.read()
        self.assertEqual(response.status_code, 503)
        self.assertFalse(MedicalAuditEvent.objects.filter(action="read").exists())
