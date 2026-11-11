from django.test import TestCase, override_settings
from rest_framework.exceptions import ValidationError

from apps.ai_core import tests_voice_schedule as scheduling_tests
from apps.clients.models import Client
from apps.scheduling.models import Appointment, VisitPlan


@override_settings(AI_PROVIDER="mock", AI_ENABLED=True, VOICE_INPUT_ENABLED=True, AI_QUEUE_LIVE_REQUESTS=False)
class VoiceIdentityCommandTests(TestCase):
    setUp = scheduling_tests.VoiceScheduleCommandTests.setUp
    visit = scheduling_tests.VoiceScheduleCommandTests.visit
    execute = scheduling_tests.VoiceScheduleCommandTests.execute

    def test_conflicting_phone_rejected_without_writes(self):
        client = Client.objects.create(business=self.business, full_name="Иван Иванов", phone="+77011111111")
        self.values["client"]["phone"] = "+77022222222"
        self.values.update(plan=True, visits=[self.visit(7), self.visit(8)])
        with self.assertRaises(ValidationError):
            self.execute()
        self.assertFalse(Appointment.objects.exists())
        self.assertFalse(VisitPlan.objects.exists())
        self.assertEqual(Client.objects.count(), 1)
        client.refresh_from_db()
        self.assertEqual(client.phone, "+77011111111")

    def test_matching_normalized_phone_disambiguates_same_names(self):
        Client.objects.create(business=self.business, full_name="Иван Иванов", phone="+77011111111")
        selected = Client.objects.create(business=self.business, full_name="Иван Иванов", phone="+77022222222")
        self.values["client"]["phone"] = "8 (702) 222-22-22"
        self.execute()
        self.assertEqual(Appointment.objects.get().client_id, selected.pk)

    def test_phone_change_between_preparation_and_execution_blocks_write(self):
        from apps.ai_core.voice_schedule_commands import validate_schedule
        client = Client.objects.create(business=self.business, full_name="Иван Иванов", phone="+77011111111")
        self.values["client"]["phone"] = client.phone
        validate_schedule(business=self.business, user=self.owner, values=self.values)
        client.phone = "+77022222222"
        client.save()
        with self.assertRaises(ValidationError):
            self.execute()
        self.assertFalse(Appointment.objects.exists())

    def test_non_text_phone_is_validation_error_without_writes(self):
        Client.objects.create(business=self.business, full_name="Иван Иванов", phone="+77011111111")
        for phone in (None, 77011111111, [], {}):
            with self.subTest(phone=phone):
                self.values["client"]["phone"] = phone
                with self.assertRaises(ValidationError):
                    self.execute()
        self.assertFalse(Appointment.objects.exists())


@override_settings(AI_PROVIDER="mock", AI_ENABLED=True, VOICE_INPUT_ENABLED=True, AI_QUEUE_LIVE_REQUESTS=False)
class VoiceIdentityConversationTests(TestCase):
    setUp = scheduling_tests.VoiceScheduleConversationTests.setUp
    visit = scheduling_tests.VoiceScheduleConversationTests.visit
    draft = scheduling_tests.VoiceScheduleConversationTests.draft
    run_turn = scheduling_tests.VoiceScheduleConversationTests.run_turn

    def test_conflicting_phone_clarifies_then_explicit_selection_and_replay(self):
        client = Client.objects.create(business=self.business, full_name="Иван Иванов", phone="+77011111111")
        turn = self.run_turn(self.draft(client_phone="+77022222222"))
        self.assertEqual(turn.status, "clarifying", turn.error_code)
        self.assertIn("Телефон не совпадает", turn.response)
        self.assertIn(f"#{client.pk}", turn.response)
        self.assertFalse(turn.tool_calls.exists())
        self.assertFalse(Appointment.objects.exists())
        self.assertEqual(Client.objects.count(), 1)
        selected = self.draft(client_phone="+77022222222", client_id=client.pk)
        completed = self.run_turn(selected, key="choice", message=f"#{client.pk}")
        self.assertEqual(completed.status, "completed", completed.error_code)
        replay = self.run_turn(selected, key="choice", message=f"#{client.pk}")
        self.assertEqual(replay.pk, completed.pk)
        self.assertEqual(Appointment.objects.get().client_id, client.pk)
        client.refresh_from_db()
        self.assertEqual(client.phone, "+77011111111")

    def test_client_without_phone_requires_selection_when_phone_supplied(self):
        Client.objects.create(business=self.business, full_name="Иван Иванов")
        turn = self.run_turn(self.draft(client_phone="+77022222222"))
        self.assertEqual(turn.status, "clarifying", turn.error_code)
        self.assertFalse(Appointment.objects.exists())

    def test_formatted_matching_phone_does_not_require_extra_confirmation(self):
        client = Client.objects.create(business=self.business, full_name="Иван Иванов", phone="+77022222222")
        turn = self.run_turn(self.draft(client_phone="8 (702) 222-22-22"))
        self.assertEqual(turn.status, "completed", turn.error_code)
        self.assertEqual(Appointment.objects.get().client_id, client.pk)

    def test_matching_phone_outside_business_never_selects_foreign_client(self):
        Client.objects.create(business=self.business, full_name="Иван Иванов", phone="+77011111111")
        foreign = Client.objects.create(business=self.other_business, full_name="Иван Иванов", phone="+77022222222")
        turn = self.run_turn(self.draft(client_phone=foreign.phone))
        self.assertEqual(turn.status, "clarifying", turn.error_code)
        self.assertNotIn({"entity": "clients", "id": foreign.pk}, turn.references_json)
        self.assertFalse(Appointment.objects.exists())

    def test_phone_conflict_explained_in_employee_language_without_phone_disclosure(self):
        from apps.ai_core.voice_schedule_planner import resolve_schedule
        client = Client.objects.create(business=self.business, full_name="Иван Иванов", phone="+77011111111")
        for language, expected in (("ru", "Телефон не совпадает"), ("kk", "Телефон нөмірі сәйкес келмейді"),
                                   ("en", "The phone number does not match")):
            with self.subTest(language=language):
                payload, question, references = resolve_schedule(business=self.business, user=self.owner,
                    draft=self.draft(client_phone="+77022222222"), language=language)
                self.assertIsNone(payload)
                self.assertIn(expected, question)
                self.assertNotIn(client.phone, question)
                self.assertIn({"entity": "clients", "id": client.pk}, references)
        self.assertFalse(Appointment.objects.exists())
