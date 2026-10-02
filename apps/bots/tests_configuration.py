from unittest.mock import patch

from django.test import TestCase
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.ai_core.models import AgentProfile
from apps.bots.models import Bot
from apps.businesses.models import Business, BusinessMember


class AgentConfigurationTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="agent-config", email="config@example.test")
        self.business = Business.objects.create(owner=self.user, name="Configuration", slug="agent-config")
        BusinessMember.objects.create(business=self.business, user=self.user, role="owner")
        self.bot = Bot.objects.create(business=self.business, name="Before", settings_json={"temperature": 0.4})
        self.profile = AgentProfile.objects.create(business=self.business, bot=self.bot, name="Before", tone="friendly")
        self.api = APIClient()
        self.api.force_authenticate(self.user)
        self.url = f"/api/bots/{self.bot.id}/configuration/"

    def payload(self):
        return {"bot": {"name": "After", "default_language": "kk", "settings_json": {"temperature": 0.1}},
                "profile": {"id": self.profile.id, "name": "After", "tone": "formal", "is_active": True}}

    def assert_unchanged(self):
        self.bot.refresh_from_db(); self.profile.refresh_from_db()
        self.assertEqual(self.bot.name, "Before")
        self.assertEqual(self.profile.tone, "friendly")

    def test_atomic_save_and_readback(self):
        response = self.api.put(self.url, self.payload(), format="json")
        self.assertEqual(response.status_code, 200, response.data)
        self.bot.refresh_from_db(); self.profile.refresh_from_db()
        self.assertEqual(self.bot.settings_json["temperature"], 0.1)
        self.assertEqual(self.profile.tone, "formal")
        self.assertEqual(self.profile.language, "kk")
        self.assertEqual(response.data["profile"]["id"], self.profile.id)

    def test_invalid_either_half_preserves_both(self):
        for section, field, value in [("profile", "tone", "invalid"), ("bot", "settings_json", {"temperature": 8})]:
            with self.subTest(section=section):
                payload = self.payload(); payload[section][field] = value
                response = self.api.put(self.url, payload, format="json")
                self.assertEqual(response.status_code, 400, response.data)
                self.assert_unchanged()

    def test_profile_save_failure_rolls_back_bot(self):
        with patch("apps.ai_core.serializers.AgentProfileSerializer.save", side_effect=RuntimeError("test rollback")):
            response = self.api.put(self.url, self.payload(), format="json")
        self.assertEqual(response.status_code, 500)
        self.assert_unchanged()

    def test_cannot_supply_foreign_profile_or_reparent_bot(self):
        foreign = Business.objects.create(owner=self.user, name="Foreign", slug="foreign-agent-config")
        profile = AgentProfile.objects.create(business=foreign, name="Foreign")
        payload = self.payload(); payload["profile"]["id"] = profile.id
        self.assertEqual(self.api.put(self.url, payload, format="json").status_code, 400)
        payload = self.payload(); payload["bot"]["business"] = foreign.id
        self.assertEqual(self.api.put(self.url, payload, format="json").status_code, 400)
        self.assert_unchanged()

    def test_denied_user_cannot_save(self):
        user = User.objects.create_user(username="agent-operator", email="operator@example.test")
        BusinessMember.objects.create(business=self.business, user=user, role="operator")
        self.api.force_authenticate(user)
        self.assertIn(self.api.put(self.url, self.payload(), format="json").status_code, [403, 404])
        self.assert_unchanged()
