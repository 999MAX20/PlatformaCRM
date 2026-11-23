from unittest.mock import patch

from django.db import DatabaseError
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied

from apps.core.models import AuditLog
from apps.businesses.models import Business
from apps.notifications.models import Notification, NotificationPreference
from apps.notifications.module_sources import source_projection
from apps.notifications.personal_selectors import personal_states
from .assistant_notifications import ROUTE, notify_assistant_invitation
from .models import AppointmentAssistant, MedicalRoleAssignment
from .participation_notifications import MedicalNotificationUnavailable
from .tests_assistant_invitations import AssistantInvitationTests
from .tests_patient_services import key


@override_settings(MEDICAL_DATA_KEYS={"test": key(7)}, MEDICAL_DATA_ACTIVE_KEY_ID="test",
                   MEDICAL_IDENTITY_INDEX_KEY=key(8))
class AssistantNotificationTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        AssistantInvitationTests.setUpTestData.__func__(cls)

    invite = AssistantInvitationTests.invite

    def visible(self, actor=None, business=None):
        return personal_states(actor=actor or self.assistant, business=business or self.business)

    def test_personal_neutral_notice_once_and_current_route(self):
        item, _ = self.invite()
        notice = Notification.objects.get()
        item.refresh_from_db()
        self.assertEqual(item.invitation_notification_id, notice.pk)
        self.assertEqual(list(notice.recipient_states.values_list("user_id", flat=True)), [self.assistant.pk])
        self.assertEqual((notice.text, notice.client_id, notice.appointment_id, notice.author_id), ("", None, None, None))
        self.assertEqual(source_projection(notice), {
            "message_key": "medical.notifications.assistant_invited", "action_url": ROUTE})
        self.invite()
        self.assertEqual(notify_assistant_invitation(item).pk, notice.pk)
        self.assertEqual(Notification.objects.count(), 1)
        self.assertEqual(self.visible().count(), 1)
        self.assertFalse(self.visible(self.doctor).exists())
        self.assertFalse(self.visible(self.owner).exists())

    def test_preference_does_not_fall_back_to_owner(self):
        NotificationPreference.objects.create(business=self.business, user=self.assistant,
            category="system", in_app_enabled=False)
        item, _ = self.invite()
        self.assertEqual(item.state, "pending")
        self.assertFalse(Notification.objects.exists())

    def test_failure_rolls_back_invitation_audit_and_allows_retry(self):
        with patch("apps.medical.assistant_notifications.Notification.objects.create",
                   side_effect=DatabaseError("synthetic storage failure")), self.assertRaises(MedicalNotificationUnavailable):
            self.invite()
        self.assertFalse(AppointmentAssistant.objects.exists())
        self.assertFalse(AuditLog.objects.filter(entity_type="AppointmentAssistant").exists())
        self.assertFalse(Notification.objects.exists())
        self.assertFalse(self.invite()[1])
        self.assertEqual(Notification.objects.count(), 1)

    def test_current_branch_and_role_revocation_hide_notice(self):
        self.invite()
        self.assertEqual(self.visible().count(), 1)
        self.assistant_role.branches.clear()
        self.assertFalse(self.visible().exists())
        self.assistant_role.branches.add(self.first)
        self.assertEqual(self.visible().count(), 1)
        MedicalRoleAssignment.objects.filter(pk=self.assistant_role.pk).update(revoked_at=timezone.now())
        self.assertFalse(self.visible().exists())

    def test_corrupt_recipient_business_and_route_are_rejected(self):
        self.invite()
        notice = Notification.objects.get()
        foreign = Business.objects.create(owner=self.owner, name="Synthetic other clinic", slug="assistant-notice-other")
        with self.assertRaises(PermissionDenied):
            self.visible(business=foreign)
        for values in ({"recipient": self.owner}, {"business": foreign}, {"action_url": "/app/calendar"}, {"client": self.patient.client}):
            with self.subTest(values=values):
                Notification.objects.filter(pk=notice.pk).update(**values)
                self.assertFalse(self.visible().exists())
                Notification.objects.filter(pk=notice.pk).update(business=self.business, recipient=self.assistant, action_url=ROUTE, client=None)
