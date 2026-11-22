from unittest.mock import patch

from django.test import TestCase, override_settings
from rest_framework.exceptions import NotFound, PermissionDenied
from rest_framework.test import APIClient

from apps.businesses.models import RolePermission
from apps.notifications.models import Notification
from apps.scheduling.models import Appointment
from . import tests_participation_notifications as fixtures
from .audit import MedicalAuditUnavailable
from .models import MedicalAuditEvent
from .participation_notice_reads import read_participation_notification
from .tests_patient_services import key


@override_settings(MEDICAL_DATA_KEYS={"test": key(7)}, MEDICAL_DATA_ACTIVE_KEY_ID="test",
                   MEDICAL_IDENTITY_INDEX_KEY=key(8))
class ParticipationNoticeReadTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        fixtures.ParticipationNotificationTests.setUpTestData.__func__(cls)

    propose = fixtures.ParticipationNotificationTests.propose
    respond = fixtures.ParticipationNotificationTests.respond

    def read(self, notification, **values):
        return read_participation_notification(**(dict(actor=self.recipient, business_id=self.business.pk,
            notification_id=notification.pk) | values))

    def test_incoming_context_is_current_audited_and_has_no_proposer_source(self):
        item, _ = self.propose()
        notification = Notification.objects.get()
        first = self.read(notification)
        self.assertEqual(first["participation"]["id"], item.pk)
        self.assertEqual(first["participation"]["state"], "pending")
        self.assertEqual(first["direction"], "incoming")
        self.assertIsNone(first["source_appointment_id"])
        self.respond(item)
        self.assertEqual(self.read(notification)["participation"]["state"], "active")
        self.assertEqual(MedicalAuditEvent.objects.filter(action="read", participation=item).count(), 2)
        self.assertNotIn("Synthetic private reason", str(first))

    def test_reply_context_uses_current_source_and_disappears_after_its_loss(self):
        item, _ = self.propose()
        self.respond(item)
        reply = Notification.objects.get(recipient=self.doctor)
        data = self.read(reply, actor=self.doctor)
        self.assertEqual(data["direction"], "outgoing")
        self.assertEqual(data["source_appointment_id"], self.appointment.pk)
        Appointment.objects.filter(pk=self.appointment.pk).update(resource=None)
        with self.assertRaises(NotFound):
            self.read(reply, actor=self.doctor)

    def test_other_actor_owner_unknown_notice_and_denied_action_do_not_open_context(self):
        item, _ = self.propose()
        notification = Notification.objects.get()
        with self.assertRaises(NotFound):
            self.read(notification, actor=self.doctor)
        with self.assertRaises(PermissionDenied):
            self.read(notification, actor=self.owner)
        with self.assertRaises(NotFound):
            self.read(notification, notification_id=9999999)
        self.respond(item)
        reply = Notification.objects.get(recipient=self.doctor)
        RolePermission.objects.filter(business_role=self.role, resource="medical_participation",
                                      action="create").update(is_allowed=False)
        with self.assertRaises(NotFound):
            self.read(reply, actor=self.doctor)

    def test_context_api_is_strict_private_and_audit_failure_is_closed(self):
        self.propose()
        notification = Notification.objects.get()
        api = APIClient()
        api.force_authenticate(self.recipient)
        url = "/api/medical/participations/notification-context/"
        params = {"business_id": self.business.pk, "notification_id": notification.pk}
        response = api.get(url, params)
        self.assertEqual(response.status_code, 200, response.data)
        self.assertIn("no-store", response["Cache-Control"])
        self.assertEqual(api.get(url, params | {"patient_id": self.patient.pk}).status_code, 400)
        self.assertEqual(api.get(url, params | {"notification_id": 0}).status_code, 400)
        count = MedicalAuditEvent.objects.filter(action="read").count()
        with patch("apps.medical.participation_reads.write_patient_audit", side_effect=MedicalAuditUnavailable()):
            response = api.get(url, params)
        self.assertEqual(response.status_code, 503)
        self.assertIn("no-store", response["Cache-Control"])
        self.assertEqual(MedicalAuditEvent.objects.filter(action="read").count(), count)
