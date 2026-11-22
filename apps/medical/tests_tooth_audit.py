from unittest.mock import patch

from django.db import DatabaseError, IntegrityError, transaction
from django.db.models.deletion import ProtectedError
from django.test import TestCase, override_settings
from django.utils import timezone

from apps.businesses.models import Business
from apps.clients.models import Client
from . import tests_tooth_content as fixtures
from .tests_patient_services import key
from .audit import MedicalAuditUnavailable, write_patient_audit
from .models import DentalToothHistory, MedicalAuditEvent, PatientProfile


@override_settings(MEDICAL_DATA_KEYS={"test": key(7)}, MEDICAL_DATA_ACTIVE_KEY_ID="test")
class DentalToothAuditTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        fixtures.DentalToothContentTests.setUpTestData.__func__(cls)

    append = fixtures.DentalToothContentTests.append
    advance = fixtures.DentalToothContentTests.advance

    def audit(self, history, **overrides):
        return write_patient_audit(**(dict(actor=self.doctor, business=self.business, patient=self.patient,
            action="tooth_observation_saved", tooth_history=history) | overrides))

    def test_exact_history_reference_has_no_text_and_prevents_deletion(self):
        history = self.append()
        event = self.audit(history)
        self.assertEqual((event.tooth_history_id, event.patient_id, event.patient_revision), (history.pk, self.patient.pk, 1))
        for text in ("Синтетическое наблюдение", "Private synthetic reason", history.content_encrypted):
            self.assertNotIn(text, str(event.__dict__))
        with self.assertRaises(ProtectedError):
            history.delete()

    def test_history_read_allowed_write_requires_current_revision_and_draft(self):
        first = self.append()
        self.advance()
        second = self.append()
        with self.assertRaises(ValueError):
            self.audit(first)
        self.assertEqual(self.audit(first, action="read").tooth_history_id, first.pk)
        self.audit(second)
        now = timezone.now()
        type(self.encounter).objects.filter(pk=self.encounter.pk).update(state="finalized",
            ended_at=now, finalized_at=now, finalized_by=self.doctor)
        with self.assertRaises(ValueError):
            self.audit(second)
        self.audit(second, action="read")

    def test_foreign_business_patient_and_corrupt_links_are_rejected(self):
        history = self.append()
        foreign = Business.objects.create(name="Foreign", slug="tooth-audit-foreign", owner=self.owner)
        client = Client.objects.create(business=self.business, full_name="Other synthetic")
        patient = PatientProfile.objects.create(business=self.business, client=client, created_by=self.owner)
        for values in ({"business": foreign}, {"patient": patient}):
            with self.subTest(values=values), self.assertRaises(ValueError):
                self.audit(history, **values)
        type(self.encounter).objects.filter(pk=self.encounter.pk).update(branch=self.second)
        with self.assertRaises(ValueError):
            self.audit(history)
        self.assertFalse(MedicalAuditEvent.objects.exists())

    def test_missing_mixed_or_unrelated_reference_rejected_in_helper_and_database(self):
        history = self.append()
        for values in ({"tooth_history": None}, {"record": self.record}, {"action": "patient_updated"}):
            with self.subTest(values=values), self.assertRaises(ValueError):
                self.audit(history, **values)
        cases = [{}, {"tooth_history": history, "record": self.record},
                 {"tooth_history": history, "action": "patient_updated"},
                 {"tooth_history": history, "patient": None, "patient_revision": None}]
        defaults = dict(business=self.business, actor=self.doctor, patient=self.patient, patient_revision=1,
            action="tooth_observation_saved", result="success")
        for values in cases:
            with self.subTest(values=values), self.assertRaises(IntegrityError), transaction.atomic():
                MedicalAuditEvent.objects.create(**(defaults | values))

    def test_audit_failure_rolls_back_new_history_and_revision(self):
        self.append()
        with self.assertRaises(MedicalAuditUnavailable), transaction.atomic():
            self.advance()
            history = self.append(observation="Rollback synthetic observation")
            with patch("apps.medical.audit.MedicalAuditEvent.objects.create", side_effect=DatabaseError("synthetic")):
                self.audit(history)
        self.state.refresh_from_db()
        self.assertEqual(self.state.revision, 1)
        self.assertEqual(DentalToothHistory.objects.count(), 1)
        self.assertFalse(MedicalAuditEvent.objects.exists())

    def test_missing_durable_event_is_not_reported_as_success(self):
        history = self.append()
        with patch("apps.medical.audit.MedicalAuditEvent.objects.create", return_value=None):
            with self.assertRaises(MedicalAuditUnavailable):
                self.audit(history)
