from unittest.mock import patch

from django.test import TestCase, override_settings
from rest_framework.exceptions import PermissionDenied

from apps.ai_core import tests_conversation_execution as fixtures
from apps.ai_core.conversation_preparation import prepare_actions
from apps.ai_core.conversation_router import normalize_new_requests, route_turn
from apps.ai_core.conversation_state import start_turn
from apps.ai_core.models import AgentProfile
from apps.leads.models import Lead
from apps.scheduling.models import Appointment


@override_settings(AI_PROVIDER="mock", AI_ENABLED=True, AI_QUEUE_LIVE_REQUESTS=False)
class RequestAppointmentTests(TestCase):
    def setUp(self):
        fixtures.ConversationExecutionTests.setUp(self)

    def test_new_lead_output_asks_appointment_details_without_any_write(self):
        question = fixtures.output({"tool": None, "arguments": {}, "question": "Which specialist and time?"})
        turn, _, _ = fixtures.ConversationExecutionTests.prepare(self,
            [fixtures.action_route(fixtures.create_step("leads", "Create inquiry")), question],
            message="Создай новую заявку")
        self.assertEqual(turn.status, "clarifying", turn.error_code)
        self.assertEqual(turn.plan_json["steps"][0]["entity"], "appointments")
        self.assertFalse(turn.tool_calls.exists())
        self.assertFalse(Lead.objects.exists())
        self.assertFalse(Appointment.objects.exists())

    def test_planner_cannot_return_lead_after_route_normalization(self):
        turn, _, _ = fixtures.ConversationExecutionTests.prepare(self,
            [fixtures.action_route(fixtures.create_step("leads")), fixtures.create_plan("leads", message="Wrong")],
            message="Создай заявку")
        self.assertEqual(turn.status, "failed")
        self.assertFalse(turn.tool_calls.exists())
        self.assertFalse(Lead.objects.exists())

    def test_disabled_appointment_source_does_not_fall_back_to_leads(self):
        profile = AgentProfile.objects.get(bot=self.agent)
        profile.rules_json = {"sources": ["clients", "leads", "tasks"]}
        profile.save()
        with patch("apps.ai_core.services.generate_text", return_value=fixtures.action_route(fixtures.create_step("leads"))):
            with self.assertRaises(PermissionDenied):
                route_turn(thread=self.thread, user=self.owner, message="Create lead", memory={}, context={})
        self.assertFalse(Lead.objects.exists())

    def test_old_pending_plan_is_normalized_before_field_planning(self):
        turn, _ = start_turn(conversation_id=self.thread.pk, user=self.owner,
            message="Завтра в 11:00", idempotency_key="followup")
        plan = {"intent": "actions", "steps": [fixtures.create_step("leads")]}
        with patch("apps.ai_core.conversation_preparation.plan_command", return_value={"question": "Which service?"}) as planner:
            result = prepare_actions(turn, plan, {}, "ru")
        self.assertEqual(planner.call_args.kwargs["entity"], "appointments")
        self.assertEqual(result["plan"]["steps"][0]["entity"], "appointments")
        self.assertEqual(plan["steps"][0]["entity"], "leads")
        self.assertFalse(Lead.objects.exists())

    def test_existing_lead_identity_and_other_steps_are_preserved(self):
        for operation in ("update", "archive", "restore", "transition"):
            with self.subTest(operation=operation):
                step = {"entity": "leads", "operation": operation, "target_id": 17, "after": None}
                plan = {"intent": "actions", "steps": [fixtures.create_step("clients"), step, fixtures.create_step("leads", after=0)]}
                normalize_new_requests(plan)
                self.assertEqual(plan["steps"][1], step)
                self.assertEqual(step["entity"], "leads")
                self.assertEqual(step["target_id"], 17)
                self.assertEqual(plan["steps"][0]["entity"], "clients")
                self.assertEqual(plan["steps"][2]["entity"], "appointments")
                self.assertEqual(plan["steps"][2]["after"], 0)
