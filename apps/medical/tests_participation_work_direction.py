from unittest.mock import patch
from datetime import date, datetime

from django.test import TestCase, override_settings
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.test import APIClient

from apps.core.domain_errors import IdempotencyConflict
from apps.core.idempotency import canonical_request_hash
from apps.core.models import CRMCommandIdempotency
from apps.notifications.models import Notification
from . import tests_participation_notifications as fixtures
from .identity_crypto import MedicalDataUnavailable, MedicalKeyUnavailable, medical_request_digest
from .models import MedicalAuditEvent, TreatmentParticipation
from .participation_access import assert_treatment_medical_basis
from .participation_reads import read_own_participations
from .tests_patient_services import key


@override_settings(MEDICAL_DATA_KEYS={"test": key(7)}, MEDICAL_DATA_ACTIVE_KEY_ID="test",
                   MEDICAL_IDENTITY_INDEX_KEY=key(8))
class ParticipationWorkDirectionTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        fixtures.ParticipationNotificationTests.setUpTestData.__func__(cls)

    propose = fixtures.ParticipationNotificationTests.propose
    respond = fixtures.ParticipationNotificationTests.respond

    def read(self):
        return read_own_participations(actor=self.recipient, business_id=self.business.pk)["results"][0]

    def test_direction_required_without_creating_partial_invitation(self):
        for value in ("", " \n", None, 1, "x" * 2001):
            with self.subTest(value=value), self.assertRaises(ValidationError):
                self.propose(work_direction=value)
        for model in (TreatmentParticipation, MedicalAuditEvent, Notification, CRMCommandIdempotency):
            self.assertFalse(model.objects.exists())

    def test_recipient_gets_organizational_direction_and_initiator_without_chart(self):
        item, _ = self.propose(work_direction="  Synthetic organizational work\n")
        row = self.read()
        self.assertEqual(row["work_direction"], "  Synthetic organizational work\n")
        self.assertEqual(row["proposer_name"], self.doctor.full_name)
        self.assertNotIn("Synthetic private reason", str(row))
        self.assertNotIn("organizational", item.work_direction_encrypted)
        with self.assertRaises(PermissionDenied):
            assert_treatment_medical_basis(actor=self.recipient, business=self.business,
                patient_id=self.patient.pk, participation_id=item.pk)
        for model in (MedicalAuditEvent, Notification, CRMCommandIdempotency):
            self.assertNotIn("organizational", str(list(model.objects.values())))

    def test_current_role_is_required_for_organizational_data(self):
        self.propose()
        self.target_role.branches.clear()
        self.assertEqual(read_own_participations(actor=self.recipient, business_id=self.business.pk)["results"], [])

    def test_replay_binds_direction_and_keeps_one_invitation(self):
        self.propose()
        self.assertTrue(self.propose()[1])
        with self.assertRaises(IdempotencyConflict):
            self.propose(work_direction="Different organizational work")
        self.assertEqual(TreatmentParticipation.objects.count(), 1)
        self.assertEqual(Notification.objects.count(), 1)

    def test_old_successful_proposal_receipt_replays_without_new_direction(self):
        item, _ = self.propose()
        old_payload = {"patient": self.patient.pk, "branch": self.first.pk, "target": self.target.pk,
            "expected_patient_revision": 1,
            "reason_digest": medical_request_digest({"reason": "Synthetic private reason"}, business_id=self.business.pk),
            "source_appointment": self.appointment.pk, "source_participation": None}
        CRMCommandIdempotency.objects.filter(action="medical.participation.propose").update(
            request_hash=canonical_request_hash(old_payload))
        TreatmentParticipation.objects.filter(pk=item.pk).update(work_direction_encrypted="")
        self.assertTrue(self.propose(work_direction="", planned_work_date=None)[1])
        self.assertIsNone(self.read()["work_direction"])

    def test_crypto_failure_rolls_back_and_corrupt_read_fails_closed(self):
        with patch("apps.medical.participation_services.encrypt_medical_value", side_effect=MedicalKeyUnavailable()):
            with self.assertRaises(MedicalKeyUnavailable):
                self.propose()
        self.assertFalse(TreatmentParticipation.objects.exists())
        self.assertFalse(Notification.objects.exists())
        item, _ = self.propose()
        TreatmentParticipation.objects.filter(pk=item.pk).update(work_direction_encrypted="invalid")
        with self.assertRaises(MedicalDataUnavailable):
            self.read()

    def test_http_requires_direction_and_does_not_echo_it_in_command(self):
        api = APIClient()
        api.force_authenticate(self.doctor)
        body = {"business_id": self.business.pk, "patient_id": self.patient.pk, "branch_id": self.first.pk,
            "target_member_id": self.target.pk, "expected_patient_revision": 1,
            "source_appointment_id": self.appointment.pk}
        url = "/api/medical/participations/"
        self.assertEqual(api.post(url, body, format="json", HTTP_IDEMPOTENCY_KEY="http").status_code, 400)
        response = api.post(url, body | {"work_direction": "Synthetic organizational work", "planned_work_date": "2026-12-01"},
                            format="json", HTTP_IDEMPOTENCY_KEY="http")
        self.assertEqual(response.status_code, 201, response.data)
        self.assertIn("no-store", response["Cache-Control"])
        self.assertNotIn("organizational", str(response.data))

    def test_date_is_required_and_does_not_expire_pending_participation(self):
        for value in (None, "2026-12-01", datetime(2026, 12, 1), 1):
            with self.subTest(value=value), self.assertRaises(ValidationError):
                self.propose(planned_work_date=value)
        item, _ = self.propose(planned_work_date=date(2020, 1, 1))
        self.assertEqual(self.read()["planned_work_date"], date(2020, 1, 1))
        item.refresh_from_db()
        self.assertEqual(item.state, "pending")
        with self.assertRaises(IdempotencyConflict):
            self.propose(planned_work_date=date(2020, 1, 2))
        accepted, _ = self.respond(item)
        self.assertEqual(accepted.state, "active")
        assert_treatment_medical_basis(actor=self.recipient, business=self.business,
            patient_id=self.patient.pk, participation_id=item.pk)
