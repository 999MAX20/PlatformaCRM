from unittest.mock import patch

from django.db import DatabaseError
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied, ValidationError

from apps.businesses.models import Business
from . import tests_tooth_services as fixtures
from .tests_patient_services import key
from .audit import MedicalAuditUnavailable
from .identity_crypto import MedicalDataUnavailable
from .models import DentalToothHistory, MedicalAuditEvent, TreatmentParticipation
from .tooth_reads import read_tooth_observation, read_tooth_snapshot, read_tooth_revision_history


@override_settings(MEDICAL_DATA_KEYS={"test": key(7)}, MEDICAL_DATA_ACTIVE_KEY_ID="test",
                   MEDICAL_IDENTITY_INDEX_KEY=key(8), MEDICAL_TOOTH_SURFACE_POLICIES="")
class ToothObservationReadTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        fixtures.PrimaryToothObservationTests.setUpTestData.__func__(cls)

    save = fixtures.PrimaryToothObservationTests.save

    def setUp(self):
        self.history, _ = self.save()
        MedicalAuditEvent.objects.all().delete()

    def read(self, **overrides):
        return read_tooth_observation(**(dict(actor=self.doctor, business_id=self.business.pk,
            patient_id=self.patient.pk, history_id=self.history.pk, appointment_id=self.appointment.pk) | overrides))

    def test_exact_revision_read_is_audited_without_clinical_text(self):
        result = self.read()
        self.assertEqual((result["history_id"], result["revision"], result["tooth"]), (self.history.pk, 1, 11))
        self.assertEqual(result["observation"], "Private synthetic tooth observation")
        event = MedicalAuditEvent.objects.get()
        self.assertEqual((event.action, event.tooth_history_id), ("read", self.history.pk))
        self.assertNotIn("Private synthetic", str(event.__dict__))

    def test_historical_read_returns_old_content_after_later_change(self):
        self.save(expected_tooth_revision=1, idempotency_key="later", observation="Later synthetic")
        result = self.read()
        self.assertEqual(result["observation"], "Private synthetic tooth observation")
        self.assertEqual(result["revision"], 1)

    def test_participation_reads_snapshot_and_history_without_active_booking_then_denies_after_end(self):
        self.save(expected_tooth_revision=1, idempotency_key="later", observation="Later synthetic")
        type(self.appointment).objects.filter(pk=self.appointment.pk).update(status="completed")
        now = timezone.now()
        participation = TreatmentParticipation.objects.create(patient=self.patient, member=self.member,
            branch=self.first, proposed_by=self.owner, state="active", proposed_at=now, accepted_at=now)
        scope = dict(actor=self.doctor, business_id=self.business.pk, patient_id=self.patient.pk,
                     participation_id=participation.pk)
        self.assertEqual(read_tooth_snapshot(**scope)["observations"][0]["observation"], "Later synthetic")
        self.assertEqual(read_tooth_snapshot(**scope, as_of=self.history.observed_at)["observations"][0]["revision"], 1)
        self.assertEqual(len(read_tooth_revision_history(**scope, tooth_state_id=self.history.tooth_state_id)["versions"]), 2)
        self.assertEqual(read_tooth_observation(**scope, history_id=self.history.pk)["revision"], 1)
        participation.state, participation.closed_at, participation.closed_by = "ended", now, self.owner
        participation.save(update_fields=["state", "closed_at", "closed_by"])
        count = MedicalAuditEvent.objects.count()
        for reader, params in ((read_tooth_snapshot, {}),
                (read_tooth_revision_history, {"tooth_state_id": self.history.tooth_state_id}),
                (read_tooth_observation, {"history_id": self.history.pk})):
            with self.subTest(reader=reader.__name__), self.assertRaises(PermissionDenied):
                reader(**scope, **params)
        self.assertEqual(MedicalAuditEvent.objects.count(), count)

    def test_audit_failure_never_decrypts(self):
        with patch("apps.medical.audit.MedicalAuditEvent.objects.create", side_effect=DatabaseError("synthetic")):
            with patch("apps.medical.tooth_reads.read_tooth_history") as decrypt:
                with self.assertRaises(MedicalAuditUnavailable):
                    self.read()
                decrypt.assert_not_called()

    def test_unknown_or_foreign_scope_cannot_read(self):
        with self.assertRaises(PermissionDenied):
            self.read(history_id=self.history.pk + 10000)
        foreign = Business.objects.create(owner=self.owner, name="Foreign", slug="tooth-read-foreign")
        with self.assertRaises(PermissionDenied):
            self.read(business_id=foreign.pk)
        self.assertFalse(MedicalAuditEvent.objects.exists())

    def test_revoked_role_denies_before_audit(self):
        type(self.assignment).objects.filter(pk=self.assignment.pk).update(revoked_at=timezone.now())
        with self.assertRaises(PermissionDenied):
            self.read()
        self.assertFalse(MedicalAuditEvent.objects.exists())

    def test_missing_or_multiple_basis_is_rejected(self):
        for values in ({"appointment_id": None}, {"participation_id": 1}):
            with self.subTest(values=values), self.assertRaises(ValidationError):
                self.read(**values)

    def test_corrupt_ciphertext_does_not_return_text_or_commit_success_audit(self):
        DentalToothHistory.objects.filter(pk=self.history.pk).update(content_encrypted="invalid")
        with self.assertRaises(MedicalDataUnavailable):
            self.read()
        self.assertFalse(MedicalAuditEvent.objects.exists())
