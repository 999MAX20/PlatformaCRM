from unittest.mock import patch

from django.test import TestCase, override_settings
from rest_framework.exceptions import PermissionDenied

from apps.ai_core import tests_voice_schedule as fixtures
from apps.ai_core.conversation_actions import confirm_turn
from apps.ai_core.conversation_state import start_turn
from apps.ai_core.models import ApprovalRequest
from apps.ai_core.services import process_ai_job
from apps.ai_core.tests_conversation_execution import action_route, create_step, output
from apps.ai_core.tool_registry import tool_call_fingerprint
from apps.scheduling.models import Appointment


@override_settings(AI_PROVIDER="mock", AI_ENABLED=True, VOICE_INPUT_ENABLED=True, AI_QUEUE_LIVE_REQUESTS=False)
class VoiceAppointmentReviewTests(TestCase):
    setUp = fixtures.VoiceScheduleConversationTests.setUp
    visit = fixtures.VoiceScheduleConversationTests.visit
    draft = fixtures.VoiceScheduleConversationTests.draft
    run_turn = fixtures.VoiceScheduleConversationTests.run_turn

    def prepare_transition(self, action):
        self.run_turn(self.draft())
        appointment = Appointment.objects.get()
        values = {"start_at": "2030-11-08T13:00:00Z"} if action == "reschedule" else {}
        message = "Перенеси запись на 8 ноября 2030 в 13:00" if action == "reschedule" else "Отмени запись по просьбе клиента"
        message = message.replace("запись", f"запись #{appointment.pk}")
        turn, job = start_turn(conversation_id=self.thread.pk, user=self.owner, message=message,
            idempotency_key=action, context={"execution": "direct"})
        step = {**create_step("appointments", request=message), "operation": "transition", "target_id": appointment.pk}
        proposal = {"tool": "crm_transition", "arguments": {"entity": "appointments", "entity_id": appointment.pk,
            "action": action, "values": values, "reason": "По просьбе клиента"}, "question": ""}
        with patch("apps.ai_core.services.generate_text", side_effect=[action_route(step), output(proposal)]):
            process_ai_job(job.pk)
        turn.refresh_from_db()
        self.assertEqual(turn.status, "awaiting_confirmation", (turn.error_code, turn.response))
        log = turn.tool_calls.get()
        self.assertEqual(log.input_json["preview"]["client_name"], "Иван Иванов")
        self.assertIn({"entity": "clients", "id": appointment.client_id}, turn.references_json)
        self.assertIn("2030-11-07", log.input_json["preview"]["start_at"])
        return appointment, turn, dict(conversation_id=self.thread.pk, turn_id=turn.pk, user=self.owner,
            expected_revision=turn.sequence, actions=[{"id": log.pk, "fingerprint": tool_call_fingerprint(log)}])

    def test_reschedule_waits_for_exact_review_and_replays_once(self):
        appointment, turn, args = self.prepare_transition("reschedule")
        with self.assertRaises(PermissionDenied):
            confirm_turn(**args, _direct=True)
        appointment.refresh_from_db()
        self.assertEqual(appointment.start_at.day, 7)
        done, _ = confirm_turn(**args)
        self.assertEqual(done.status, "completed", done.error_code)
        appointment.refresh_from_db()
        self.assertEqual((appointment.start_at.day, appointment.start_at.hour), (8, 13))
        count = ApprovalRequest.objects.count()
        confirm_turn(**args)
        self.assertEqual(ApprovalRequest.objects.count(), count)

    def test_discard_cancel_proposal_keeps_appointment(self):
        from apps.ai_core.conversation_state import cancel_turn
        appointment, turn, args = self.prepare_transition("cancel")
        status = appointment.status
        with self.assertRaises(PermissionDenied):
            confirm_turn(**args, _direct=True)
        cancel_turn(conversation_id=self.thread.pk, turn_id=turn.pk, user=self.owner)
        appointment.refresh_from_db()
        self.assertEqual(appointment.status, status)

    def test_reviewed_cancel_executes(self):
        appointment, turn, args = self.prepare_transition("cancel")
        done, _ = confirm_turn(**args)
        self.assertEqual(done.status, "completed", done.error_code)
        appointment.refresh_from_db()
        self.assertEqual(appointment.status, "cancelled")

    def test_client_scope_revocation_redacts_transition_preview(self):
        from apps.ai_core.conversation_views import turn_payload
        from apps.clients.models import Client
        appointment, turn, _ = self.prepare_transition("cancel")
        Client.objects.filter(pk=appointment.client_id).update(business=self.other_business)
        rendered = turn_payload(turn, self.owner)
        self.assertTrue(rendered["redacted"])
        self.assertEqual(rendered["actions"], [])
        self.assertNotIn("Иван Иванов", str(rendered))
