from unittest.mock import patch

from django.test import TestCase, override_settings
from rest_framework.exceptions import NotFound, PermissionDenied, ValidationError
from rest_framework.test import APIClient

from apps.core.domain_errors import IdempotencyConflict
from apps.core.idempotency import canonical_request_hash
from apps.core.models import CRMCommandIdempotency
from apps.notifications.models import Notification
from apps.scheduling.models import Appointment
from . import tests_participation_notifications as fixtures
from .identity_crypto import MedicalDataUnavailable, MedicalKeyUnavailable
from .models import MedicalAuditEvent, TreatmentParticipation
from .participation_notice_reads import read_participation_notification
from .participation_reads import read_own_participations
from .tests_patient_services import key


@override_settings(MEDICAL_DATA_KEYS={"test": key(7)}, MEDICAL_DATA_ACTIVE_KEY_ID="test",
                   MEDICAL_IDENTITY_INDEX_KEY=key(8))
class ParticipationDeclineTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        fixtures.ParticipationNotificationTests.setUpTestData.__func__(cls)

    propose = fixtures.ParticipationNotificationTests.propose
    respond = fixtures.ParticipationNotificationTests.respond

    def decline(self, item, **values):
        return self.respond(item, **({"decision": "decline", "reason": "Synthetic confidential refusal"} | values))

    def reply(self):
        return read_participation_notification(actor=self.doctor, business_id=self.business.pk,
            notification_id=Notification.objects.get(recipient=self.doctor).pk)

    def test_reason_required_and_accept_cannot_silently_discard_text(self):
        item, _ = self.propose()
        for reason in ("", " \n\t", None, 42, "x" * 2001):
            with self.subTest(reason=reason), self.assertRaises(ValidationError):
                self.decline(item, reason=reason)
        with self.assertRaises(ValidationError):
            self.respond(item, reason="Unexpected reason")
        item.refresh_from_db()
        self.assertEqual((item.state, item.revision, item.decline_reason_encrypted), ("pending", 1, ""))
        self.assertEqual(Notification.objects.count(), 1)

    def test_pre_reason_acceptance_receipt_can_still_be_replayed(self):
        item, _ = self.propose()
        self.respond(item)
        old_payload = {"patient": self.patient.pk, "participation": item.pk,
                       "expected_revision": 1, "decision": "accept"}
        CRMCommandIdempotency.objects.filter(action="medical.participation.respond").update(
            request_hash=canonical_request_hash(old_payload))
        self.assertTrue(self.respond(item)[1])
        self.assertEqual(Notification.objects.count(), 2)

    def test_encrypted_reason_replay_and_initiator_only_projection(self):
        item, _ = self.propose()
        result, replayed = self.decline(item)
        self.assertFalse(replayed)
        self.assertNotIn("confidential", result.decline_reason_encrypted)
        self.assertTrue(self.decline(item)[1])
        with self.assertRaises(IdempotencyConflict):
            self.decline(item, reason="Different reason")
        self.assertEqual(self.reply()["participation"]["decline_reason"], "Synthetic confidential refusal")
        own = read_own_participations(actor=self.recipient, business_id=self.business.pk)
        self.assertIsNone(own["results"][0]["decline_reason"])
        for model in (MedicalAuditEvent, CRMCommandIdempotency, Notification):
            self.assertNotIn("confidential", str(list(model.objects.values())))
        self.assertEqual(Notification.objects.count(), 2)
        self.appointment.refresh_from_db()
        self.assertEqual(self.appointment.status, "created")

    def test_reason_does_not_bypass_current_source_access(self):
        item, _ = self.propose()
        self.decline(item)
        Appointment.objects.filter(pk=self.appointment.pk).update(resource=None)
        with self.assertRaises(NotFound):
            self.reply()

    def test_owner_and_proposer_cannot_decline_for_recipient(self):
        item, _ = self.propose()
        for actor in (self.owner, self.doctor):
            with self.subTest(actor=actor.pk), self.assertRaises(PermissionDenied):
                self.decline(item, actor=actor)
        self.assertEqual(Notification.objects.count(), 1)

    def test_key_failure_rolls_back_then_same_command_recovers(self):
        item, _ = self.propose()
        with patch("apps.medical.participation_services.encrypt_medical_value", side_effect=MedicalKeyUnavailable()):
            with self.assertRaises(MedicalKeyUnavailable):
                self.decline(item)
        item.refresh_from_db()
        self.assertEqual((item.state, item.revision, item.decline_reason_encrypted), ("pending", 1, ""))
        self.assertFalse(MedicalAuditEvent.objects.filter(action="participation_declined").exists())
        self.assertEqual(Notification.objects.count(), 1)
        self.assertFalse(self.decline(item)[1])

    def test_corruption_fails_closed_and_legacy_missing_reason_stays_null(self):
        item, _ = self.propose()
        self.decline(item)
        TreatmentParticipation.objects.filter(pk=item.pk).update(decline_reason_encrypted="corrupt")
        with self.assertRaises(MedicalDataUnavailable):
            self.reply()
        TreatmentParticipation.objects.filter(pk=item.pk).update(decline_reason_encrypted="")
        self.assertIsNone(self.reply()["participation"]["decline_reason"])

    def test_http_requires_reason_and_keeps_command_response_private(self):
        item, _ = self.propose()
        api = APIClient()
        api.force_authenticate(self.recipient)
        url = f"/api/medical/participations/{item.pk}/respond/"
        body = {"business_id": self.business.pk, "patient_id": self.patient.pk,
                "expected_revision": 1, "decision": "decline"}
        self.assertEqual(api.post(url, body, format="json", HTTP_IDEMPOTENCY_KEY="http").status_code, 400)
        response = api.post(url, body | {"reason": "Synthetic HTTP refusal"}, format="json", HTTP_IDEMPOTENCY_KEY="http")
        self.assertEqual(response.status_code, 200, response.data)
        self.assertIn("no-store", response["Cache-Control"])
        self.assertNotIn("refusal", str(response.data))
