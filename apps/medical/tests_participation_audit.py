from unittest.mock import patch

from django.db import DatabaseError, IntegrityError, transaction
from django.test import TestCase

from apps.clients.models import Client
from . import tests_participation_storage as fixtures
from .audit import MedicalAuditUnavailable, write_patient_audit
from .models import MedicalAuditEvent, PatientProfile, TreatmentParticipation


class ParticipationAuditTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        fixtures.TreatmentParticipationStorageTests.setUpTestData.__func__(cls)
        cls.participation = TreatmentParticipation.objects.create(patient=cls.patient, member=cls.member,
            branch=cls.first, proposed_by=cls.owner)

    def audit(self, **overrides):
        return write_patient_audit(**(dict(actor=self.owner, business=self.business, patient=self.patient,
            action="participation_proposed", participation=self.participation) | overrides))

    def test_action_records_patient_and_participation_versions_without_reason(self):
        event = self.audit()
        self.assertEqual((event.patient_id, event.participation_id, event.participation_revision, event.result),
            (self.patient.pk, self.participation.pk, 1, "success"))
        self.assertFalse(hasattr(event, "reason"))

    def test_missing_and_other_patient_links_rejected(self):
        with self.assertRaises(ValueError):
            self.audit(participation=None)
        client = Client.objects.create(business=self.business, full_name="Other synthetic patient")
        patient = PatientProfile.objects.create(business=self.business, client=client, created_by=self.owner)
        with self.assertRaises(ValueError):
            self.audit(patient=patient)
        self.assertEqual(MedicalAuditEvent.objects.count(), 0)

    def test_database_rejects_missing_relation_or_revision(self):
        for values in ({}, {"participation": self.participation},
                       {"participation": self.participation, "participation_revision": 0}):
            with self.subTest(values=values), self.assertRaises(IntegrityError), transaction.atomic():
                MedicalAuditEvent.objects.create(business=self.business, actor=self.owner, patient=self.patient,
                    patient_revision=1, action="participation_accepted", result="success", **values)

    def test_audit_failure_rolls_back_transition_in_caller_transaction(self):
        with self.assertRaises(MedicalAuditUnavailable):
            with transaction.atomic():
                TreatmentParticipation.objects.filter(pk=self.participation.pk).update(revision=2)
                with patch("apps.medical.audit.MedicalAuditEvent.objects.create", side_effect=DatabaseError("synthetic")):
                    self.audit()
        self.participation.refresh_from_db()
        self.assertEqual(self.participation.revision, 1)
        self.assertEqual(MedicalAuditEvent.objects.count(), 0)
