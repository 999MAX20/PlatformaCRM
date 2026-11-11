import json
from unittest.mock import patch

from django.test import TestCase, override_settings
from rest_framework.exceptions import PermissionDenied

from apps.ai_core import tests_conversation_execution as fixtures
from apps.ai_core.ai_client import AIClientError
from apps.ai_core.conversation_router import parse_route, resolve_step_target
from apps.tasks.models import Task


@override_settings(AI_PROVIDER="mock", AI_ENABLED=True)
class ConversationTargetTests(TestCase):
    def setUp(self):
        fixtures.ConversationExecutionTests.setUp(self)
        self.first = Task.objects.create(business=self.business, title="Check invoice")

    def resolve(self, message, *, query="", target=None, **kwargs):
        return resolve_step_target(thread=self.thread, user=self.owner, language="en", message=message,
            step={"entity": "tasks", "operation": "update", "target_id": target, "query": query}, **kwargs)

    def test_duplicate_name_never_accepts_recent_model_id(self):
        second = Task.objects.create(business=self.business, title=self.first.title)
        for query in ("", self.first.title):
            target, question, refs = self.resolve("Update Check invoice", query=query, target=self.first.pk)
            self.assertIsNone(target)
            self.assertTrue(question)
            self.assertEqual({ref["id"] for ref in refs}, {self.first.pk, second.pk})

    def test_absent_name_cannot_substitute_existing_id_or_model_query(self):
        for query in ("", "Missing invoice", self.first.title):
            target, question, _ = self.resolve("Update Missing invoice", query=query, target=self.first.pk)
            self.assertIsNone(target)
            self.assertTrue(question)

    def test_unique_literal_name_resolves_beyond_recent_sample(self):
        for index in range(10):
            Task.objects.create(business=self.business, title=f"Recent {index}")
        target, question, _ = self.resolve("Update Check invoice", query=self.first.title)
        self.assertEqual(target, self.first.pk)
        self.assertFalse(question)

    def test_partial_quote_cannot_substitute_different_title(self):
        target, question, _ = self.resolve('Update "Missing Check invoice"', query=self.first.title, target=self.first.pk)
        self.assertIsNone(target)
        self.assertTrue(question)

    def test_ungrounded_query_does_not_fall_back_to_an_old_pronoun(self):
        memory = {"messages": [{"references": [{"entity": "tasks", "id": self.first.pk}]}]}
        target, question, _ = self.resolve('У задачи «Missing invoice» измени её описание',
            query=self.first.title, target=self.first.pk, memory=memory)
        self.assertIsNone(target)
        self.assertTrue(question)

    def test_explicit_id_disambiguates_duplicate(self):
        Task.objects.create(business=self.business, title=self.first.title)
        target, question, _ = self.resolve(f"Update task #{self.first.pk}", target=self.first.pk)
        self.assertEqual(target, self.first.pk)
        self.assertFalse(question)

    def test_explicit_selection_overrides_model_choice_of_the_other_duplicate(self):
        second = Task.objects.create(business=self.business, title=self.first.title)
        for model_id in (None, second.pk):
            target, question, _ = self.resolve(f"Используй задачу #{self.first.pk}. Замени её описание.",
                query=self.first.title, target=model_id)
            self.assertEqual(target, self.first.pk)
            self.assertFalse(question)

    def test_linked_client_id_does_not_select_task_with_same_id(self):
        target, question, _ = self.resolve(f"Клиенту #{self.first.pk} поменяй связь с отсутствующей задачей", target=self.first.pk)
        self.assertIsNone(target)
        self.assertTrue(question)

    def test_multi_step_message_does_not_apply_one_id_to_another_named_step(self):
        second = Task.objects.create(business=self.business, title="Other task")
        target, question, _ = self.resolve(f"Update task #{self.first.pk} and Other task",
            query=second.title, target=second.pk, allow_explicit_override=False)
        self.assertEqual(target, second.pk)
        self.assertFalse(question)

    def test_pronoun_requires_single_latest_reference(self):
        refs = [{"entity": "tasks", "id": self.first.pk}]
        target, _, _ = self.resolve("Update it", target=self.first.pk, memory={"messages": [{"references": refs}]})
        self.assertEqual(target, self.first.pk)
        refs.append({"entity": "tasks", "id": self.first.pk + 1})
        target, question, _ = self.resolve("Update it", target=self.first.pk, memory={"messages": [{"references": refs}]})
        self.assertIsNone(target)
        self.assertTrue(question)

    def test_foreign_named_record_is_not_offered(self):
        Task.objects.create(business=self.other_business, title=self.first.title)
        target, _, refs = self.resolve("Update Check invoice", query=self.first.title)
        self.assertEqual(target, self.first.pk)
        self.assertEqual(refs, [{"entity": "tasks", "id": self.first.pk}])

    def test_explicit_foreign_id_is_denied(self):
        foreign = Task.objects.create(business=self.other_business, title="Hidden")
        with self.assertRaises(PermissionDenied):
            self.resolve(f"Update #{foreign.pk}", target=foreign.pk)

    def test_completed_parent_result_is_revalidated(self):
        target, _, _ = self.resolve("Create then update", target=self.first.pk, parent_target=self.first.pk)
        self.assertEqual(target, self.first.pk)

    def test_explicit_id_beyond_recent_sample_is_allowed_but_invented_id_is_not(self):
        route = json.dumps({"intent": "actions", "question": "", "steps": [{"entity": "tasks",
            "operation": "update", "target_id": self.first.pk, "query": "", "request": "Change description", "after": None}]})
        context = {"available_records": {}, "fresh_references": []}
        self.assertEqual(parse_route(route, context, f"Update #{self.first.pk}")["steps"][0]["target_id"], self.first.pk)
        with self.assertRaises(AIClientError):
            parse_route(route, context, "Update missing task")

    def test_bare_task_title_reply_preserves_user_code_before_review(self):
        from apps.ai_core.agent_runtime import bind_thread
        from apps.ai_core.crm_planner import plan_command
        memory = {"pending": {"question": "Title?", "plan": {"steps": [fixtures.create_step()]}}}
        for prefix in ("OPS-17", "ҚР", "Q4 2026"):
            with self.subTest(prefix=prefix), bind_thread(self.thread), patch("apps.ai_core.services.generate_text",
                    return_value=fixtures.create_plan(title="Проверить накладную")):
                source = prefix + " Проверить накладную"
                result = plan_command(business=self.business, user=self.owner, entity="tasks", message=source,
                    source_message=source, conversation_memory=memory, persist=False, expected_tool="crm_create")
                self.assertEqual(result["prepared_command"]["payload"]["values"]["title"], source)
                self.assertEqual(Task.objects.count(), 1)

    def test_title_prefix_guard_does_not_copy_commands_or_other_pending_work(self):
        from apps.ai_core.crm_planner import preserve_task_title_prefix
        memory = {"pending": {"question": "Title?", "plan": {"steps": [fixtures.create_step()]}}}
        for message, context in (("CREATE TASK Call", memory), ("OPS-17 Call", {}), ("Deadline tomorrow Call", memory)):
            with self.subTest(message=message):
                values = {"title": "Call"}
                preserve_task_title_prefix(values, message, context)
                self.assertEqual(values["title"], "Call")
