from unittest.mock import patch

from django.db import DatabaseError
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from apps.clients.models import Client
from apps.branches.models import Branch
from apps.businesses.models import Business, BusinessMember
from apps.scheduling.models import Appointment
from . import tests_encounter_content as fixtures
from . import tests_patient_services as crypto_fixtures
from .models import DentalMedicalRecord, MedicalAuditEvent, MedicalEncounter, MedicalEncounterRevision, PatientProfile


@override_settings(MEDICAL_DATA_KEYS={"test": crypto_fixtures.key(7)}, MEDICAL_DATA_ACTIVE_KEY_ID="test")
class ClinicalWorkspaceAPITests(TestCase):
    @classmethod
    def setUpTestData(cls):
        fixtures.EncounterContentTests.setUpTestData.__func__(cls)

    append = fixtures.EncounterContentTests.append
    advance = fixtures.EncounterContentTests.advance

    def setUp(self):
        self.version = self.append()
        self.api = APIClient()
        self.api.force_authenticate(self.doctor)
        self.url = "/api/medical/encounters/workspace/"

    def read(self, **overrides):
        return self.api.get(self.url, dict(business_id=self.business.pk, patient_id=self.patient.pk,
            appointment_id=self.appointment.pk) | overrides)

    def extra_encounter(self):
        appointment = Appointment.objects.create(business=self.business, client=self.patient_client,
            branch=self.first, resource=self.staff, service=self.service,
            start_at=self.appointment.start_at, end_at=self.appointment.end_at)
        encounter = MedicalEncounter.objects.create(business=self.business, patient=self.patient, record=self.record,
            appointment=appointment, branch=self.first, primary_clinician=self.member)
        self.append(encounter=encounter)
        return encounter

    def test_workspace_exposes_metadata_and_audits_without_decrypting(self):
        self.doctor.full_name = "Synthetic clinician"
        self.doctor.save(update_fields=["full_name"])
        with patch("apps.medical.encounter_reads.read_encounter_revision") as decrypt:
            response = self.read()
            decrypt.assert_not_called()
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response["Cache-Control"], "no-store, private")
        self.assertEqual(response.data["active_record"]["id"], self.record.pk)
        self.assertEqual(response.data["encounters"][0]["version_id"], self.version.pk)
        self.assertEqual(response.data["encounters"][0]["branch_name"], self.first.name)
        self.assertEqual(response.data["encounters"][0]["primary_clinician_name"], "Synthetic clinician")
        self.assertEqual(response.data["encounters"][0]["author_name"], "Synthetic clinician")
        self.assertNotIn("content", response.data["encounters"][0])
        self.assertNotIn("Оқу жоспары", response.content.decode())
        self.assertEqual(MedicalAuditEvent.objects.filter(record=self.record, action="read").count(), 1)
        self.assertEqual(MedicalAuditEvent.objects.filter(encounter_version=self.version, action="read").count(), 1)

    def test_pagination_continues_without_duplicates_after_new_insert(self):
        second = self.extra_encounter()
        first_page = self.read(limit=1)
        self.assertEqual(first_page.data["encounters"][0]["id"], second.pk)
        cursor = first_page.data["next_before_id"]
        newest = self.extra_encounter()
        second_page = self.read(limit=1, before_id=cursor)
        self.assertEqual([row["id"] for row in second_page.data["encounters"]], [self.encounter_record.pk])
        self.assertIsNone(second_page.data["next_before_id"])
        self.assertNotEqual(newest.pk, second_page.data["encounters"][0]["id"])

    def test_foreign_branch_or_clinician_labels_are_not_exposed_on_corrupt_links(self):
        foreign = Business.objects.create(owner=self.owner, name="Foreign", slug="history-label-foreign")
        branch = Branch.objects.create(business=foreign, name="Private foreign branch")
        member = BusinessMember.objects.create(business=foreign, user=self.owner, role="admin")
        for changes in ({"branch": branch, "primary_clinician": self.member},
                        {"branch": self.first, "primary_clinician": member}):
            with self.subTest(changes=changes):
                MedicalEncounter.objects.filter(pk=self.encounter_record.pk).update(**changes)
                response = self.read()
                self.assertEqual(response.status_code, 503)
                self.assertNotIn("Private foreign branch", response.content.decode())
                self.assertFalse(MedicalAuditEvent.objects.exists())

    def test_current_version_replaces_old_pointer_without_destroying_history(self):
        self.advance()
        newest = self.append(content={"plan": "Later"})
        response = self.read()
        self.assertEqual(response.data["encounters"][0]["version_id"], newest.pk)
        self.assertTrue(MedicalEncounterRevision.objects.filter(pk=self.version.pk).exists())

    def test_empty_workspace_is_explicit_and_audited(self):
        self.version.delete()
        self.encounter_record.delete()
        self.record.delete()
        response = self.read()
        self.assertEqual(response.status_code, 200, response.data)
        self.assertIsNone(response.data["active_record"])
        self.assertEqual(response.data["encounters"], [])
        self.assertIsNone(response.data["next_before_id"])
        self.assertEqual(MedicalAuditEvent.objects.get().patient_id, self.patient.pk)

    def test_other_patient_records_are_not_discovered(self):
        client = Client.objects.create(business=self.business, full_name="Other patient")
        patient = PatientProfile.objects.create(business=self.business, client=client, created_by=self.owner)
        record = DentalMedicalRecord.objects.create(business=self.business, patient=patient, number="PRIVATE-OTHER", opened_by=self.owner)
        response = self.read()
        self.assertNotIn(record.number, response.content.decode())
        denied = self.read(patient_id=patient.pk)
        self.assertEqual(denied.status_code, 403, denied.data)
        self.assertEqual(denied["Cache-Control"], "no-store, private")

    def test_revocation_and_invalid_pagination_are_not_cached_success(self):
        for values in ({"limit": 0}, {"limit": 51}, {"before_id": -1}, {"unknown": "x"}):
            response = self.read(**values)
            self.assertEqual(response.status_code, 400, response.data)
        self.assignment.revoked_at = timezone.now()
        self.assignment.save(update_fields=["revoked_at"])
        response = self.read()
        self.assertEqual(response.status_code, 403, response.data)
        self.assertEqual(response["Cache-Control"], "no-store, private")
        self.assertNotIn(self.record.number, response.content.decode())

    def test_audit_failure_or_missing_current_version_never_returns_partial_page(self):
        with patch("apps.medical.audit.MedicalAuditEvent.objects.create", side_effect=DatabaseError("synthetic")):
            response = self.read()
        self.assertEqual(response.status_code, 503, response.data)
        self.assertNotIn(self.record.number, response.content.decode())
        self.advance()
        response = self.read()
        self.assertEqual(response.status_code, 503, response.data)
        self.assertFalse(MedicalAuditEvent.objects.exists())
