from datetime import timedelta

from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.db.models.deletion import ProtectedError
from django.test import TestCase
from django.utils import timezone

from apps.branches.models import Branch
from apps.businesses.models import Business, BusinessMember
from apps.clients.models import Client
from . import tests_appointment_access as fixtures
from .models import DentalMedicalRecord, MedicalEncounter, MedicalEncounterRevision, PatientProfile


class MedicalEncounterStorageTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        fixtures.AppointmentMedicalBasisTests.setUpTestData.__func__(cls)
        cls.record = DentalMedicalRecord.objects.create(business=cls.business, patient=cls.patient,
            number="SYNTHETIC-001", opened_by=cls.doctor)

    def encounter(self, **overrides):
        return MedicalEncounter(**(dict(business=self.business, patient=self.patient, record=self.record,
            appointment=self.appointment, branch=self.first, primary_clinician=self.member) | overrides))

    def test_one_active_record_and_unique_local_number_preserve_archived_history(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            DentalMedicalRecord.objects.create(business=self.business, patient=self.patient,
                number="SYNTHETIC-002", opened_by=self.doctor)
        DentalMedicalRecord.objects.filter(pk=self.record.pk).update(state="archived", archived_at=timezone.now(), archived_by=self.doctor)
        second = DentalMedicalRecord.objects.create(business=self.business, patient=self.patient,
            number="SYNTHETIC-002", opened_by=self.doctor)
        second.full_clean()
        with self.assertRaises(IntegrityError), transaction.atomic():
            DentalMedicalRecord.objects.create(business=self.business, patient=self.patient,
                number="SYNTHETIC-001", opened_by=self.doctor, state="archived", opened_at=self.record.opened_at,
                archived_at=timezone.now(), archived_by=self.doctor)
        self.assertEqual(DentalMedicalRecord.objects.count(), 2)

    def test_record_archival_requires_actor_and_chronology(self):
        for changes in ({"state": "archived"}, {"state": "archived", "archived_at": timezone.now()},
                        {"state": "unknown"}, {"number": ""}):
            with self.subTest(changes=changes), self.assertRaises(IntegrityError), transaction.atomic():
                DentalMedicalRecord.objects.filter(pk=self.record.pk).update(**changes)

    def test_only_one_primary_encounter_for_appointment(self):
        item = self.encounter()
        item.full_clean()
        item.save()
        with self.assertRaises(IntegrityError), transaction.atomic():
            self.encounter().save()
        self.appointment.refresh_from_db()
        self.assertEqual(self.appointment.status, "created")

    def test_incomplete_finalization_and_invalid_times_rejected_by_database(self):
        item = self.encounter()
        item.save()
        before = item.started_at - timedelta(seconds=1)
        now = timezone.now()
        cases = [{"state": "finalized"}, {"state": "draft", "ended_at": now}, {"revision": 0},
            {"state": "finalized", "ended_at": before, "finalized_at": now, "finalized_by": self.doctor},
            {"state": "finalized", "ended_at": now, "finalized_at": before, "finalized_by": self.doctor}]
        for changes in cases:
            with self.subTest(changes=changes), self.assertRaises(IntegrityError), transaction.atomic():
                MedicalEncounter.objects.filter(pk=item.pk).update(**changes)

    def test_valid_finalized_storage_does_not_claim_signature_or_payment(self):
        start = timezone.now() - timedelta(hours=1)
        item = self.encounter(state="finalized", started_at=start, ended_at=start + timedelta(minutes=30),
            finalized_at=timezone.now(), finalized_by=self.doctor)
        item.full_clean()
        item.save()
        self.assertNotIn("signed", MedicalEncounter.States.values)
        self.assertFalse(hasattr(item, "paid"))

    def test_wrong_patient_record_and_calendar_branch_rejected(self):
        other = Client.objects.create(business=self.business, full_name="Other synthetic patient")
        other_patient = PatientProfile.objects.create(business=self.business, client=other, created_by=self.owner)
        other_record = DentalMedicalRecord.objects.create(business=self.business, patient=other_patient,
            number="OTHER", opened_by=self.doctor)
        for changes in ({"patient": other_patient}, {"record": other_record}, {"branch": self.second}):
            with self.subTest(changes=changes), self.assertRaises(ValidationError):
                self.encounter(**changes).full_clean()

    def test_foreign_tenant_links_rejected(self):
        foreign = Business.objects.create(owner=self.owner, name="Foreign", slug="encounter-foreign")
        branch = Branch.objects.create(business=foreign, name="Foreign")
        member = BusinessMember.objects.create(business=foreign, user=self.doctor, role="specialist")
        for changes in ({"business": foreign}, {"branch": branch}, {"primary_clinician": member}):
            with self.subTest(changes=changes), self.assertRaises(ValidationError):
                self.encounter(**changes).full_clean()
        self.record.business = foreign
        with self.assertRaises(ValidationError):
            self.record.full_clean()

    def test_revision_identity_and_required_payload_are_enforced(self):
        item = self.encounter()
        item.save()
        MedicalEncounterRevision.objects.create(encounter=item, revision=1, content_encrypted="synthetic-envelope", author=self.doctor)
        for version, payload in ((1, "duplicate"), (0, "invalid"), (2, "")):
            with self.subTest(version=version), self.assertRaises(IntegrityError), transaction.atomic():
                MedicalEncounterRevision.objects.create(encounter=item, revision=version, content_encrypted=payload, author=self.doctor)
        MedicalEncounterRevision.objects.create(encounter=item, revision=2, content_encrypted="another-envelope", author=self.owner)
        self.assertEqual(item.clinical_revisions.count(), 2)

    def test_revisions_and_encounter_retain_parent_history(self):
        item = self.encounter()
        item.save()
        MedicalEncounterRevision.objects.create(encounter=item, revision=1, content_encrypted="synthetic-envelope", author=self.doctor)
        for parent in (item, self.appointment, self.record, self.member):
            with self.subTest(parent=type(parent).__name__), self.assertRaises(ProtectedError):
                parent.delete()
