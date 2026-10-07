from unittest.mock import patch

from django.test import TestCase
from rest_framework.test import APIClient

from apps.bots import tests_runtime_configuration as fixtures
from apps.ai_core.models import BusinessKnowledgeItem
from apps.ai_core.context_service import get_business_knowledge_context
from apps.ai_core.knowledge import connect_shared_knowledge
from apps.bots.runtime_configuration import agent_runtime_fingerprint
from rest_framework.exceptions import ValidationError


class CustomerKnowledgeTests(TestCase):
    def setUp(self):
        fixtures.RuntimeConfigurationTests.setUp(self)

    def test_unpublished_owned_and_shared_materials_never_enter_customer_context(self):
        internal = BusinessKnowledgeItem.objects.create(business=self.business, bot=self.bot, title="Internal", content="INTERNAL_CANARY")
        shared = BusinessKnowledgeItem.objects.create(business=self.business, title="Shared", content="SHARED_PRIVATE_CANARY")
        shared.connected_agents.add(self.bot)
        context = get_business_knowledge_context(self.business, agent=self.bot)
        self.assertEqual({item["id"] for item in context}, {self.knowledge.pk})
        self.assertNotIn("INTERNAL_CANARY", str(context))
        self.assertNotIn("SHARED_PRIVATE_CANARY", str(context))

    def test_shared_connection_requires_explicit_publication_and_is_reversible(self):
        shared = BusinessKnowledgeItem.objects.create(business=self.business, title="Public hours", content="Open 9 to 5")
        with self.assertRaises(ValidationError):
            connect_shared_knowledge(actor=self.business.owner, item=shared, agent_id=self.bot.pk, connected=True)
        self.assertFalse(shared.connected_agents.exists())
        connect_shared_knowledge(actor=self.business.owner, item=shared, agent_id=self.bot.pk, connected=True, allow_customer_use=True)
        self.assertIn(shared.pk, {item["id"] for item in get_business_knowledge_context(self.business, agent=self.bot)})
        before = agent_runtime_fingerprint(self.conversation)
        shared.customer_visible = False
        shared.save()
        self.assertNotEqual(before, agent_runtime_fingerprint(self.conversation))
        self.assertNotIn(shared.pk, {item["id"] for item in get_business_knowledge_context(self.business, agent=self.bot)})

    def test_customer_publication_rejects_secret_without_echoing_it(self):
        api = APIClient()
        api.force_authenticate(self.business.owner)
        response = api.post("/api/ai/knowledge-items/", {"business": self.business.pk, "bot": self.bot.pk,
            "title": "Invalid", "content": "api_key=synthetic-secret-sentinel", "customer_visible": True}, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertNotIn("synthetic-secret-sentinel", str(response.data))
        self.assertFalse(BusinessKnowledgeItem.objects.filter(title="Invalid").exists())

    def test_private_crm_material_stays_available_to_its_own_agent(self):
        from apps.bots.lifecycle import create_bot
        crm = create_bot(validated_data={"business": self.business, "name": "Internal", "scenario": "crm"})
        private = BusinessKnowledgeItem.objects.create(business=self.business, bot=crm, title="Internal", content="INTERNAL_CRM_CANARY")
        self.assertIn(private.pk, {item["id"] for item in get_business_knowledge_context(self.business, agent=crm)})
        self.assertNotIn(private.pk, {item["id"] for item in get_business_knowledge_context(self.business, agent=self.bot)})
