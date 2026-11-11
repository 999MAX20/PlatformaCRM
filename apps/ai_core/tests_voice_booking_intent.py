from unittest.mock import patch

from django.test import SimpleTestCase, TestCase, override_settings
from rest_framework.exceptions import PermissionDenied

from apps.ai_core.conversation_state import start_turn
from apps.ai_core.services import process_ai_job
from apps.ai_core.tests_conversation_execution import action_route, create_step, create_plan, output
from apps.ai_core import tests_voice_schedule as schedule_fixtures
from apps.ai_core.voice_policy import validate_voice_plan, voice_booking_request
from apps.clients.models import Client
from apps.scheduling.models import Appointment


class BookingInstructionTests(SimpleTestCase):
    def test_explicit_booking_phrasings(self):
        for message in (
            "Запиши нового клиента Павла Тестового на консультацию Канни 7 ноября 2026 года в 9 часов",
            "Пожалуйста, запишите Павла к Анне завтра в 9",
            "Создай запись для нового клиента",
            "Book a new client Paul for a consultation with Anna tomorrow at nine",
            "Schedule an appointment for Paul",
            "Павелді консультацияға ертең сағат тоғызға жазыңыз",
        ):
            with self.subTest(message=message):
                self.assertTrue(voice_booking_request(message))

    def test_standalone_client_task_note_and_negation_are_not_booking_authority(self):
        for message in (
            "Создай нового клиента Павла Тестового",
            "Create client Paul with notes: book a visit with Anna",
            "Создай задачу: запиши Павла на консультацию",
            "Добавь заметку: запиши Павла к Анне",
            "Do not book an appointment, create client Paul only",
            "Не запиши Павла к Анне, создай только клиента",
        ):
            with self.subTest(message=message):
                self.assertFalse(voice_booking_request(message))

    def test_incomplete_stored_plan_cannot_execute_as_client_only(self):
        with self.assertRaises(PermissionDenied):
            validate_voice_plan({"origin": "voice"}, {"steps": [create_step("clients")]},
                                "Запиши Павла на консультацию")
        validate_voice_plan({}, {"steps": [create_step("clients")]}, "Запиши Павла на консультацию")


@override_settings(AI_PROVIDER="mock", AI_ENABLED=True, VOICE_INPUT_ENABLED=True, AI_QUEUE_LIVE_REQUESTS=False)
class BookingIntentConversationTests(TestCase):
    setUp = schedule_fixtures.VoiceScheduleConversationTests.setUp
    visit = schedule_fixtures.VoiceScheduleConversationTests.visit
    draft = schedule_fixtures.VoiceScheduleConversationTests.draft

    def run_incomplete_route(self, draft, *, key="booking", message="Запиши нового клиента Ивана Иванова на Consultation к Anna 7 ноября 2030 в 12:00"):
        turn, job = start_turn(conversation_id=self.thread.pk, user=self.owner, message=message,
                              idempotency_key=key, context={"execution": "direct"})
        if job:
            with patch("apps.ai_core.services.generate_text", side_effect=[
                    action_route(create_step("clients", request=message)), output(draft)]):
                process_ai_job(job.pk)
        turn.refresh_from_db()
        turn = schedule_fixtures.confirm_prepared_creation(turn, self.owner)
        return turn

    def booking_draft(self):
        draft = self.draft()
        draft["visits"][0]["time_text"] = "12:00"
        return draft

    def test_client_only_router_output_creates_actual_visit_and_replay_once(self):
        turn = self.run_incomplete_route(self.booking_draft())
        self.assertEqual(turn.status, "completed", turn.error_code)
        self.assertEqual(turn.tool_calls.get().tool_name, "crm_schedule")
        self.assertEqual(Appointment.objects.get().client_id, Client.objects.get().pk)
        self.assertEqual(turn.response, "Создано записей: 1.")
        self.assertEqual(self.run_incomplete_route(self.booking_draft()).pk, turn.pk)
        self.assertEqual(Appointment.objects.count(), 1)
        self.assertEqual(Client.objects.count(), 1)

    def test_missing_time_clarifies_without_client_or_success(self):
        draft = self.booking_draft()
        draft["visits"][0].update(time="", time_text="")
        turn = self.run_incomplete_route(draft, message="Запиши нового клиента Ивана Иванова на Consultation к Anna 7 ноября 2030")
        self.assertEqual(turn.status, "clarifying", turn.error_code)
        self.assertIn("время", turn.response)
        self.assertFalse(Client.objects.exists())
        self.assertFalse(Appointment.objects.exists())
        self.assertFalse(turn.tool_calls.exists())

    def test_unavailable_time_does_not_report_success_or_create_client(self):
        draft = self.booking_draft()
        draft["visits"][0].update(time="02:00", time_text="02:00")
        turn = self.run_incomplete_route(draft, message="Запиши Ивана на Consultation к Anna 7 ноября 2030 в 02:00")
        self.assertEqual(turn.status, "clarifying", turn.error_code)
        self.assertFalse(Client.objects.exists())
        self.assertFalse(Appointment.objects.exists())

    def test_standalone_client_creation_reports_only_client(self):
        turn, job = start_turn(conversation_id=self.thread.pk, user=self.owner,
            message="Создай клиента Ивана Иванова", idempotency_key="client", context={"execution": "direct"})
        with patch("apps.ai_core.services.generate_text", side_effect=[
                action_route(create_step("clients")), create_plan("clients", full_name="Иван Иванов")]):
            process_ai_job(job.pk)
        turn.refresh_from_db()
        self.assertEqual(turn.status, "awaiting_confirmation")
        self.assertFalse(Client.objects.exists())
        turn = schedule_fixtures.confirm_prepared_creation(turn, self.owner)
        self.assertEqual(turn.status, "completed", turn.error_code)
        self.assertEqual(turn.response, "Клиент создан.")
        self.assertEqual(Client.objects.count(), 1)
        self.assertFalse(Appointment.objects.exists())

    def test_successful_tool_without_persisted_visit_cannot_report_success(self):
        result = {"entity": "appointments", "entity_id": 999999,
                  "records": [{"entity": "appointments", "entity_id": 999999, "created": True}]}
        with patch("apps.ai_core.voice_schedule_commands.execute_schedule", return_value=result):
            turn = self.run_incomplete_route(self.booking_draft())
        self.assertEqual(turn.status, "failed")
        self.assertEqual(turn.error_code, "action_failed")
        self.assertEqual(turn.response, "")
        self.assertFalse(Appointment.objects.exists())
        self.assertFalse(Client.objects.exists())

    def test_incomplete_execution_result_rolls_back_created_client_and_visit(self):
        from apps.ai_core.voice_schedule_commands import execute_schedule

        def incomplete_result(log, user):
            result = execute_schedule(log, user)
            result["records"] = []
            return result

        with patch("apps.ai_core.voice_schedule_commands.execute_schedule", side_effect=incomplete_result):
            turn = self.run_incomplete_route(self.booking_draft())
        self.assertEqual(turn.status, "failed")
        self.assertEqual(turn.error_code, "action_failed")
        self.assertEqual(turn.response, "")
        self.assertFalse(Appointment.objects.exists())
        self.assertFalse(Client.objects.exists())

    def test_success_response_uses_employee_language(self):
        from apps.accounts.models import UserPreference
        UserPreference.objects.update_or_create(user=self.owner, defaults={"language": "en"})
        turn = self.run_incomplete_route(self.booking_draft())
        self.assertEqual(turn.status, "completed", turn.error_code)
        self.assertEqual(turn.response, "Appointments created: 1.")

    def test_success_response_in_kazakh(self):
        from apps.accounts.models import UserPreference
        UserPreference.objects.update_or_create(user=self.owner, defaults={"language": "kk"})
        turn = self.run_incomplete_route(self.booking_draft())
        self.assertEqual(turn.status, "completed", turn.error_code)
        self.assertEqual(turn.response, "Құрылған жазбалар саны: 1.")
