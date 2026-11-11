from unittest.mock import patch

from django.test import TestCase, override_settings
from rest_framework.exceptions import PermissionDenied, ValidationError

from apps.ai_core import tests as foundation
from apps.ai_core.tests_conversation_execution import action_route, create_step, create_plan, output
from apps.ai_core.conversation_access import create_voice_conversation
from apps.ai_core.conversation_state import start_turn, cancel_turn
from apps.ai_core.tests_voice_schedule import confirm_prepared_creation
from apps.ai_core.services import process_ai_job
from apps.ai_core.models import ApprovalRequest
from apps.tasks.models import Task


@override_settings(AI_PROVIDER="mock", AI_ENABLED=True, VOICE_INPUT_ENABLED=True, AI_QUEUE_LIVE_REQUESTS=False)
class VoiceDirectTests(TestCase):
    def setUp(self):
        foundation.AICoreFoundationTests.setUp(self)
        self.thread = create_voice_conversation(business=self.business, user=self.owner)

    def start(self, **kwargs):
        return start_turn(conversation_id=self.thread.pk, user=self.owner, message="Create Call task",
                          idempotency_key="direct", context={"execution": "direct"}, **kwargs)

    def run_job(self, job, responses=None):
        with patch("apps.ai_core.services.generate_text", side_effect=responses or
                   [action_route(create_step()), create_plan(title="Call")]):
            process_ai_job(job.pk)

    def test_task_submission_waits_for_review_and_executes_once_with_review_audit(self):
        turn, job = self.start()
        self.run_job(job)
        turn.refresh_from_db()
        self.assertEqual(turn.status, "awaiting_confirmation", turn.error_code)
        self.assertFalse(Task.objects.exists())
        self.assertFalse(ApprovalRequest.objects.exists())
        from apps.ai_core.conversation_actions import confirm_turn
        from apps.ai_core.tool_registry import tool_call_fingerprint
        log = turn.tool_calls.get()
        with self.assertRaises(PermissionDenied):
            confirm_turn(conversation_id=self.thread.pk, turn_id=turn.pk, user=self.owner, expected_revision=turn.sequence,
                actions=[{"id": log.pk, "fingerprint": tool_call_fingerprint(log)}], _direct=True)
        turn = confirm_prepared_creation(turn, self.owner)
        self.assertEqual(turn.status, "completed", turn.error_code)
        self.assertEqual(Task.objects.get().title, "Call")
        self.assertEqual(ApprovalRequest.objects.get().payload["authorization"], "review")
        replay, next_job = self.start()
        self.assertEqual(replay.pk, turn.pk)
        self.assertIsNone(next_job)
        self.run_job(job)
        self.assertEqual(Task.objects.count(), 1)

    def test_missing_title_only_clarifies_without_write(self):
        turn, job = self.start()
        self.run_job(job, [action_route(create_step()), output({"tool": None, "arguments": {}, "question": "What task?"})])
        turn.refresh_from_db()
        self.assertEqual(turn.status, "clarifying", turn.error_code)
        self.assertFalse(Task.objects.exists())
        self.assertFalse(ApprovalRequest.objects.exists())

    def test_corrected_kazakh_task_title_is_reviewed_before_write(self):
        turn, job = self.start()
        self.run_job(job, [action_route(create_step()), create_plan(title="Ертән клиентке қынарау шалу")])
        turn.refresh_from_db()
        self.assertEqual(turn.status, "awaiting_confirmation")
        self.assertFalse(Task.objects.exists())
        corrected, job = start_turn(conversation_id=self.thread.pk, user=self.owner,
            message="Create task Ертең клиентке қоңырау шалу", idempotency_key="corrected", context={"execution": "direct"})
        self.run_job(job, [action_route(create_step()), create_plan(title="Ертең клиентке қоңырау шалу")])
        corrected.refresh_from_db(); turn.refresh_from_db()
        self.assertEqual(turn.status, "superseded")
        self.assertEqual(corrected.status, "awaiting_confirmation")
        self.assertFalse(Task.objects.exists())
        confirm_prepared_creation(corrected, self.owner)
        self.assertEqual(Task.objects.get().title, "Ертең клиентке қоңырау шалу")

    def test_cancel_during_model_call_prevents_execution(self):
        turn, job = self.start()
        def response(*args, **kwargs):
            cancel_turn(conversation_id=self.thread.pk, turn_id=turn.pk, user=self.owner)
            return action_route(create_step())
        with patch("apps.ai_core.services.generate_text", side_effect=response):
            process_ai_job(job.pk)
        turn.refresh_from_db()
        self.assertEqual(turn.status, "cancelled")
        self.assertFalse(Task.objects.exists())

    def test_revocation_during_preparation_prevents_execution(self):
        turn, job = self.start()
        def response(*args, **kwargs):
            self.owner.is_active = False
            self.owner.save(update_fields=["is_active"])
            return action_route(create_step())
        with patch("apps.ai_core.services.generate_text", side_effect=response):
            process_ai_job(job.pk)
        turn.refresh_from_db()
        self.assertEqual(turn.status, "failed")
        self.assertFalse(Task.objects.exists())

    def test_audit_failure_rolls_back_and_explicit_retry_executes_once(self):
        turn, job = self.start()
        self.run_job(job)
        turn.refresh_from_db()
        with patch("apps.ai_core.conversation_actions.audit_ai_tool_execution", side_effect=RuntimeError("rollback")), self.assertRaises(RuntimeError):
            confirm_prepared_creation(turn, self.owner)
        turn.refresh_from_db()
        self.assertEqual(turn.status, "awaiting_confirmation")
        self.assertFalse(Task.objects.exists())
        self.assertFalse(ApprovalRequest.objects.exists())
        turn = confirm_prepared_creation(turn, self.owner)
        self.assertEqual(turn.status, "completed", turn.error_code)
        self.assertEqual(Task.objects.count(), 1)

    def test_foreign_context_denied_before_provider(self):
        from apps.clients.models import Client
        client = Client.objects.create(business=self.other_business, full_name="Foreign")
        with self.assertRaises(PermissionDenied):
            start_turn(conversation_id=self.thread.pk, user=self.owner, message="Add note",
                idempotency_key="foreign", context={"execution": "direct", "current_entity": {"entity": "clients", "id": client.pk}})
        self.assertFalse(self.thread.turns.exists())

    def test_direct_api_and_unsupported_delete(self):
        self.api.force_authenticate(self.owner)
        with patch("apps.ai_core.services.generate_text", side_effect=[action_route(create_step()), create_plan(title="Call")]):
            response = self.api.post(f"/api/ai/conversations/{self.thread.pk}/turns/",
                {"message": "Create Call task", "execution": "direct", "idempotency_key": "api"}, format="json")
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data["status"], "awaiting_confirmation")
        self.assertFalse(Task.objects.exists())
        response = self.api.post(f"/api/ai/conversations/{self.thread.pk}/turns/{response.data['id']}/confirm/", {
            "expected_revision": response.data["sequence"],
            "actions": [{"id": action["id"], "fingerprint": action["fingerprint"]} for action in response.data["actions"]],
        }, format="json")
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data["status"], "completed")
        with patch("apps.ai_core.services.generate_text", return_value=action_route({**create_step("clients"), "operation": "archive"})):
            response = self.api.post(f"/api/ai/conversations/{self.thread.pk}/turns/",
                {"message": "Delete client", "execution": "direct", "idempotency_key": "delete"}, format="json")
        self.assertEqual(response.data["status"], "failed")
        self.assertEqual(Task.objects.count(), 1)

    def test_direct_flag_rejected_for_staff_thread(self):
        from apps.bots.lifecycle import create_bot, activate_bot
        from apps.ai_core.conversation_access import create_staff_conversation
        agent = create_bot(validated_data={"business": self.business, "name": "CRM", "scenario": "crm"})
        activate_bot(bot=agent)
        self.thread = create_staff_conversation(business=self.business, agent_id=agent.pk, user=self.owner)
        with self.assertRaises(ValidationError):
            self.start()

    def test_no_approval_permission_blocks_task_confirmation(self):
        from apps.accounts.models import User
        from apps.businesses.models import BusinessMember, BusinessRole, RolePermission
        user = User.objects.create_user(username="voice-limited", email="voice-limited@example.test", password="pass", role="staff")
        role = BusinessRole.objects.create(business=self.business, name="Voice limited")
        for resource, action in (("ai_assistant", "suggest"), ("ai_pipeline", "suggest"), ("tasks", "view"), ("tasks", "create")):
            RolePermission.objects.create(business_role=role, resource=resource, action=action, scope="business", is_allowed=True)
        RolePermission.objects.create(business_role=role, resource="ai_pipeline", action="approve", scope="none", is_allowed=False)
        BusinessMember.objects.create(business=self.business, user=user, role="specialist", business_role=role)
        self.owner = user
        self.thread = create_voice_conversation(business=self.business, user=user)
        turn, job = self.start()
        self.run_job(job)
        turn.refresh_from_db()
        self.assertEqual(turn.status, "awaiting_confirmation")
        with self.assertRaises(PermissionDenied):
            confirm_prepared_creation(turn, self.owner)
        self.assertFalse(Task.objects.exists())
        self.assertFalse(ApprovalRequest.objects.exists())

    def test_linked_new_client_and_appointment_execute_once_after_identity_review(self):
        from datetime import datetime, time, timezone
        from apps.clients.models import Client
        from apps.services.models import Service
        from apps.scheduling.models import Resource, WorkingHours, Appointment
        service = Service.objects.create(business=self.business, name="Consultation", duration_minutes=30)
        resource = Resource.objects.create(business=self.business, name="Specialist")
        WorkingHours.objects.create(business=self.business, weekday=0, start_time=time(9), end_time=time(18))
        calls = []
        def response(*args, **kwargs):
            calls.append(1)
            if len(calls) == 1:
                return action_route(create_step("clients"), create_step("appointments", after=0))
            return output({"client_name": "Voice Mira", "client_phone": "", "client_id": None, "plan": False,
                "visits": [{"date": "2026-10-05", "time": "10:00", "time_text": "10 UTC", "time_basis": "utc", "service": service.name,
                    "specialist": resource.name, "branch": "", "any_resource": False}]})
        with patch("django.utils.timezone.now", return_value=datetime(2026, 10, 4, 10, tzinfo=timezone.utc)):
            turn, job = start_turn(conversation_id=self.thread.pk, user=self.owner,
                message="Create Voice Mira and book a consultation October 5 at 10 UTC", idempotency_key="linked", context={"execution": "direct"})
            with patch("apps.ai_core.services.generate_text", side_effect=response):
                process_ai_job(job.pk)
            turn.refresh_from_db()
            self.assertEqual(turn.status, "awaiting_confirmation")
            self.assertFalse(Client.objects.exists())
            self.assertFalse(Appointment.objects.exists())
            from apps.ai_core.tests_voice_schedule import confirm_prepared_creation
            turn = confirm_prepared_creation(turn, self.owner)
            self.assertEqual(turn.status, "completed", turn.error_code)
            self.assertEqual(Appointment.objects.get().client_id, Client.objects.get().pk)
            self.assertEqual(ApprovalRequest.objects.count(), 1)
            process_ai_job(job.pk)
            self.assertEqual(Client.objects.count(), 1)
            self.assertEqual(Appointment.objects.count(), 1)
