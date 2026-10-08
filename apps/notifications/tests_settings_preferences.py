from types import SimpleNamespace

from django.test import TestCase
from django.utils import timezone

from apps.accounts.models import User
from apps.bots.inbox_service import create_inbound_message_notifications
from apps.bots.models import Bot, BotConversation, BotMessage
from apps.businesses.assignment_notifications import create_assignment_notifications
from apps.businesses.models import Business, BusinessMember
from apps.clients.models import Client
from apps.leads.models import Lead
from apps.leads.services import notify_responsible
from apps.notifications.models import Notification, NotificationPreference
from apps.notifications.routing import create_role_notification
from apps.scheduling.services import notify_appointment_responsible


class SettingsPreferenceConsumersTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(username="preference-owner", email="pref-owner@example.test")
        self.user = User.objects.create_user(username="preference-user", email="pref-user@example.test")
        self.business = Business.objects.create(owner=self.owner, name="Preferences", slug="preference-consumers")
        BusinessMember.objects.create(business=self.business, user=self.user, role="operator")
        self.customer = Client.objects.create(business=self.business, full_name="Customer")

    def disable(self, category, **overrides):
        return NotificationPreference.objects.create(business=self.business, user=self.user,
                                                     category=category, in_app_enabled=False, **overrides)

    def test_assignment_preferences_filter_each_recipient(self):
        self.disable("tasks")
        rows = create_assignment_notifications(business=self.business, previous_user=self.owner,
            new_user=self.user, text="Assigned", action_url="/app/tasks")
        self.assertEqual([row.recipient_id for row in rows], [self.owner.pk])

    def test_sales_preference_applies_to_leads_and_appointments(self):
        lead = Lead.objects.create(business=self.business, client=self.customer, responsible_user=self.user)
        appointment = SimpleNamespace(business=self.business, lead=lead, resource=None)
        self.disable("sales")
        self.assertIsNone(notify_responsible(lead, "Lead assigned"))
        self.assertIsNone(notify_appointment_responsible(appointment, "Appointment assigned"))
        self.assertFalse(Notification.objects.exists())

    def test_inbox_normal_suppressed_but_handoff_high_retained(self):
        bot = Bot.objects.create(business=self.business, name="Inbox")
        conversation = BotConversation.objects.create(business=self.business, bot=bot,
            client=self.customer, assigned_to=self.user, external_user_id="visitor")
        message = BotMessage.objects.create(conversation=conversation, direction="inbound", text="Hello")
        self.disable("sales")
        self.assertEqual(create_inbound_message_notifications(conversation, message), [])
        conversation.handoff_required = True
        self.assertEqual(len(create_inbound_message_notifications(conversation, message)), 1)
        self.assertEqual(Notification.objects.get().priority, "high")

    def test_all_categories_are_business_and_user_scoped_with_urgent_bypass(self):
        foreign = Business.objects.create(owner=self.owner, name="Other", slug="pref-other")
        for category in Notification.Categories.values:
            with self.subTest(category=category):
                preference = self.disable(category)
                kwargs = dict(business=self.business, preferred_user=self.user, text="Notice", category=category)
                self.assertEqual(create_role_notification(**kwargs), [])
                self.assertEqual(len(create_role_notification(**kwargs, priority="urgent")), 1)
                preference.business = foreign
                preference.save()
                self.assertEqual(len(create_role_notification(**kwargs)), 1)
                preference.business = self.business
                preference.user = self.owner
                preference.save()
                self.assertEqual(len(create_role_notification(**kwargs)), 1)
