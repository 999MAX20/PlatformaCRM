from datetime import timedelta

from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.db.models.deletion import ProtectedError
from django.test import TestCase, override_settings
from django.utils import timezone

from apps.scheduling.models import Appointment
from . import tests_participation_services as fixtures
from .models import MedicalRoleAssignment, TreatmentParticipation
from .tests_patient_services import key


@override_settings(MEDICAL_DATA_KEYS={"test": key(7)}, MEDICAL_DATA_ACTIVE_KEY_ID="test",
                   MEDICAL_IDENTITY_INDEX_KEY=key(8))
class ParticipationSourceTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        fixtures.ParticipationCommandTests.setUpTestData.__func__(cls)

    propose = fixtures.ParticipationCommandTests.propose
    respond = fixtures.ParticipationCommandTests.respond

    def source(self):
        return TreatmentParticipation.objects.create(patient=self.patient, member=self.member,
            branch=self.first, proposed_by=self.owner, state="active",
            proposed_at=timezone.now() - timedelta(seconds=1), accepted_at=timezone.now())

    def test_appointment_origin_survives_replay_and_response(self):
        item, _ = self.propose()
        self.assertEqual(item.source_appointment_id, self.appointment.pk)
        self.assertIsNone(item.source_participation_id)
        replay, repeated = self.propose()
        self.assertTrue(repeated)
        self.assertEqual(replay.source_appointment_id, self.appointment.pk)
        accepted, _ = self.respond(item)
        self.assertEqual(accepted.source_appointment_id, self.appointment.pk)
        with self.assertRaises(ProtectedError):
            self.appointment.delete()

    def test_participation_origin_is_preserved_and_protected(self):
        source = self.source()
        item, _ = self.propose(source_appointment_id=None, source_participation_id=source.pk)
        self.assertEqual(item.source_participation_id, source.pk)
        self.assertIsNone(item.source_appointment_id)
        with self.assertRaises(ProtectedError):
            source.delete()

    def test_head_uses_its_authority_without_persisting_unvalidated_source(self):
        MedicalRoleAssignment.objects.filter(pk=self.assignment.pk).update(kind="head")
        item, _ = self.propose(source_appointment_id=99999999)
        self.assertIsNone(item.source_appointment_id)
        self.assertIsNone(item.source_participation_id)

    def test_source_reassignment_does_not_block_recipient_response(self):
        item, _ = self.propose()
        Appointment.objects.filter(pk=self.appointment.pk).update(resource=None)
        accepted, _ = self.respond(item)
        self.assertEqual(accepted.state, "active")
        self.assertEqual(accepted.source_appointment_id, self.appointment.pk)

    def test_database_rejects_two_sources_and_self_reference(self):
        source = self.source()
        item, _ = self.propose()
        for values in ({"source_participation_id": source.pk},
                       {"source_appointment_id": None, "source_participation_id": item.pk}):
            with self.subTest(values=values), self.assertRaises(IntegrityError), transaction.atomic():
                TreatmentParticipation.objects.filter(pk=item.pk).update(**values)

    def test_original_source_cannot_be_cleared_by_model_validation(self):
        item, _ = self.propose()
        item.source_appointment_id = None
        with self.assertRaises(ValidationError):
            item.full_clean()

    def test_new_source_cannot_belong_to_another_proposer(self):
        item = TreatmentParticipation(patient=self.patient, member=self.member, branch=self.first,
            proposed_by=self.recipient, source_appointment=self.appointment)
        with self.assertRaises(ValidationError):
            item.full_clean()
        item.source_appointment = None
        item.source_participation = self.source()
        with self.assertRaises(ValidationError):
            item.full_clean()
