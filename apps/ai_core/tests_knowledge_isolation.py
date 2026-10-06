from unittest.mock import patch

from django.test import TestCase, override_settings
from rest_framework.exceptions import PermissionDenied

from apps.ai_core import tests as fixtures
from apps.ai_core.models import AgentProfile, BusinessKnowledgeItem
from apps.ai_core.context_service import get_business_knowledge_context
from apps.ai_core.knowledge import connect_shared_knowledge
from apps.ai_core.services import run_ai_request
from apps.ai_core.agent_runtime import bind_agent
from apps.ai_core.workflows import workflow_settings
from apps.bots.ai import get_agent_profile
from apps.bots.deletion import delete_agent
from apps.bots.lifecycle import create_bot
from apps.bots.models import Bot, BotConversation
from apps.core.models import AuditLog


@override_settings(AI_PROVIDER="mock", AI_ENABLED=True)
class AgentKnowledgeIsolationTests(TestCase):
    def setUp(self):
        fixtures.AICoreFoundationTests.setUp(self)
        self.api.force_authenticate(self.owner)
        self.agent = create_bot(validated_data={"business": self.business, "name": "First"})
        self.other = create_bot(validated_data={"business": self.business, "name": "Second"})
        self.shared = BusinessKnowledgeItem.objects.create(business=self.business, title="Shared", content="Legacy material")
        self.own = BusinessKnowledgeItem.objects.create(business=self.business, bot=self.agent, title="Private", content="Only first agent")
        self.foreign = BusinessKnowledgeItem.objects.create(business=self.other_business, title="Foreign", content="Other tenant")

    def knowledge_ids(self, agent):
        return {item["id"] for item in get_business_knowledge_context(self.business, agent=agent)}

    def connect(self, item=None, agent=None, connected=True):
        return self.api.post(f"/api/ai/knowledge-items/{(item or self.shared).pk}/connection/",
            {"agent": (agent or self.agent).pk, "connected": connected}, format="json")

    def test_empty_default_and_explicit_shared_connection_are_agent_scoped(self):
        self.assertEqual(self.knowledge_ids(self.agent), {self.own.pk})
        self.assertEqual(self.knowledge_ids(self.other), set())
        self.assertEqual(get_business_knowledge_context(self.business), [])
        self.assertEqual(self.connect().status_code, 200)
        self.assertEqual(self.knowledge_ids(self.agent), {self.own.pk, self.shared.pk})
        self.assertEqual(self.knowledge_ids(self.other), set())
        response = self.api.get("/api/ai/knowledge-items/", {"agent": self.agent.pk})
        self.assertEqual({item["id"] for item in response.data["results"]}, {self.own.pk, self.shared.pk})
        self.assertEqual(self.connect(connected=False).status_code, 200)
        self.assertEqual(self.knowledge_ids(self.agent), {self.own.pk})

    def test_private_ownership_cannot_be_moved_or_connected(self):
        self.assertEqual(self.connect(item=self.own, agent=self.other).status_code, 400)
        for bot in (None, self.other.pk):
            response = self.api.patch(f"/api/ai/knowledge-items/{self.own.pk}/", {"bot": bot}, format="json")
            self.assertEqual(response.status_code, 400)
        response = self.api.post("/api/ai/knowledge-items/", {"business": self.business.pk, "bot": self.other.pk,
            "title": "New", "content": "Independent"}, format="json")
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(self.knowledge_ids(self.other), {response.data["id"]})

    def test_foreign_business_and_disallowed_role_cannot_link_or_read(self):
        foreign_agent = create_bot(validated_data={"business": self.other_business, "name": "Foreign"})
        self.assertEqual(self.connect(item=self.foreign).status_code, 404)
        self.assertEqual(self.connect(agent=foreign_agent).status_code, 404)
        self.assertEqual(self.api.get("/api/ai/knowledge-items/", {"agent": foreign_agent.pk}).status_code, 404)
        response = self.api.post("/api/ai/knowledge-items/", {"business": self.business.pk, "bot": foreign_agent.pk,
            "title": "Invalid", "content": "Invalid"}, format="json")
        self.assertEqual(response.status_code, 400)
        from apps.accounts.models import User
        from apps.businesses.models import BusinessMember
        viewer = User.objects.create_user(username="knowledge-viewer", email="knowledge-viewer@example.test")
        BusinessMember.objects.create(business=self.business, user=viewer, role="manager")
        self.api.force_authenticate(viewer)
        self.assertIn(self.connect().status_code, {403, 404})
        self.assertFalse(self.shared.connected_agents.exists())

    def test_deletion_retains_history_without_transferring_to_replacement(self):
        self.assertEqual(self.connect().status_code, 200)
        profile = AgentProfile.objects.create(business=self.business, bot=self.agent, name="Old", system_prompt="Old rules")
        delete_agent(bot=self.agent, actor=self.owner)
        replacement = create_bot(validated_data={"business": self.business, "name": "Replacement"})
        self.assertFalse(replacement.channels.exists())
        self.assertFalse(replacement.agent_profiles.exists())
        self.assertEqual(replacement.settings_json, {"scenario": "inbox"})
        self.assertEqual(self.knowledge_ids(replacement), set())
        profile.refresh_from_db()
        self.assertFalse(profile.is_active)
        self.assertTrue(BusinessKnowledgeItem.objects.filter(pk=self.own.pk, bot_id=self.agent.pk).exists())
        self.assertEqual(self.api.get(f"/api/ai/knowledge-items/{self.own.pk}/").status_code, 404)
        self.assertEqual(self.connect().status_code, 404)
        self.assertIsNone(get_agent_profile(BotConversation(business=self.business, bot=replacement)))

    def test_legacy_unbound_profile_is_not_an_agent_default(self):
        from apps.conversations.auto_pipeline import _resolve_allowed_tools
        AgentProfile.objects.create(business=self.business, name="Unbound", system_prompt="Legacy instructions")
        self.assertIsNone(get_agent_profile(BotConversation(business=self.business, bot=self.agent)))
        self.assertEqual(_resolve_allowed_tools(BotConversation(business=self.business, bot=self.agent)), set())
        AgentProfile.objects.create(business=self.business, name="Old internal", system_prompt="Old internal rules",
                                    rules_json={"scenario": "employee"})
        self.assertNotIn("instructions", workflow_settings(self.business, "employee"))
        crm = create_bot(validated_data={"business": self.business, "name": "CRM", "scenario": "crm"})
        with bind_agent(crm.pk):
            self.assertEqual(workflow_settings(self.business, "employee")["instructions"], "")

    def test_actual_ai_context_excludes_other_agent_and_unconnected_shared_material(self):
        _, log = run_ai_request(business=self.business, user=self.owner, source="bot", prompt_type="bot_suggest_reply",
            user_input="Hello", input_json={"bot_id": self.other.pk})
        self.assertEqual(log.input_json["context"], [])
        self.assertEqual(self.connect().status_code, 200)
        _, log = run_ai_request(business=self.business, user=self.owner, source="bot", prompt_type="bot_suggest_reply",
            user_input="Hello", input_json={"bot_id": self.agent.pk})
        self.assertEqual({item["id"] for item in log.input_json["context"]}, {self.own.pk, self.shared.pk})

    def test_connection_is_idempotent_and_audit_failure_rolls_it_back(self):
        with patch("apps.ai_core.knowledge.write_actor_audit_log", side_effect=RuntimeError("Audit unavailable")):
            with self.assertRaises(RuntimeError):
                connect_shared_knowledge(actor=self.owner, item=self.shared, agent_id=self.agent.pk, connected=True)
        self.assertFalse(self.shared.connected_agents.exists())
        self.assertEqual(self.connect().status_code, 200)
        count = AuditLog.objects.count()
        self.assertEqual(self.connect().status_code, 200)
        self.assertEqual(AuditLog.objects.count(), count)

    def test_disconnect_during_provider_call_rejects_stale_context(self):
        from apps.ai_core.ai_client import AIClientResult
        self.assertEqual(self.connect().status_code, 200)
        def answer(*args, **kwargs):
            connect_shared_knowledge(actor=self.owner, item=self.shared, agent_id=self.agent.pk, connected=False)
            return AIClientResult(output_text="Stale answer", model="mock", tokens_used=0, is_mock=True, provider="mock")
        with patch("apps.ai_core.services.generate_text", side_effect=answer):
            with self.assertRaises(PermissionDenied):
                run_ai_request(business=self.business, user=self.owner, source="bot", prompt_type="bot_suggest_reply",
                    user_input="Hello", input_json={"bot_id": self.agent.pk})
