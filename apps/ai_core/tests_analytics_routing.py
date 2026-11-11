import json
from unittest.mock import patch

from django.test import TestCase, override_settings

from apps.ai_core import tests_conversation_memory as fixtures
from apps.ai_core.ai_client import AIClientError, AIClientResult
from apps.ai_core.conversation_state import cancel_turn, start_turn
from apps.ai_core.models import AIRequestLog, AIToolCallLog, AgentProfile
from apps.ai_core.services import process_ai_job
from apps.tasks.models import Task


def output(value):
    return AIClientResult(json.dumps(value), "test", provider="test")


def route(**values):
    return {"intent": "answer", "question": "", "steps": [], "period": None, "read": None, **values}


@override_settings(AI_PROVIDER="mock", AI_ENABLED=True, AI_QUEUE_LIVE_REQUESTS=False)
class AnalyticsRoutingTests(TestCase):
    def setUp(self):
        fixtures.ConversationMemoryTests.setUp(self)
        self.profile = AgentProfile.objects.get(bot=self.agent)
        self.profile.rules_json = {"sources": ["tasks"], "analyst_enabled": True}
        self.profile.allowed_tools_json = {"tools": ["crm_read"]}
        self.profile.save()
        self.match = Task.objects.create(business=self.business, title="LIVE-QA-731: проверить отчёт")
        Task.objects.create(business=self.business, title="Другая задача")
        Task.objects.create(business=self.business, title="Архив LIVE-QA-731", is_archived=True)
        Task.objects.create(business=self.other_business, title="Чужая LIVE-QA-731")

    def prepare(self, responses, *, mode="analytics", key="initial", message="Сколько задач? Назови LIVE-QA-731.", context=None):
        turn, job = start_turn(conversation_id=self.thread.pk, user=self.owner, message=message,
                               idempotency_key=key, mode=mode, context=context)
        with patch("apps.ai_core.services.generate_text", side_effect=responses) as generate:
            process_ai_job(job.pk)
        turn.refresh_from_db()
        return turn, job, generate

    def answer(self):
        return output({"answer": "Всего доступно 2 задачи; по запросу найдена 1: LIVE-QA-731: проверить отчёт.",
                       "source_ids": ["CRM-summary", f"TASK-{self.match.pk}"], "no_data": False})

    def test_extra_context_keys_are_regenerated_not_accepted(self):
        invalid = route(read={"entity": "tasks", "query": "LIVE-QA-731"}, available_records={"tasks_count": 2})
        turn, job, generate = self.prepare([output(invalid), output(route(read={"entity": "tasks", "query": "LIVE-QA-731"})), self.answer()])
        self.assertEqual(turn.status, "completed", turn.error_code)
        self.assertEqual(generate.call_count, 3)
        self.assertEqual(AIRequestLog.objects.filter(prompt_type="agent_turn_plan").count(), 2)
        self.assertFalse(turn.tool_calls.exists())
        self.assertEqual(Task.objects.count(), 4)
        with patch("apps.ai_core.services.generate_text") as replay:
            process_ai_job(job.pk)
        replay.assert_not_called()

    def test_supported_model_receives_strict_analytics_schema(self):
        from apps.ai_core.conversation_router import ANALYTICS_ROUTE_SCHEMA
        self.agent.settings_json = {**self.agent.settings_json, "model": "gpt-4o-mini"}
        self.agent.save()
        turn, _, generate = self.prepare([output(route()), self.answer()])
        self.assertEqual(turn.status, "completed", turn.error_code)
        response_format = generate.call_args_list[0].args[0].response_format
        self.assertEqual(response_format["type"], "json_schema")
        self.assertTrue(response_format["json_schema"]["strict"])
        self.assertEqual(response_format["json_schema"]["schema"], ANALYTICS_ROUTE_SCHEMA)
        self.assertEqual(generate.call_args_list[1].args[0].response_format, {"type": "json_object"})

    def test_analytics_read_combination_retries_into_historical_report(self):
        from django.utils import timezone
        day = timezone.localdate().isoformat()
        period = {"start": day, "end": day}
        invalid = route(intent="analytics", period=period, read={"entity": "tasks", "query": ""})
        answer = output({"answer": "В периоде 3 задачи, включая архив.", "source_ids": ["CRM-summary"], "no_data": False})
        turn, _, generate = self.prepare([output(invalid), output(route(intent="analytics", period=period)), answer])
        self.assertEqual(turn.status, "completed", turn.error_code)
        self.assertEqual(generate.call_count, 3)
        report = AIRequestLog.objects.get(prompt_type="business_history_analyst").input_json["crm_context"]["summary"]
        self.assertEqual(report["operations"]["tasks"]["count"], 3)
        self.assertEqual(turn.context_json["period"], period)
        self.assertFalse(turn.tool_calls.exists())

    def test_repair_is_bounded_and_strict(self):
        invalid = output(route(available_records={"invented": "must not execute"}))
        turn, _, generate = self.prepare([invalid, invalid])
        self.assertEqual(turn.status, "failed")
        self.assertEqual(turn.error_code, "invalid_action_plan")
        self.assertEqual(generate.call_count, 2)
        self.assertFalse(AIToolCallLog.objects.exists())
        self.assertEqual(Task.objects.count(), 4)

    def test_provider_failure_is_not_retried(self):
        turn, _, generate = self.prepare([AIClientError(code="provider_unavailable")])
        self.assertEqual(turn.status, "failed")
        self.assertEqual(generate.call_count, 1)

    def test_work_invalid_route_is_not_retried(self):
        turn, _, generate = self.prepare([output(route(extra="invalid"))], mode="work")
        self.assertEqual(turn.status, "failed")
        self.assertEqual(generate.call_count, 1)

    def test_cancelled_analytics_does_not_spend_a_repair_call(self):
        turn, job = start_turn(conversation_id=self.thread.pk, user=self.owner, message="Сколько задач?",
                               idempotency_key="cancel", mode="analytics")
        def cancel(*args, **kwargs):
            cancel_turn(conversation_id=self.thread.pk, turn_id=turn.pk, user=self.owner)
            return output(route(extra="invalid"))
        with patch("apps.ai_core.services.generate_text", side_effect=cancel) as generate:
            process_ai_job(job.pk)
        turn.refresh_from_db()
        self.assertEqual(turn.status, "cancelled")
        self.assertEqual(generate.call_count, 1)

    def test_search_total_and_matches_have_distinct_scoped_counts(self):
        turn, _, _ = self.prepare([output(route(read={"entity": "tasks", "query": "LIVE-QA-731"})), self.answer()])
        self.assertEqual(turn.status, "completed", turn.error_code)
        context = AIRequestLog.objects.get(prompt_type="crm_assistant").input_json["crm_context"]
        search = context["summary"]["search"]
        self.assertEqual(search["total_count"], 2)
        self.assertEqual(search["count"], 1)
        self.assertEqual(search["shown"], 1)
        self.assertEqual(search["coverage"], "permitted_non_archived_records")
        self.assertEqual([row["id"] for row in context["tasks"]], [self.match.pk])
        self.assertNotIn("Чужая", json.dumps(context, ensure_ascii=False))

    def test_forbidden_read_cannot_supply_total_or_matches(self):
        turn, _, generate = self.prepare([output(route(read={"entity": "clients", "query": ""}))])
        self.assertEqual(turn.status, "failed")
        self.assertEqual(turn.error_code, "access_changed")
        self.assertEqual(generate.call_count, 1)
        self.assertFalse(AIRequestLog.objects.filter(prompt_type="crm_assistant").exists())

    def test_empty_matches_do_not_erase_the_total(self):
        answer = output({"answer": "Всего 2 задачи; совпадений нет.", "source_ids": ["CRM-summary"], "no_data": False})
        turn, _, _ = self.prepare([output(route(read={"entity": "tasks", "query": "MISSING-999"})), answer])
        self.assertEqual(turn.status, "completed", turn.error_code)
        context = AIRequestLog.objects.get(prompt_type="crm_assistant").input_json["crm_context"]
        self.assertEqual(context["summary"]["search"]["total_count"], 2)
        self.assertEqual(context["summary"]["search"]["count"], 0)
        self.assertEqual(context["tasks"], [])

    def test_totals_are_not_the_limited_result_page(self):
        Task.objects.bulk_create([Task(business=self.business, title=f"Task {index}") for index in range(28)])
        answer = output({"answer": "Всего 30 задач; показано 20.", "source_ids": ["CRM-summary"], "no_data": False})
        turn, _, _ = self.prepare([output(route(read={"entity": "tasks", "query": ""})), answer])
        self.assertEqual(turn.status, "completed", turn.error_code)
        search = AIRequestLog.objects.get(prompt_type="crm_assistant").input_json["crm_context"]["summary"]["search"]
        self.assertEqual((search["total_count"], search["count"], search["shown"], search["has_more"]), (30, 30, 20, True))

    def test_totals_follow_the_requesting_users_own_scope(self):
        from apps.accounts.models import User
        from apps.businesses.models import BusinessMember, BusinessRole, RolePermission
        from apps.ai_core.conversation_access import create_staff_conversation
        actor = User.objects.create_user(username="analytics-own", password="test")
        role = BusinessRole.objects.create(business=self.business, name="Own tasks analyst")
        RolePermission.objects.create(business_role=role, resource="tasks", action="view", scope="own", is_allowed=True)
        RolePermission.objects.create(business_role=role, resource="ai_analyst", action="view", scope="business", is_allowed=True)
        BusinessMember.objects.create(business=self.business, user=actor, role="manager", business_role=role)
        self.match.assignee = actor
        self.match.save()
        Task.objects.create(business=self.business, assignee=actor, title="Own second task")
        self.owner = actor
        self.thread = create_staff_conversation(business=self.business, agent_id=self.agent.pk, user=actor, mode="analytics")
        turn, _, _ = self.prepare([output(route(read={"entity": "tasks", "query": "LIVE-QA-731"})), self.answer()])
        self.assertEqual(turn.status, "completed", turn.error_code)
        search = AIRequestLog.objects.get(prompt_type="crm_assistant").input_json["crm_context"]["summary"]["search"]
        self.assertEqual((search["total_count"], search["count"]), (2, 1))

    def test_repair_cannot_create_actions_in_analytics(self):
        mutation = route(intent="actions", steps=[{"entity": "tasks", "operation": "create", "target_id": None,
                         "query": "", "request": "Create task", "after": None}])
        turn, _, generate = self.prepare([output(route(extra="invalid")), output(mutation)])
        self.assertEqual(turn.status, "completed", turn.error_code)
        self.assertIn("CRM", turn.response)
        self.assertEqual(generate.call_count, 2)
        self.assertFalse(AIToolCallLog.objects.exists())
        self.assertEqual(Task.objects.count(), 4)

    def test_no_enabled_sources_does_not_call_provider(self):
        self.profile.rules_json = {"sources": [], "analyst_enabled": True}
        self.profile.save()
        turn, _, generate = self.prepare([])
        self.assertEqual(turn.status, "completed", turn.error_code)
        self.assertEqual(turn.context_json["provider_state"], "no_data")
        generate.assert_not_called()

    def test_denied_sources_complete_without_provider_or_false_interruption(self):
        from apps.accounts.models import User
        from apps.businesses.models import BusinessMember, BusinessRole, RolePermission
        from apps.ai_core.conversation_access import create_staff_conversation
        actor = User.objects.create_user(username="analytics-no-tasks")
        role = BusinessRole.objects.create(business=self.business, name="No task sources")
        RolePermission.objects.create(business_role=role, resource="tasks", action="view", is_allowed=False)
        RolePermission.objects.create(business_role=role, resource="ai_analyst", action="view", scope="business", is_allowed=True)
        BusinessMember.objects.create(business=self.business, user=actor, role="manager", business_role=role)
        self.owner = actor
        self.thread = create_staff_conversation(business=self.business, agent_id=self.agent.pk, user=actor, mode="analytics")
        turn, _, generate = self.prepare([])
        self.assertEqual(turn.status, "completed", turn.error_code)
        self.assertEqual(turn.context_json["reason"], "sources_unavailable")
        self.assertIn("источников", turn.response)
        self.assertEqual(turn.sources_json, [])
        self.assertFalse(AIToolCallLog.objects.exists())
        generate.assert_not_called()

    def test_selected_period_cannot_fall_back_to_current_search(self):
        from django.utils import timezone
        day = timezone.localdate().isoformat()
        period = {"start": day, "end": day}
        answer = output({"answer": "3 задачи, включая архив.", "source_ids": ["CRM-summary"], "no_data": False})
        turn, _, _ = self.prepare([output({"route": route(read={"entity": "tasks", "query": ""})}), answer],
            context={"period": period}, message="Сколько задач за выбранный период?")
        self.assertEqual(turn.status, "completed", turn.error_code)
        self.assertEqual(turn.plan_json["intent"], "analytics")
        self.assertEqual(turn.context_json["period"], period)
        report = AIRequestLog.objects.get(prompt_type="business_history_analyst").input_json["crm_context"]["summary"]
        self.assertEqual(report["operations"]["tasks"]["count"], 3)

    def test_date_search_dsl_is_rejected_before_false_zero_answer(self):
        from django.utils import timezone
        day = timezone.localdate().isoformat()
        invalid = output({"route": route(read={"entity": "tasks", "query": f"created_at:{day}"})})
        valid = output({"route": route(intent="analytics", period={"start": day, "end": day})})
        answer = output({"answer": "3 задачи.", "source_ids": ["CRM-summary"], "no_data": False})
        turn, _, generate = self.prepare([invalid, valid, answer], message=f"Сколько задач создано {day}?")
        self.assertEqual(turn.status, "completed", turn.error_code)
        self.assertEqual(generate.call_count, 3)
        self.assertFalse(AIRequestLog.objects.filter(prompt_type="crm_assistant").exists())
