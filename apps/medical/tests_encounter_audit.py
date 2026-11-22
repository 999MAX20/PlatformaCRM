from unittest.mock import patch

from django.db import DatabaseError, IntegrityError, transaction
from django.db.models.deletion import ProtectedError
from django.test import TestCase, override_settings

from apps.businesses.models import Business
from apps.clients.models import Client
from . import tests_encounter_content as fixtures
from . import tests_patient_services as crypto_fixtures
from .audit import MedicalAuditUnavailable, write_patient_audit
from .models import MedicalAuditEvent, MedicalEncounterRevision, PatientProfile, TreatmentParticipation


@override_settings(MEDICAL_DATA_KEYS={"test": crypto_fixtures.key(7)}, MEDICAL_DATA_ACTIVE_KEY_ID="test")
class EncounterAuditTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        fixtures.EncounterContentTests.setUpTestData.__func__(cls)

    append = fixtures.EncounterContentTests.append
    advance = fixtures.EncounterContentTests.advance

    def audit(self, version, **overrides):
        return write_patient_audit(**(dict(actor=self.doctor, business=self.business, patient=self.patient,
            action="encounter_opened", encounter_version=version) | overrides))

    def test_exact_version_is_protected_without_clinical_content_in_event(self):
        version = self.append()
        event = self.audit(version)
        self.assertEqual((event.encounter_version_id, event.patient_id, event.patient_revision),
                         (version.pk, self.patient.pk, 1))
        self.assertNotIn("Synthetic private correction", str(event.__dict__))
        self.assertNotIn("Учебные жалобы", str(event.__dict__))
        with self.assertRaises(ProtectedError):
            version.delete()

    def test_other_patient_or_business_cannot_be_attached(self):
        version = self.append()
        other_client = Client.objects.create(business=self.business, full_name="Other synthetic patient")
        other_patient = PatientProfile.objects.create(business=self.business, client=other_client, created_by=self.owner)
        foreign = Business.objects.create(owner=self.owner, name="Foreign", slug="encounter-audit-foreign")
        for changes in ({"patient": other_patient}, {"business": foreign}):
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                self.audit(version, **changes)
        self.assertFalse(MedicalAuditEvent.objects.exists())

    def test_historical_read_allowed_but_write_event_requires_current_version(self):
        first = self.append()
        self.advance()
        second = self.append()
        with self.assertRaises(ValueError):
            self.audit(first, action="encounter_draft_saved")
        event = self.audit(first, action="read")
        self.assertEqual(event.encounter_version_id, first.pk)
        self.audit(second, action="encounter_draft_saved")

    def test_missing_version_or_mixed_relations_rejected_by_helper_and_database(self):
        version = self.append()
        participation = TreatmentParticipation.objects.create(patient=self.patient, member=self.member,
            branch=self.first, proposed_by=self.owner)
        with self.assertRaises(ValueError):
            self.audit(None)
        with self.assertRaises(ValueError):
            self.audit(version, participation=participation)
        cases = [dict(), dict(encounter_version=version, participation=participation, participation_revision=1)]
        for values in cases:
            with self.subTest(values=values), self.assertRaises(IntegrityError), transaction.atomic():
                MedicalAuditEvent.objects.create(business=self.business, patient=self.patient, patient_revision=1,
                    actor=self.doctor, action="encounter_opened", result="success", **values)
        with self.assertRaises(IntegrityError), transaction.atomic():
            MedicalAuditEvent.objects.create(business=self.business, actor=self.doctor,
                encounter_version=version, action="read", result="success")

    def test_audit_failure_rolls_back_new_encrypted_version_and_parent_revision(self):
        self.append()
        with self.assertRaises(MedicalAuditUnavailable):
            with transaction.atomic():
                self.advance()
                version = self.append(content={"plan": "Must roll back"})
                with patch("apps.medical.audit.MedicalAuditEvent.objects.create", side_effect=DatabaseError("synthetic")):
                    self.audit(version, action="encounter_draft_saved")
        self.encounter_record.refresh_from_db()
        self.assertEqual(self.encounter_record.revision, 1)
        self.assertEqual(MedicalEncounterRevision.objects.count(), 1)
        self.assertFalse(MedicalAuditEvent.objects.exists())

    def test_inconsistent_encounter_links_cannot_be_audited_as_success(self):
        version = self.append()
        type(self.encounter_record).objects.filter(pk=self.encounter_record.pk).update(branch=self.second)
        with self.assertRaises(ValueError):
            self.audit(version)
