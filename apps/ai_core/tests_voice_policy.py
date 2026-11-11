from unittest.mock import patch

from django.test import SimpleTestCase, TestCase, override_settings
from rest_framework.exceptions import PermissionDenied

from apps.ai_core.tests_conversation_execution import ConversationExecutionTests, action_route, create_step, create_plan
from apps.ai_core.conversation_state import start_turn, retry_turn
from apps.ai_core.services import process_ai_job
from apps.ai_core.voice_policy import validate_voice_plan, validate_voice_proposal
from apps.tasks.models import Task


@override_settings(AI_PROVIDER="mock", AI_ENABLED=True, AI_QUEUE_LIVE_REQUESTS=False)
class VoicePolicyTests(TestCase):
    setUp = ConversationExecutionTests.setUp
    confirm = ConversationExecutionTests.confirm

    def prepare(self, responses, message="Create Call task"):
        turn, job = start_turn(conversation_id=self.thread.pk, user=self.owner,
            message=message, idempotency_key="voice", context={"origin": "voice"})
        with patch("apps.ai_core.services.generate_text", side_effect=responses):
            process_ai_job(job.pk)
        turn.refresh_from_db()
        return turn

    def test_voice_proposal_requires_click_and_replay_is_once(self):
        turn = self.prepare([action_route(create_step()), create_plan(title="Call")])
        self.assertEqual(turn.status, "awaiting_confirmation", turn.error_code)
        self.assertFalse(Task.objects.exists())
        log = turn.tool_calls.get()
        turn, _ = self.confirm(turn, [log])
        self.assertEqual(turn.status, "completed")
        self.confirm(turn, [log])
        self.assertEqual(Task.objects.count(), 1)

    def test_task_title_with_archive_prepares_confirms_and_replays_once(self):
        title = "Проверить архив документов"
        turn = self.prepare([action_route(create_step()), create_plan(title=title)],
                            message=f"Создай задачу {title}")
        self.assertEqual(turn.status, "awaiting_confirmation", turn.error_code)
        self.assertFalse(Task.objects.exists())
        log = turn.tool_calls.get()
        turn, _ = self.confirm(turn, [log])
        self.assertEqual(turn.status, "completed")
        self.confirm(turn, [log])
        self.assertEqual(list(Task.objects.values_list("title", flat=True)), [title])

    def test_no_show_note_is_text_only_and_requires_confirmation(self):
        from apps.clients.models import Client
        from apps.ai_core.tests_conversation_execution import output
        client = Client.objects.create(business=self.business, full_name="Note target", notes="Before")
        note = "Клиент не пришёл вчера"
        step = {**create_step("clients"), "operation": "update", "target_id": client.pk,
                "request": "Add note to this client"}
        proposal = output({"tool": "crm_update", "arguments": {"entity": "clients",
                           "entity_id": client.pk, "values": {"notes": note}}, "question": ""})
        turn = self.prepare([action_route(step), proposal], message=f"Клиенту #{client.pk} добавь заметку: {note}")
        self.assertEqual(turn.status, "awaiting_confirmation", turn.error_code)
        client.refresh_from_db()
        self.assertEqual(client.notes, "Before")
        turn, _ = self.confirm(turn)
        self.assertEqual(turn.status, "completed")
        client.refresh_from_db()
        self.assertEqual(client.notes, note)

    def test_bulk_and_archive_routes_fail_before_any_proposal(self):
        for steps in ([create_step(), create_step()], [{**create_step(), "operation": "archive"}]):
            with self.subTest(steps=steps), self.assertRaises(PermissionDenied):
                validate_voice_plan({"origin": "voice"}, {"steps": steps})
        validate_voice_plan({"origin": "voice"}, {"steps": [create_step("clients"), create_step("appointments", after=0)]})

    def test_unsupported_model_route_reports_boundary_without_proposals(self):
        turn = self.prepare([action_route({**create_step(), "operation": "archive"})])
        self.assertEqual(turn.status, "failed")
        self.assertEqual(turn.error_code, "voice_action_unavailable")
        self.assertFalse(turn.tool_calls.exists())
        self.assertFalse(Task.objects.exists())

    def test_planner_cannot_substitute_unsafe_operation(self):
        for tool, payload in (("crm_archive", {"entity": "clients"}),
                ("crm_transition", {"entity": "appointments", "action": "no_show"}),
                ("crm_update", {"entity": "clients", "values": {"phone": "123"}}),
                ("crm_create", {"entity": "deals", "values": {}})):
            with self.subTest(tool=tool), self.assertRaises(PermissionDenied):
                validate_voice_proposal({"origin": "voice"}, tool, payload)
        validate_voice_proposal({}, "crm_archive", {"entity": "clients"})

    def test_explicit_delete_or_no_show_cannot_be_reinterpreted_as_cancellation(self):
        plan = {"steps": [{**create_step("appointments"), "operation": "transition", "request": "Cancel appointment"}]}
        for message in ("Не пришёл, удали запись", "Delete the appointment", "Жазбаны өшір"):
            with self.subTest(message=message), self.assertRaises(PermissionDenied):
                validate_voice_plan({"origin": "voice"}, plan, message)
        validate_voice_plan({"origin": "voice"}, {"steps": []}, "Сколько неявок вчера?")
        validate_voice_plan({"origin": "voice"}, {"steps": [create_step("clients")]}, "Создай клиента Удалов")

    def test_confirmation_rechecks_voice_boundary(self):
        turn = self.prepare([action_route(create_step()), create_plan(title="Call")])
        log = turn.tool_calls.get()
        log.tool_name = "crm_archive"
        log.save()
        with self.assertRaises(PermissionDenied):
            self.confirm(turn, [log])
        self.assertFalse(Task.objects.exists())

    def test_linked_client_and_appointment_need_separate_confirmations(self):
        from datetime import datetime, time, timezone
        from apps.clients.models import Client
        from apps.services.models import Service
        from apps.scheduling.models import Resource, WorkingHours, Appointment
        service = Service.objects.create(business=self.business, name="Consultation", duration_minutes=30)
        resource = Resource.objects.create(business=self.business, name="Specialist")
        WorkingHours.objects.create(business=self.business, weekday=0, start_time=time(9), end_time=time(18))
        with patch("django.utils.timezone.now", return_value=datetime(2026, 10, 4, 10, tzinfo=timezone.utc)):
            turn = self.prepare([action_route(create_step("clients"), create_step("appointments", after=0)),
                create_plan("clients", full_name="Voice Mira")], message="Create Voice Mira and book a consultation on October 5 at 10 UTC")
            self.assertEqual(turn.status, "awaiting_confirmation", turn.error_code)
            self.assertFalse(Client.objects.exists())
            self.assertFalse(Appointment.objects.exists())
            turn, job = self.confirm(turn)
            client = Client.objects.get(full_name="Voice Mira")
            self.assertFalse(Appointment.objects.exists())
            with patch("apps.ai_core.services.generate_text", return_value=create_plan("appointments",
                    client=client.pk, service=service.pk, resource=resource.pk, start_at="2026-10-05T10:00:00Z")):
                process_ai_job(job.pk)
            turn.refresh_from_db()
            self.assertEqual(turn.status, "awaiting_confirmation", turn.error_code)
            self.assertFalse(Appointment.objects.exists())
            logs = list(turn.tool_calls.filter(status="suggested"))
            turn, _ = self.confirm(turn, logs)
            self.assertEqual(turn.status, "completed", turn.error_code)
            self.confirm(turn, logs)
            self.assertEqual(Appointment.objects.get().client_id, client.pk)
            self.assertEqual(Client.objects.count(), 1)

    def test_context_rejects_foreign_record_before_turn(self):
        from apps.clients.models import Client
        client = Client.objects.create(business=self.other_business, full_name="Private")
        with self.assertRaises(PermissionDenied):
            start_turn(conversation_id=self.thread.pk, user=self.owner, message="Add note", idempotency_key="foreign",
                context={"origin": "voice", "current_entity": {"entity": "clients", "id": client.pk}})
        self.assertFalse(self.thread.turns.exists())


class VoiceLanguagePolicyTests(SimpleTestCase):
    def test_task_and_note_content_does_not_become_a_forbidden_operation(self):
        context = {"origin": "voice"}
        for message in ("Создай задачу Проверить архив документов", "Add a task: archive documents", "Тапсырма қос: архив"):
            with self.subTest(message=message):
                validate_voice_plan(context, {"steps": [{"entity": "tasks", "operation": "create"}]}, message)
        for entity in ("clients", "tasks", "appointments"):
            for message in ("Добавь заметку: клиент не пришёл вчера", "Add a note: no-show yesterday", "Ескертпе қос: клиент келмеді"):
                with self.subTest(entity=entity, message=message):
                    validate_voice_plan(context, {"steps": [{"entity": entity, "operation": "update"}]}, message)

    def test_content_exception_cannot_authorize_a_different_or_multiple_operation(self):
        for steps, message in (
            ([{"entity": "appointments", "operation": "transition"}], "Добавь заметку: клиент не пришёл"),
            ([{"entity": "appointments", "operation": "transition"}], "Создай задачу удалить запись"),
            ([{"entity": "clients", "operation": "create"}], "Создай задачу Проверить архив"),
            ([{"entity": "tasks", "operation": "create"}], "Удали запись, затем создай задачу"),
            ([{"entity": "tasks", "operation": "create"}], "Delete the appointment"),
            ([{"entity": "tasks", "operation": "create"}] * 2, "Создай задачу Проверить архив"),
        ):
            with self.subTest(message=message, steps=steps), self.assertRaises(PermissionDenied):
                validate_voice_plan({"origin": "voice"}, {"steps": steps}, message)

    def test_explicit_unsupported_intent_is_not_a_valid_cancel_but_names_and_reads_remain_valid(self):
        context = {"origin": "voice"}
        cancel = {"steps": [{"entity": "appointments", "operation": "transition"}]}
        for message in ("Не пришёл, удали запись", "Delete the appointment", "Жазбаны өшір", "Архивируйте запись"):
            with self.subTest(message=message), self.assertRaises(PermissionDenied):
                validate_voice_plan(context, cancel, message)
        validate_voice_plan(context, cancel, "Отмени запись")
        validate_voice_plan(context, {"steps": []}, "Сколько неявок вчера?")
        validate_voice_plan(context, {"steps": [{"entity": "clients", "operation": "create"}]}, "Создай клиента Удалов")
