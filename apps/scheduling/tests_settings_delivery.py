from unittest.mock import patch
from datetime import time

from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.bots.models import Bot, BotChannel
from apps.businesses.models import Business, BusinessMember
from apps.clients.models import Client
from apps.integrations.bot_channel_credentials import store_telegram_bot_token
from apps.notifications.channels import available_appointment_channels, preferred_client_delivery_channel
from apps.notifications.models import Notification
from apps.notifications.delivery import claim_notification, deliver_notification
from apps.scheduling.models import Appointment, AppointmentMessageSetting, Resource, WorkingHours
from apps.scheduling.services import ensure_appointment_message_settings, schedule_appointment_followups, schedule_post_service_followup
from apps.services.models import Service


class AppointmentSettingsDeliveryTests(TestCase):
    def test_reschedule_and_cancel_revoke_retry_and_inflight_jobs(self):
        from apps.scheduling.services import reschedule_appointment, cancel_appointment

        resource = Resource.objects.create(business=self.business, name="Test specialist", resource_type="staff")
        appointment = self.make_appointment(resource=resource)
        confirmation, reminder = schedule_appointment_followups(appointment)
        claimed = self.due_claim(confirmation)
        Notification.objects.filter(pk=reminder.pk).update(status="retry_scheduled", next_retry_at=timezone.now())
        new_start = appointment.start_at + timezone.timedelta(days=1)
        for weekday in range(7):
            WorkingHours.objects.create(business=self.business, weekday=weekday, start_time=time(0), end_time=time(23, 59))
        appointment = reschedule_appointment(appointment=appointment, actor=self.owner, start_at=new_start, resource=resource)
        for old in (confirmation, reminder):
            old.refresh_from_db()
            self.assertEqual(old.status, "cancelled")
            self.assertIsNone(old.next_retry_at)
        self.assertEqual(Notification.objects.filter(appointment=appointment, status="pending").count(), 2)
        with patch("apps.notifications.delivery._deliver") as deliver:
            self.assertEqual(deliver_notification(claimed, claimed=True)["status"], "skipped")
        deliver.assert_not_called()
        pending = Notification.objects.filter(appointment=appointment, status="pending").first()
        Notification.objects.filter(pk=pending.pk).update(status="retry_scheduled", next_retry_at=timezone.now())
        cancel_appointment(appointment=appointment, actor=self.owner, reason="Client requested cancellation")
        pending.refresh_from_db()
        self.assertEqual(pending.status, "cancelled")
        self.assertIsNone(pending.next_retry_at)

    def setUp(self):
        self.api = APIClient()
        self.owner = User.objects.create_user(username="message-settings", email="message-settings@example.com")
        self.business = Business.objects.create(owner=self.owner, name="Messages", slug="message-settings")
        BusinessMember.objects.create(business=self.business, user=self.owner, role="owner")
        self.customer = Client.objects.create(business=self.business, full_name="Customer", phone="+77010000000", telegram_id="telegram-id", whatsapp_id="wa-id", email="customer@example.com")
        self.setting = ensure_appointment_message_settings(self.business)[0]
        self.api.force_authenticate(self.owner)
        self.url = f"/api/appointment-message-settings/{self.setting.pk}/"

    def make_appointment(self, **overrides):
        start = timezone.now() + timezone.timedelta(days=3)
        return Appointment.objects.create(business=self.business, client=self.customer,
            service=Service.objects.create(business=self.business, name="Consultation", duration_minutes=30),
            start_at=start, end_at=start + timezone.timedelta(minutes=30), **overrides)

    def due_claim(self, notification):
        Notification.objects.filter(pk=notification.pk).update(send_at=timezone.now() - timezone.timedelta(seconds=1))
        return claim_notification(notification.pk)

    @override_settings(TELEGRAM_ENABLED=True, WHATSAPP_ENABLED=True, EMAIL_BACKEND="django.core.mail.backends.smtp.EmailBackend", EMAIL_HOST="smtp.example.com")
    def test_auto_requires_contact_and_usable_active_channel(self):
        self.assertEqual(preferred_client_delivery_channel(self.customer), "email")
        bot = Bot.objects.create(business=self.business, name="Transport", status="active")
        channel = BotChannel.objects.create(bot=bot, channel="telegram", status="active")
        self.assertEqual(preferred_client_delivery_channel(self.customer), "email")
        credential = store_telegram_bot_token(channel, "synthetic-settings-token")
        self.assertEqual(preferred_client_delivery_channel(self.customer), "email")
        credential.connector.status = "connected"
        credential.connector.save(update_fields=["status"])
        self.assertEqual(preferred_client_delivery_channel(self.customer), "telegram")
        credential.expires_at = timezone.now() - timezone.timedelta(seconds=1)
        credential.save(update_fields=["expires_at"])
        self.assertEqual(preferred_client_delivery_channel(self.customer), "email")
        BotChannel.objects.create(bot=bot, channel="whatsapp", status="active", config_json={"provider_mode": "mock", "access_token": "synthetic-token", "phone_number_id": "123"})
        self.assertNotIn("whatsapp", available_appointment_channels(self.business))
        bot.status = "paused"
        bot.save(update_fields=["status"])
        self.assertNotIn("telegram", available_appointment_channels(self.business))

    @override_settings(TELEGRAM_ENABLED=False, WHATSAPP_ENABLED=False, EMAIL_BACKEND="django.core.mail.backends.console.EmailBackend")
    def test_missing_delivery_configuration_falls_back_to_staff_not_sms(self):
        self.assertEqual(preferred_client_delivery_channel(self.customer), "system")
        self.assertEqual(available_appointment_channels(self.business), ["auto", "system"])
        for channel in ("sms", "telegram", "whatsapp", "email"):
            self.assertEqual(self.api.patch(self.url, {"channel_policy": channel}, format="json").status_code, 400)

    def test_invalid_placeholders_are_rejected_and_legacy_sms_can_be_disabled(self):
        for template in ("{unknown}", "{client_name.__class__}", "{client_name[0]}", "{time:bad}", "{client_name", "{client_name!r}"):
            self.assertEqual(self.api.patch(self.url, {"template_text": template}, format="json").status_code, 400)
        self.setting.channel_policy = "sms"
        self.setting.save(update_fields=["channel_policy"])
        self.assertEqual(self.api.patch(self.url, {"is_enabled": False}, format="json").status_code, 200)
        response = self.api.patch(self.url, {"channel_policy": "system", "is_enabled": True, "template_text": "{client_name}: {date} {time}"}, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertIn("available_channels", response.data)

    def test_setting_change_replaces_pending_retry_once_and_preserves_other_scenario(self):
        appointment = self.make_appointment()
        old, reminder = schedule_appointment_followups(appointment)
        old.status = Notification.Statuses.RETRY_SCHEDULED
        old.save(update_fields=["status"])
        payload = {"template_text": "New {client_name} at {time}", "offset_minutes": -60}
        response = self.api.patch(self.url, payload, format="json")
        self.assertEqual(response.status_code, 200, response.data)
        old.refresh_from_db()
        reminder.refresh_from_db()
        self.assertEqual(old.status, "cancelled")
        self.assertEqual(reminder.status, "pending")
        new = Notification.objects.get(appointment=appointment, action_label=old.action_label, status="pending")
        self.assertIn("New Customer", new.text)
        self.assertEqual(new.send_at, appointment.start_at - timezone.timedelta(hours=1))
        count = Notification.objects.count()
        self.assertEqual(self.api.patch(self.url, payload, format="json").status_code, 200)
        self.assertEqual(Notification.objects.count(), count)

    def test_disabling_revokes_claim_before_provider_call(self):
        notification = schedule_appointment_followups(self.make_appointment())[0]
        claimed = self.due_claim(notification)
        self.assertEqual(self.api.patch(self.url, {"is_enabled": False}, format="json").status_code, 200)
        with patch("apps.notifications.delivery._deliver") as deliver:
            result = deliver_notification(claimed, claimed=True)
        self.assertEqual(result["status"], "skipped")
        deliver.assert_not_called()
        notification.refresh_from_db()
        self.assertEqual(notification.status, "cancelled")

    def test_inflight_failure_or_ack_cannot_resurrect_revoked_job(self):
        appointment = self.make_appointment()
        for provider_result in ({"ok": False, "status_code": 503}, {"ok": True, "message_id": "ack"}):
            self.setting.is_enabled = True
            self.setting.save(update_fields=["is_enabled"])
            notification = schedule_appointment_followups(appointment)[0]
            claimed = self.due_claim(notification)
            def finish_after_cancel(_):
                response = self.api.patch(self.url, {"is_enabled": False}, format="json")
                self.assertEqual(response.status_code, 200)
                return provider_result
            with patch("apps.notifications.delivery._deliver", side_effect=finish_after_cancel):
                self.assertEqual(deliver_notification(claimed, claimed=True)["status"], "skipped")
            notification.refresh_from_db()
            self.assertEqual(notification.status, "cancelled")
            self.assertIsNone(notification.next_retry_at)

    def test_audit_failure_rolls_back_setting_and_queued_messages(self):
        notification = schedule_appointment_followups(self.make_appointment())[0]
        with patch("apps.scheduling.message_settings.write_audit_log", side_effect=RuntimeError("audit unavailable")):
            response = self.api.patch(self.url, {"is_enabled": False}, format="json")
        self.assertEqual(response.status_code, 500)
        self.setting.refresh_from_db()
        notification.refresh_from_db()
        self.assertTrue(self.setting.is_enabled)
        self.assertEqual(notification.status, "pending")

    def test_completed_followup_reconciliation_does_not_backfill_old_visits(self):
        appointment = self.make_appointment(status="completed")
        historical = self.make_appointment(status="completed")
        old = schedule_post_service_followup(appointment)
        setting = AppointmentMessageSetting.objects.get(business=self.business, scenario="thank_you")
        response = self.api.patch(f"/api/appointment-message-settings/{setting.pk}/", {"template_text": "Thank you {client_name}"}, format="json")
        self.assertEqual(response.status_code, 200)
        old.refresh_from_db()
        self.assertEqual(old.status, "cancelled")
        self.assertEqual(Notification.objects.filter(appointment=appointment, status="pending").count(), 1)
        self.assertFalse(Notification.objects.filter(appointment=historical).exists())

    def test_foreign_setting_denied_and_cancelled_appointment_skips_delivery(self):
        outsider = User.objects.create_user(username="settings-foreign", email="settings-foreign@example.com")
        self.api.force_authenticate(outsider)
        self.assertEqual(self.api.patch(self.url, {"is_enabled": False}, format="json").status_code, 404)
        appointment = self.make_appointment()
        notification = schedule_appointment_followups(appointment)[0]
        claimed = self.due_claim(notification)
        Appointment.objects.filter(pk=appointment.pk).update(status="cancelled")
        with patch("apps.notifications.delivery._deliver") as deliver:
            self.assertEqual(deliver_notification(claimed, claimed=True)["status"], "cancelled")
        deliver.assert_not_called()
