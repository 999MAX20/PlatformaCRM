from datetime import timedelta
from unittest.mock import patch

from django.test import TestCase
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied, ValidationError

from apps.bots.models import BotMessage
from apps.bots.safety_policy import validate_safety_policy
from apps.bots.safety_state import admit_message, count_off_topic, reserve_call, reset_behavior_for_staff, usage
from apps.bots import tests_runtime_configuration as fixtures


class CustomerSafetyStateTests(TestCase):
    def setUp(self):
        fixtures.RuntimeConfigurationTests.setUp(self)

    def new_message(self, text="Please tell me the price"):
        return BotMessage.objects.create(conversation=self.conversation, direction="inbound", text=text)

    def test_settings_cannot_disable_protection_or_raise_owner_call_ceiling(self):
        for settings in ({"enabled": False}, {"calls_per_24h": 31}, {"calls_per_24h": True},
                         {"off_topic_handoff_after": 4}, {"allow_first_off_topic": "yes"},
                         {"messages_per_minute": 0}, {"max_message_chars": 999999}):
            with self.subTest(settings=settings), self.assertRaises(ValidationError):
                validate_safety_policy(settings)
        self.assertEqual(validate_safety_policy({})["calls_per_24h"], 30)
        self.assertEqual(validate_safety_policy({"off_topic_handoff_after": 1})["off_topic_handoff_after"], 1)

    def test_call_limit_is_reserved_before_result_and_rolling(self):
        instant = timezone.now()
        with patch("apps.bots.safety_state.timezone.now", return_value=instant):
            for _ in range(30):
                self.assertTrue(reserve_call(conversation=self.conversation, stage="qualification"))
            self.assertFalse(reserve_call(conversation=self.conversation, stage="reply"))
        with patch("apps.bots.safety_state.timezone.now", return_value=instant + timedelta(hours=24, seconds=1)):
            self.assertTrue(reserve_call(conversation=self.conversation, stage="reply"))
        self.conversation.refresh_from_db()
        self.assertEqual(len(self.conversation.ai_safety_state["calls"]), 1)

    def test_settings_lower_limit_applies_to_previously_reserved_calls(self):
        self.assertTrue(reserve_call(conversation=self.conversation, stage="reply"))
        self.bot.settings_json["customer_safety"] = {"calls_per_24h": 1}
        self.bot.save()
        self.assertFalse(reserve_call(conversation=self.conversation, stage="reply"))

    def test_repeated_message_is_free_then_handoff_signal(self):
        first = self.new_message()
        self.assertEqual(admit_message(conversation=self.conversation, message=first), "")
        self.assertEqual(admit_message(conversation=self.conversation, message=first), "")
        second = self.new_message("  PLEASE tell me the PRICE ")
        self.assertEqual(admit_message(conversation=self.conversation, message=second), "duplicate_text")
        third = self.new_message()
        self.assertEqual(admit_message(conversation=self.conversation, message=third), "repeated_messages")

    def test_short_booking_confirmations_do_not_trigger_text_duplicate_rule(self):
        for _ in range(3):
            self.assertEqual(admit_message(conversation=self.conversation, message=self.new_message("Да")), "")

    def test_burst_and_oversized_messages_do_not_need_model(self):
        self.bot.settings_json["customer_safety"] = {"messages_per_minute": 3}
        self.bot.save()
        for text in ("First", "Second", "Third"):
            self.assertEqual(admit_message(conversation=self.conversation, message=self.new_message(text)), "")
        self.assertEqual(admit_message(conversation=self.conversation, message=self.new_message("Fourth")), "message_burst")
        self.assertEqual(admit_message(conversation=self.conversation, message=self.new_message("X" * 4001)), "message_too_long")

    def test_foreign_message_cannot_use_or_change_conversation_state(self):
        from apps.bots.models import BotConversation
        other = BotConversation.objects.create(business=self.business, bot=self.bot, channel="website")
        message = BotMessage.objects.create(conversation=other, direction="inbound", text="Foreign")
        with self.assertRaises(PermissionDenied):
            admit_message(conversation=self.conversation, message=message)
        self.conversation.refresh_from_db()
        self.assertEqual(self.conversation.ai_safety_state, {})

    def test_off_topic_retry_is_counted_once_and_staff_reset_preserves_calls(self):
        first, second = self.new_message(), self.new_message("Another question")
        self.assertEqual(count_off_topic(conversation=self.conversation, message_id=first.pk), 1)
        self.assertEqual(count_off_topic(conversation=self.conversation, message_id=first.pk), 1)
        self.assertEqual(count_off_topic(conversation=self.conversation, message_id=second.pk), 2)
        reserve_call(conversation=self.conversation, stage="reply")
        reset_behavior_for_staff(conversation=self.conversation, actor=self.business.owner)
        self.conversation.refresh_from_db()
        self.assertEqual(self.conversation.ai_safety_state["off_topic_count"], 0)
        self.assertEqual(usage(self.conversation)["calls_used"], 1)

    def test_memory_reset_does_not_reset_safety_state(self):
        from apps.ai_core.inbox_runtime import reset_inbox_memory
        count_off_topic(conversation=self.conversation, message_id=self.message.pk)
        reserve_call(conversation=self.conversation, stage="reply")
        reset_inbox_memory(conversation=self.conversation, actor=self.business.owner)
        self.conversation.refresh_from_db()
        self.assertEqual(self.conversation.ai_safety_state["off_topic_count"], 1)
        self.assertEqual(usage(self.conversation)["calls_used"], 1)

    def test_staff_reset_cannot_bypass_exhausted_limit(self):
        self.bot.settings_json["customer_safety"] = {"calls_per_24h": 1}
        self.bot.save()
        reserve_call(conversation=self.conversation, stage="reply")
        with self.assertRaises(ValidationError):
            reset_behavior_for_staff(conversation=self.conversation, actor=self.business.owner)

    def test_lowered_limit_reports_time_when_enough_calls_actually_expire(self):
        instant = timezone.now()
        for index in range(3):
            with patch("apps.bots.safety_state.timezone.now", return_value=instant + timedelta(seconds=index)):
                reserve_call(conversation=self.conversation, stage="reply")
        self.bot.settings_json["customer_safety"] = {"calls_per_24h": 1}
        self.bot.save()
        self.conversation.refresh_from_db()
        expected = instant + timedelta(hours=24, seconds=2)
        self.assertEqual(timezone.datetime.fromisoformat(usage(self.conversation)["next_call_available_at"]), expected)
