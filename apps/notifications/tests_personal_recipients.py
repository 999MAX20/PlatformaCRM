from unittest.mock import patch

from django.test import TestCase
from django.utils import timezone

from apps.accounts.models import User
from apps.businesses.models import Business, BusinessMember
from apps.notifications.models import Notification, NotificationRecipient
from apps.notifications.recipients import create_recipient_states


class PersonalRecipientPersistenceTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(username="receipt-owner", email="receipt-owner@example.com")
        self.staff = User.objects.create_user(username="receipt-staff", email="receipt-staff@example.com")
        self.other = User.objects.create_user(username="receipt-other", email="receipt-other@example.com")
        self.business = Business.objects.create(name="Receipt business", slug="receipt-business", owner=self.owner)
        BusinessMember.objects.create(business=self.business, user=self.staff, role="specialist")
        self.foreign = Business.objects.create(name="Foreign business", slug="receipt-foreign", owner=self.other)

    def notification(self, **kwargs):
        return Notification.objects.create(business=self.business, text="Synthetic", send_at=timezone.now(), **kwargs)

    def test_shared_audience_is_fixed_and_includes_owner_without_membership(self):
        notification = self.notification()
        self.assertSetEqual(set(notification.recipient_states.values_list("user_id", flat=True)), {self.owner.pk, self.staff.pk})
        BusinessMember.objects.create(business=self.business, user=self.other, role="specialist")
        notification.text = "Updated"
        notification.save()
        create_recipient_states([notification])
        self.assertEqual(notification.recipient_states.count(), 2)

    def test_personal_and_external_channel_audiences(self):
        personal = self.notification(recipient=self.staff)
        foreign = self.notification(recipient=self.other)
        external = self.notification(channel="email")
        self.assertEqual(list(personal.recipient_states.values_list("user_id", flat=True)), [self.staff.pk])
        self.assertFalse(foreign.recipient_states.exists())
        self.assertFalse(external.recipient_states.exists())

    def test_inactive_members_and_disabled_users_do_not_receive(self):
        BusinessMember.objects.filter(business=self.business, user=self.staff).update(is_active=False)
        self.assertEqual(self.notification().recipient_states.count(), 1)
        BusinessMember.objects.filter(business=self.business, user=self.staff).update(is_active=True)
        User.objects.filter(pk=self.staff.pk).update(is_active=False)
        self.assertEqual(self.notification().recipient_states.count(), 1)

    def test_bulk_producers_have_personal_state_and_idempotent_repair(self):
        rows = Notification.objects.bulk_create([
            Notification(business=self.business, recipient=self.staff, text="One", send_at=timezone.now()),
            Notification(business=self.business, text="Two", send_at=timezone.now()),
        ])
        self.assertEqual(NotificationRecipient.objects.count(), 3)
        create_recipient_states(rows)
        self.assertEqual(NotificationRecipient.objects.count(), 3)

    def test_legacy_state_initializes_without_open_or_acknowledgement(self):
        now = timezone.now()
        notification = self.notification(read_at=now)
        for state in notification.recipient_states.all():
            self.assertEqual(state.read_at, now)
            self.assertEqual(state.received_at, notification.created_at)
            self.assertIsNone(state.opened_at)
            self.assertIsNone(state.acknowledged_at)

    def test_single_creation_rolls_back_with_recipient_failure(self):
        with patch("apps.notifications.recipients.create_recipient_states", side_effect=RuntimeError("synthetic")):
            with self.assertRaises(RuntimeError):
                self.notification()
        self.assertFalse(Notification.objects.exists())

    def test_bulk_creation_rolls_back_with_recipient_failure(self):
        with patch("apps.notifications.recipients.create_recipient_states", side_effect=RuntimeError("synthetic")):
            with self.assertRaises(RuntimeError):
                Notification.objects.bulk_create([
                    Notification(business=self.business, text="Synthetic", send_at=timezone.now()),
                ])
        self.assertFalse(Notification.objects.exists())
