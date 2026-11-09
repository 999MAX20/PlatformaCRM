from unittest.mock import patch

from django.test import TestCase, override_settings
from rest_framework.exceptions import PermissionDenied, ValidationError

from apps.ai_core import tests as foundation
from apps.ai_core.tests_conversation_execution import action_route, create_step, create_plan, output
from apps.ai_core.conversation_access import create_voice_conversation
from apps.ai_core.conversation_state import start_turn, cancel_turn, retry_turn
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

    def test_direct_submission_executes_once_and_binds_audit(self):
        turn, job = self.start()
        self.run_job(job)
        turn.refresh_from_db()
        self.assertEqual(turn.status, "completed", turn.error_code)
        self.assertEqual(Task.objects.get().title, "Call")
        self.assertEqual(ApprovalRequest.objects.get().payload["authorization"], "voice_direct_submission")
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
        with patch("apps.ai_core.conversation_actions.audit_ai_tool_execution", side_effect=RuntimeError("rollback")):
            self.run_job(job)
        turn.refresh_from_db()
        self.assertEqual(turn.status, "failed")
        self.assertFalse(Task.objects.exists())
        self.assertFalse(ApprovalRequest.objects.exists())
        turn, retry = retry_turn(conversation_id=self.thread.pk, turn_id=turn.pk, user=self.owner, idempotency_key="retry")
        self.run_job(retry)
        turn.refresh_from_db()
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

    def test_no_approval_permission_blocks_direct_write(self):
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
        self.assertEqual(turn.status, "failed")
        self.assertEqual(turn.error_code, "access_changed")
        self.assertFalse(Task.objects.exists())
        self.assertFalse(ApprovalRequest.objects.exists())

    def test_linked_client_then_appointment_execute_once_without_second_click(self):
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
            self.assertEqual(turn.status, "completed", turn.error_code)
            self.assertEqual(Appointment.objects.get().client_id, Client.objects.get().pk)
            self.assertEqual(ApprovalRequest.objects.count(), 1)
            process_ai_job(job.pk)
            self.assertEqual(Client.objects.count(), 1)
            self.assertEqual(Appointment.objects.count(), 1)
