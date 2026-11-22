from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.db.models.deletion import ProtectedError
from django.test import TestCase

from apps.businesses.models import Business
from apps.clients.models import Client
from . import tests_encounter_storage as fixtures
from .models import DentalToothHistory, DentalToothState, FDI_TOOTH_NUMBERS, MedicalEncounter, PatientProfile


class DentalToothStorageTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        fixtures.MedicalEncounterStorageTests.setUpTestData.__func__(cls)
        cls.encounter = MedicalEncounter.objects.create(business=cls.business, patient=cls.patient,
            record=cls.record, appointment=cls.appointment, branch=cls.first, primary_clinician=cls.member)

    def state(self, **overrides):
        return DentalToothState.objects.create(**(dict(business=self.business, patient=self.patient, tooth=11) | overrides))

    def history(self, state, **overrides):
        return DentalToothHistory(**(dict(tooth_state=state, encounter=self.encounter, revision=1,
            content_encrypted="synthetic-envelope", author=self.doctor) | overrides))

    def test_all_permanent_and_deciduous_identifiers_can_coexist(self):
        self.assertEqual(len(FDI_TOOTH_NUMBERS), 52)
        for tooth in FDI_TOOTH_NUMBERS:
            state = self.state(tooth=tooth)
            state.full_clean()
        self.assertEqual(DentalToothState.objects.count(), 52)

    def test_database_rejects_non_tooth_codes_and_zero_revision(self):
        for tooth in (0, 10, 19, 49, 50, 56, 66, 76, 86, 99):
            with self.subTest(tooth=tooth), self.assertRaises(IntegrityError), transaction.atomic():
                self.state(tooth=tooth)
        with self.assertRaises(IntegrityError), transaction.atomic():
            self.state(revision=0)

    def test_unique_location_preserves_distinct_surfaces(self):
        self.state()
        self.state(surface="synthetic_surface")
        with self.assertRaises(IntegrityError), transaction.atomic():
            self.state()
        state = self.state(tooth=12, surface="invalid surface")
        with self.assertRaises(ValidationError):
            state.full_clean()

    def test_state_rejects_foreign_business_patient(self):
        foreign = Business.objects.create(name="Synthetic foreign", slug="tooth-foreign", owner=self.owner)
        state = DentalToothState(business=foreign, patient=self.patient, tooth=11)
        with self.assertRaises(ValidationError):
            state.full_clean()

    def test_history_chain_retains_old_content_and_protects_parents(self):
        state = self.state(revision=2)
        first = self.history(state)
        first.full_clean(); first.save()
        second = self.history(state, revision=2, previous=first, content_encrypted="synthetic-next-envelope")
        second.full_clean(); second.save()
        first.refresh_from_db()
        self.assertEqual(first.content_encrypted, "synthetic-envelope")
        self.assertEqual(second.previous_id, first.pk)
        for item in (state, first, self.encounter):
            with self.subTest(model=type(item).__name__), self.assertRaises(ProtectedError):
                item.delete()

    def test_history_rejects_wrong_patient_and_nonpreceding_revision(self):
        state = self.state(revision=3)
        first = self.history(state); first.save()
        another = self.state(tooth=12, revision=3)
        for value in (self.history(another, revision=2, previous=first),
                      self.history(state, revision=3, previous=first),
                      self.history(state, revision=4, previous=first)):
            with self.subTest(revision=value.revision), self.assertRaises(ValidationError):
                value.full_clean()
        client = Client.objects.create(business=self.business, full_name="Other synthetic")
        patient = PatientProfile.objects.create(business=self.business, client=client, created_by=self.owner)
        other_patient_state = self.state(patient=patient)
        with self.assertRaises(ValidationError):
            self.history(other_patient_state).full_clean()

    def test_history_database_rejects_missing_previous_empty_content_and_duplicate(self):
        state = self.state(revision=2)
        first = self.history(state); first.save()
        cases = [dict(revision=2), dict(revision=2, previous=first, content_encrypted=""),
                 dict(revision=0), dict(revision=1, previous=first), {}]
        for changes in cases:
            with self.subTest(changes=changes), self.assertRaises(IntegrityError), transaction.atomic():
                self.history(state, **changes).save()
