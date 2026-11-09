import json
from unittest.mock import patch

from django.test import TestCase, override_settings

from apps.accounts.models import UserPreference
from apps.ai_core import tests as foundation
from apps.ai_core.ai_client import AIClientError, AIClientResult
from apps.ai_core.conversation_access import create_voice_conversation
from apps.ai_core.conversation_copy import conversation_text
from apps.ai_core.conversation_router import parse_route
from apps.ai_core.conversation_state import start_turn
from apps.ai_core.services import process_ai_job
from apps.ai_core.tests_conversation_execution import action_route, create_step, create_plan
from apps.tasks.models import Task


def greeting_route(**changes):
    return {"intent": "greeting", "question": "", "steps": [], "period": None, "read": None, **changes}


@override_settings(AI_PROVIDER="mock", AI_ENABLED=True, VOICE_INPUT_ENABLED=True, AI_QUEUE_LIVE_REQUESTS=False)
class VoiceLanguageTests(TestCase):
    def setUp(self):
        foundation.AICoreFoundationTests.setUp(self)
        self.thread = create_voice_conversation(business=self.business, user=self.owner)

    def test_answer_to_title_question_reaches_planner_and_creates_once_after_approval(self):
        from apps.ai_core.tests_conversation_execution import output, ConversationExecutionTests
        initial, job = start_turn(conversation_id=self.thread.pk, user=self.owner,
                                 message="Создай задачу", idempotency_key="ask-title")
        with patch("apps.ai_core.services.generate_text", return_value=output({
            "intent": "clarify", "question": "Что нужно сделать?", "steps": [], "period": None, "read": None,
        })):
            process_ai_job(job.pk)
        initial.refresh_from_db()
        self.assertEqual(initial.status, "clarifying")
        self.assertFalse(initial.tool_calls.exists())
        title = "Позвонить поставщику"
        turn, job = start_turn(conversation_id=self.thread.pk, user=self.owner,
                              message=title, idempotency_key="answer-title")
        with patch("apps.ai_core.services.generate_text", side_effect=[
            action_route(create_step(request=f"Создай задачу {title}")), create_plan(title=title),
        ]) as generate:
            process_ai_job(job.pk)
        for call in generate.call_args_list:
            prompt = str(call.args[0])
            self.assertIn("Создай задачу", prompt)
            self.assertIn("Что нужно сделать?", prompt)
            self.assertIn(title, prompt)
        turn.refresh_from_db()
        self.assertEqual(turn.status, "awaiting_confirmation")
        self.assertFalse(Task.objects.exists())
        log = turn.tool_calls.get()
        completed, _ = ConversationExecutionTests.confirm(self, turn, [log])
        self.assertEqual(completed.status, "completed")
        ConversationExecutionTests.confirm(self, turn, [log])
        self.assertEqual(list(Task.objects.values_list("title", flat=True)), [title])

    def test_shortened_route_keeps_original_employee_details_for_field_planning(self):
        message = "Поставь задачу проверить остатки. В описании запиши: сверить артикулы со счётом."
        turn, job = start_turn(conversation_id=self.thread.pk, user=self.owner,
                              message=message, idempotency_key="original-details")
        with patch("apps.ai_core.services.generate_text", side_effect=[
            action_route(create_step(request="проверить остатки")),
            create_plan(title="проверить остатки", description="сверить артикулы со счётом"),
        ]) as generate:
            process_ai_job(job.pk)
        self.assertIn(message, str(generate.call_args_list[1].args[0]))
        self.assertEqual(str(generate.call_args_list[1].args[0]).split("User input:\n")[-1],
                         "Saved style: expert. \n" + message)
        turn.refresh_from_db()
        self.assertEqual(turn.status, "awaiting_confirmation")
        self.assertEqual(turn.tool_calls.get().input_json["values"]["description"], "сверить артикулы со счётом")
        self.assertFalse(Task.objects.exists())

    def test_greeting_uses_employee_locale_without_factual_answer_or_actions(self):
        for language in ("ru", "kk", "en"):
            UserPreference.objects.update_or_create(user=self.owner, defaults={"language": language})
            turn, job = start_turn(conversation_id=self.thread.pk, user=self.owner,
                                  message="Salam bro, how are you?", idempotency_key=language)
            reply = AIClientResult(json.dumps(greeting_route()), "test", provider="test")
            natural = {"ru": "Салам! Слушаю тебя.", "kk": "Сәлем! Сені тыңдап тұрмын.", "en": "Hey! I'm listening."}[language]
            with patch("apps.ai_core.services.generate_text", side_effect=[reply,
                    AIClientResult(json.dumps({"reply": natural}), "openai/gpt-4o-mini", provider="test")]) as generate:
                process_ai_job(job.pk)
            turn.refresh_from_db()
            self.assertEqual(turn.status, "completed")
            self.assertEqual(turn.response, natural)
            self.assertEqual(turn.sources_json, [])
            self.assertFalse(turn.tool_calls.exists())
            self.assertEqual(generate.call_count, 2)
            self.assertEqual(generate.call_args.kwargs["model"], "openai/gpt-4o-mini")
            self.assertFalse(generate.call_args.kwargs["allow_mock"])
            self.assertNotEqual(turn.context_json.get("provider_state"), "no_data")
        self.assertFalse(Task.objects.exists())

    def test_weather_gets_model_reply_without_tools_or_workspace_data(self):
        turn, job = start_turn(conversation_id=self.thread.pk, user=self.owner,
                              message="Какая погода в Алматы?", idempotency_key="weather")
        reply = "У меня нет доступа к текущей погоде в Алматы."
        with patch("apps.ai_core.services.generate_text", side_effect=[
                AIClientResult(json.dumps(greeting_route(intent="chat")), "test", provider="test"),
                AIClientResult(json.dumps({"reply": reply}), "test", provider="test")]) as generate:
            process_ai_job(job.pk)
        turn.refresh_from_db()
        self.assertEqual(turn.status, "completed")
        self.assertEqual(turn.response, reply)
        self.assertEqual(turn.sources_json, [])
        self.assertFalse(turn.tool_calls.exists())
        self.assertIn("no web search", generate.call_args.args[0].messages[0]["content"])
        self.assertFalse(Task.objects.exists())

    def test_conversational_model_cannot_return_action_payload(self):
        turn, job = start_turn(conversation_id=self.thread.pk, user=self.owner,
                              message="Салам", idempotency_key="unsafe-chat")
        with patch("apps.ai_core.services.generate_text", side_effect=[
                AIClientResult(json.dumps(greeting_route()), "test", provider="test"),
                AIClientResult(json.dumps({"reply": "OK", "tool": "crm_create"}), "test", provider="test")]):
            process_ai_job(job.pk)
        turn.refresh_from_db()
        self.assertEqual(turn.status, "failed")
        self.assertFalse(turn.tool_calls.exists())
        self.assertFalse(Task.objects.exists())

    def test_greeting_schema_rejects_freeform_facts_and_embedded_actions(self):
        context = {"available_records": {}, "fresh_references": []}
        self.assertEqual(parse_route(json.dumps(greeting_route()), context)["intent"], "greeting")
        for values in ({"question": "Revenue doubled"}, {"steps": [create_step()]},
                       {"read": {"entity": "clients", "query": ""}},
                       {"period": {"start": "2026-01-01", "end": "2026-01-02"}},
                       {"answer": "Executed the task"}):
            with self.subTest(values=values), self.assertRaises(AIClientError):
                parse_route(json.dumps(greeting_route(**values)), context)

    def test_greeting_prefixed_action_still_requires_confirmation(self):
        turn, job = start_turn(conversation_id=self.thread.pk, user=self.owner,
                              message="Привет, создай задачу Позвонить поставщику", idempotency_key="action")
        with patch("apps.ai_core.services.generate_text", side_effect=[action_route(create_step()), create_plan(title="Позвонить поставщику")]):
            process_ai_job(job.pk)
        turn.refresh_from_db()
        self.assertEqual(turn.status, "awaiting_confirmation")
        self.assertEqual(turn.tool_calls.count(), 1)
        self.assertFalse(Task.objects.exists())

    def test_business_question_keeps_grounded_no_data_boundary(self):
        turn, job = start_turn(conversation_id=self.thread.pk, user=self.owner,
                              message="Привет, почему снизились продажи?", idempotency_key="facts")
        route = AIClientResult(json.dumps({"intent": "answer", "question": "", "steps": [], "period": None, "read": None}), "test", provider="test")
        answer = AIClientResult(json.dumps({"answer": "Недостаточно данных для такого вывода.", "source_ids": [], "no_data": True}), "test", provider="test")
        with patch("apps.ai_core.services.generate_text", side_effect=[route, answer]):
            process_ai_job(job.pk)
        turn.refresh_from_db()
        self.assertEqual(turn.status, "completed")
        self.assertEqual(turn.context_json["provider_state"], "no_data")
        self.assertEqual(turn.sources_json, [])
        self.assertFalse(turn.tool_calls.exists())
