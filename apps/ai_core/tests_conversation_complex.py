from unittest.mock import patch

from django.test import TestCase, override_settings

from apps.ai_core import tests_conversation_execution as fixtures
from apps.ai_core.models import AIRequestLog, AIToolCallLog
from apps.ai_core.conversation_router import parse_route
from apps.ai_core.ai_client import AIClientError
from apps.tasks.models import Task


@override_settings(AI_PROVIDER="mock", AI_ENABLED=True, AI_QUEUE_LIVE_REQUESTS=False)
class IndependentActionTests(TestCase):
    setUp = fixtures.ConversationExecutionTests.setUp
    prepare = fixtures.ConversationExecutionTests.prepare
    confirm = fixtures.ConversationExecutionTests.confirm

    def test_router_accepts_ids_from_either_current_scoped_sample_but_not_invented_ids(self):
        route = fixtures.action_route({"entity": "tasks", "operation": "update", "target_id": 99,
            "query": "Duplicate", "request": "Update Duplicate", "after": None})
        context = {"available_records": {}, "fresh_references": [], "crm": {"tasks": [{"id": 99}]}}
        self.assertEqual(parse_route(route.output_text, context)["steps"][0]["target_id"], 99)
        context["crm"]["tasks"] = []
        with self.assertRaises(AIClientError):
            parse_route(route.output_text, context)

    def test_each_planner_receives_its_selected_step_and_creates_once(self):
        first = fixtures.create_step(request='Create task "Check cash" with description "Morning"')
        second = fixtures.create_step(request='Create task "Check delivery" with description "Evening"')
        message = first["request"] + " and " + second["request"]
        turn, _, _ = self.prepare([
            fixtures.action_route(first, second),
            fixtures.create_plan(title="Check cash", description="Morning"),
            fixtures.create_plan(title="Check delivery", description="Evening"),
        ], message=message)
        self.assertEqual(turn.status, "awaiting_confirmation", turn.error_code)
        logs = list(AIRequestLog.objects.filter(prompt_type="crm_action_plan").order_by("pk"))
        self.assertEqual(len(logs), 2)
        for log, selected, sibling in ((logs[0], first, second), (logs[1], second, first)):
            self.assertTrue(log.input_json["user_input"].endswith(selected["request"]))
            self.assertNotIn(sibling["request"], log.input_json["user_input"])
        self.assertTrue(all(log.input_json["command_context"]["original_request"] == message for log in logs))
        self.assertFalse(Task.objects.exists())
        completed, job = self.confirm(turn)
        self.assertIsNone(job)
        self.assertEqual(completed.status, "completed")
        self.assertEqual(set(Task.objects.values_list("title", "description")),
                         {("Check cash", "Morning"), ("Check delivery", "Evening")})
        self.confirm(completed, list(completed.tool_calls.all()))
        self.assertEqual(Task.objects.count(), 2)

    def test_duplicate_output_for_distinct_independent_steps_requires_clarification(self):
        turn, _, _ = self.prepare([
            fixtures.action_route(fixtures.create_step(request="Create One"), fixtures.create_step(request="Create Two")),
            fixtures.create_plan(title="One"), fixtures.create_plan(title="One"),
        ], message="Create One and Two")
        self.assertEqual(turn.status, "clarifying", turn.error_code)
        self.assertTrue(turn.response)
        self.assertFalse(AIToolCallLog.objects.exists())
        self.assertFalse(Task.objects.exists())

    def test_equal_titles_with_different_requested_fields_remain_distinct(self):
        turn, _, _ = self.prepare([
            fixtures.action_route(fixtures.create_step(request="Call Monday"), fixtures.create_step(request="Call Tuesday")),
            fixtures.create_plan(title="Call", description="Monday"),
            fixtures.create_plan(title="Call", description="Tuesday"),
        ], message="Create Call with Monday and Call with Tuesday")
        self.assertEqual(turn.status, "awaiting_confirmation", turn.error_code)
        self.assertEqual(turn.tool_calls.count(), 2)
