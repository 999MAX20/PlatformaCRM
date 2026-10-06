import json
from unittest.mock import patch

from django.test import TestCase, override_settings

from apps.ai_core import tests_conversation_execution as fixtures
from apps.ai_core.ai_client import AIClientResult
from apps.ai_core.models import AgentConversation, AgentProfile, AgentTurn
from apps.tasks.models import Task


@override_settings(AI_PROVIDER="mock", AI_ENABLED=True, AI_QUEUE_LIVE_REQUESTS=False)
class ConversationAPITests(TestCase):
    setUp = fixtures.ConversationExecutionTests.setUp

    def test_analytics_readiness_uses_analyst_permission_and_configuration(self):
        from apps.businesses.models import BusinessMember, BusinessRole, RolePermission
        role = BusinessRole.objects.create(business=self.business, name="Analyst only")
        RolePermission.objects.create(business_role=role, resource="ai_analyst", action="view", scope="business", is_allowed=True)
        RolePermission.objects.create(business_role=role, resource="ai_assistant", action="view", scope="none", is_allowed=False)
        BusinessMember.objects.create(business=self.business, user=self.other_owner, role="manager", business_role=role)
        self.api.force_authenticate(self.other_owner)
        params = {"business": self.business.pk, "agent": self.agent.pk}
        self.assertEqual(self.api.get("/api/ai/assistant/status/", params).status_code, 403)
        result = self.api.get("/api/ai/assistant/status/", {**params, "mode": "analytics"})
        self.assertEqual(result.status_code, 200, result.data)
        self.assertTrue(result.data["ready"])
        profile = AgentProfile.objects.get(bot=self.agent)
        profile.rules_json["analyst_enabled"] = False
        profile.save()
        self.assertFalse(self.api.get("/api/ai/assistant/status/", {**params, "mode": "analytics"}).data["ready"])

    def test_analytics_does_not_prepare_mutations_even_for_owner(self):
        self.api.force_authenticate(self.owner)
        with patch("apps.ai_core.services.generate_text", return_value=fixtures.action_route(fixtures.create_step())) as provider:
            response = self.api.post(self.url("turns/"), {"message": "Create Call task", "mode": "analytics", "idempotency_key": "readonly"}, format="json")
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data["status"], "completed")
        self.assertIn("CRM", response.data["response"])
        self.assertEqual(response.data["actions"], [])
        self.assertFalse(Task.objects.exists())
        provider.assert_called_once()

    def test_latest_public_turn_does_not_reveal_title_from_revoked_record(self):
        from apps.ai_core.conversation_access import memory_access_fingerprint
        fingerprint = memory_access_fingerprint(business=self.business, agent=self.agent, user=self.owner)
        self.thread.title = "Private record from first turn"
        self.thread.save()
        AgentTurn.objects.create(conversation=self.thread, sequence=1, idempotency_key="old",
            request_hash="old", message=self.thread.title, status="completed", access_fingerprint=fingerprint,
            references_json=[{"entity": "tasks", "id": 999999}])
        AgentTurn.objects.create(conversation=self.thread, sequence=2, idempotency_key="new",
            request_hash="new", message="Public question", status="completed", access_fingerprint=fingerprint)
        self.api.force_authenticate(self.owner)
        response = self.api.get(self.url())
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["conversation"]["title"], "")
        self.assertTrue(response.data["turns"][0]["redacted"])
        self.assertFalse(response.data["turns"][1]["redacted"])

    def test_older_conversations_remain_reachable_without_other_owners(self):
        self.api.force_authenticate(self.owner)
        AgentConversation.objects.bulk_create([
            AgentConversation(business=self.business, agent=self.agent, owner=self.owner,
                              kind=AgentConversation.Kinds.STAFF, title=f"Thread {index}")
            for index in range(51)])
        hidden = AgentConversation.objects.create(business=self.business, agent=self.agent,
            owner=self.other_owner, kind=AgentConversation.Kinds.STAFF, title="Private")
        params = {"business": self.business.pk, "agent": self.agent.pk}
        first = self.api.get("/api/ai/conversations/", params)
        self.assertEqual(first.status_code, 200)
        self.assertEqual(len(first.data["results"]), 50)
        second = self.api.get("/api/ai/conversations/", {**params, "offset": first.data["next_offset"]})
        self.assertIsNone(second.data["next_offset"])
        ids = [item["id"] for item in first.data["results"] + second.data["results"]]
        self.assertEqual(len(set(ids)), 52)
        self.assertNotIn(str(hidden.pk), ids)
        self.assertEqual(self.api.get("/api/ai/conversations/", {**params, "offset": -1}).status_code, 400)

    def url(self, suffix=""):
        return f"/api/ai/conversations/{self.thread.pk}/{suffix}"

    def send(self, responses, message="Create Call task", key="api-request"):
        self.api.force_authenticate(self.owner)
        with patch("apps.ai_core.services.generate_text", side_effect=responses):
            response = self.api.post(self.url("turns/"), {"message": message, "idempotency_key": key}, format="json")
        self.assertEqual(response.status_code, 200, response.data)
        return response

    def test_reachable_thread_restores_messages_and_confirmation_survives_reload(self):
        response = self.send([fixtures.action_route(fixtures.create_step()), fixtures.create_plan(title="Call")])
        self.assertEqual(response.data["status"], "awaiting_confirmation")
        restored = self.api.get(self.url())
        self.assertEqual(restored.status_code, 200, restored.data)
        turn = restored.data["turns"][0]
        self.assertEqual(turn["message"], "Create Call task")
        self.assertFalse(Task.objects.exists())
        action = turn["actions"][0]
        payload = {"expected_revision": turn["sequence"], "actions": [{"id": action["id"], "fingerprint": action["fingerprint"]}]}
        confirmed = self.api.post(self.url(f"turns/{turn['id']}/confirm/"), payload, format="json")
        self.assertEqual(confirmed.status_code, 200, confirmed.data)
        self.assertEqual(confirmed.data["status"], "completed")
        replay = self.api.post(self.url(f"turns/{turn['id']}/confirm/"), payload, format="json")
        self.assertEqual(replay.status_code, 200, replay.data)
        self.assertEqual(Task.objects.count(), 1)

    def test_foreign_thread_is_unavailable_and_private_logs_do_not_leak(self):
        route = fixtures.output({"intent": "answer", "steps": [], "question": "", "read": None, "period": None})
        answer = fixtures.output({"answer": "PRIVATE_REPLY", "source_ids": ["CRM-summary"]})
        self.send([route, answer], message="PRIVATE_QUESTION")
        logs = self.api.get("/api/ai/request-logs/", {"business": self.business.pk})
        self.assertNotIn("PRIVATE_REPLY", json.dumps(logs.data))
        self.assertNotIn("PRIVATE_QUESTION", json.dumps(logs.data))
        self.api.force_authenticate(self.other_owner)
        self.assertEqual(self.api.get(self.url()).status_code, 404)
        denied = self.api.post(self.url("turns/"), {"message": "Read private", "idempotency_key": "foreign"}, format="json")
        self.assertEqual(denied.status_code, 404)

    def test_source_revocation_redacts_history_and_exact_proposal(self):
        self.send([fixtures.action_route(fixtures.create_step()), fixtures.create_plan(title="Private task")])
        profile = AgentProfile.objects.get(bot=self.agent)
        profile.rules_json["sources"] = []
        profile.save()
        history = self.api.get(self.url())
        self.assertEqual(history.status_code, 200, history.data)
        turn = history.data["turns"][0]
        self.assertTrue(turn["redacted"])
        self.assertEqual(turn["message"], "")
        self.assertEqual(turn["actions"], [])

    def test_changed_confirmation_fingerprint_and_duplicate_key_cannot_write(self):
        response = self.send([fixtures.action_route(fixtures.create_step()), fixtures.create_plan(title="Call")])
        action = response.data["actions"][0]
        result = self.api.post(self.url(f"turns/{response.data['id']}/confirm/"), {
            "expected_revision": response.data["sequence"], "actions": [{"id": action["id"], "fingerprint": "0" * 64}]}, format="json")
        self.assertEqual(result.status_code, 409, result.data)
        with patch("apps.ai_core.services.generate_text") as provider:
            repeat = self.api.post(self.url("turns/"), {"message": "Create Call task", "idempotency_key": "api-request"}, format="json")
        self.assertEqual(repeat.status_code, 200, repeat.data)
        provider.assert_not_called()
        self.assertFalse(Task.objects.exists())
