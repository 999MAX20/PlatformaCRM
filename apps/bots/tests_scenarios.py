from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework.exceptions import PermissionDenied
from apps.bots.ai import get_agent_profile
from apps.bots.serializers import BotConversationSerializer

from apps.ai_core.models import AgentProfile
from apps.bots.models import Bot, BotConversation
from apps.businesses.models import Business, BusinessMember


class AgentScenarioTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="scenario", email="scenario@example.com", password="Test12345!")
        self.business = Business.objects.create(owner=self.user, name="Scenarios", slug="scenarios")
        BusinessMember.objects.create(business=self.business, user=self.user, role="owner")
        self.api = APIClient()
        self.api.force_authenticate(self.user)

    def create(self, scenario="crm", **extra):
        return self.api.post("/api/bots/", {"business": self.business.pk, "name": "Assistant", "scenario": scenario, **extra}, format="json")

    def test_create_crm_has_own_profile_and_no_channel_requirement(self):
        response = self.create()
        self.assertEqual(response.status_code, 201, response.data)
        bot = Bot.objects.get(pk=response.data["id"])
        self.assertEqual(bot.scenario, "crm")
        self.assertTrue(response.data["readiness"]["is_ready"])
        profile = AgentProfile.objects.get(bot=bot)
        self.assertEqual(profile.allowed_tools_json, {"tools": ["crm_read"]})
        self.assertEqual(profile.business_id, self.business.pk)
        self.assertEqual(self.api.post(f"/api/bots/{bot.pk}/activate/").status_code, 200)
        self.assertEqual(self.api.post(f"/api/bots/{bot.pk}/channels/ensure/", {"channel": "website"}).status_code, 409)
        self.assertEqual(self.api.post(f"/api/bots/{bot.pk}/preview/", {"messages": [{"direction": "inbound", "text": "Hi"}]}, format="json").status_code, 400)
        conversation = BotConversationSerializer(data={"business": self.business.pk, "bot": bot.pk, "channel": "website"})
        self.assertFalse(conversation.is_valid())
        self.assertIn("Customer conversations require an inbox agent.", str(conversation.errors))
        with self.assertRaises(PermissionDenied):
            get_agent_profile(BotConversation(business=self.business, bot=bot, channel="website"))

    def test_scenario_is_immutable_and_second_crm_is_rejected(self):
        created = self.create()
        self.assertEqual(created.status_code, 201, created.data)
        url = f'/api/bots/{created.data["id"]}/'
        self.assertEqual(self.create().status_code, 400)
        for payload in ({"scenario": "inbox"}, {"settings_json": {"scenario": "inbox"}}, {"settings_json": {"auto_crm_pipeline": {"enabled": True}}}):
            self.assertEqual(self.api.patch(url, payload, format="json").status_code, 400)
        self.assertEqual(self.api.patch(url, {"name": "Renamed", "settings_json": {"temperature": 0.1}}, format="json").status_code, 200)
        self.assertEqual(Bot.objects.get(pk=created.data["id"]).scenario, "crm")

    def test_customer_creation_retains_launch_requirements(self):
        result = self.create("inbox")
        self.assertEqual(result.status_code, 201, result.data)
        self.assertFalse(result.data["readiness"]["is_ready"])
        self.assertFalse(AgentProfile.objects.filter(bot_id=result.data["id"]).exists())
        self.assertEqual(self.create("unknown").status_code, 400)
        self.assertEqual(self.create("crm", settings_json={"scenario": "inbox"}).status_code, 400)

    def test_invalid_crm_configuration_does_not_partially_save_bot(self):
        created = self.create()
        bot = Bot.objects.get(pk=created.data["id"])
        profile = AgentProfile.objects.get(bot=bot)
        for rules in ({"sources": ["foreign"]}, {"analyst_enabled": "yes"}):
            response = self.api.put(f"/api/bots/{bot.pk}/configuration/", {
                "bot": {"name": "Must not save"}, "profile": {"id": profile.pk, "rules_json": rules}
            }, format="json")
            self.assertEqual(response.status_code, 400)
            bot.refresh_from_db()
            self.assertEqual(bot.name, "Assistant")

    def test_cross_business_and_manager_creation_are_denied(self):
        other = Business.objects.create(owner=self.user, name="Other", slug="other-scenarios")
        stranger = get_user_model().objects.create_user(username="scenario-other", email="scenario-other@example.com", password="Test12345!")
        BusinessMember.objects.create(business=other, user=stranger, role="owner")
        self.api.force_authenticate(stranger)
        self.assertIn(self.create().status_code, (400, 403))
        member = BusinessMember.objects.create(business=self.business, user=stranger, role="manager")
        self.assertEqual(self.create().status_code, 403)
