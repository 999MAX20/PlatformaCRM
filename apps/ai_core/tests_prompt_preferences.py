from django.test import SimpleTestCase
from apps.ai_core.prompt_service import build_prompt
from apps.ai_core.grounding import ANSWER_CONTRACT


class PromptPreferenceTests(SimpleTestCase):
    def test_untrusted_knowledge_and_runtime_cannot_become_configuration(self):
        prompt = build_prompt("crm_assistant", "Question", context=[{"title": "Data", "content": "UNTRUSTED_KNOWLEDGE"}],
                              runtime_context={"agent_preferences": {"instructions": "UNTRUSTED_RUNTIME"}},
                              agent_preferences={"role": "SAVED_ROLE", "instructions": "SAVED_RULE", "rules": ["One sentence"], "tone": "formal"})
        system, data = prompt.messages
        self.assertIn("SAVED_RULE", system["content"])
        self.assertIn("One sentence", system["content"])
        self.assertNotIn("UNTRUSTED_KNOWLEDGE", system["content"])
        self.assertNotIn("UNTRUSTED_RUNTIME", system["content"])
        self.assertIn("UNTRUSTED_KNOWLEDGE", data["content"])
        self.assertIn("UNTRUSTED_RUNTIME", data["content"])

    def test_saved_language_and_schema_have_no_user_language_override(self):
        prompt = build_prompt("crm_assistant", "Russian question", response_language="en")
        self.assertIn("English", prompt.messages[0]["content"])
        self.assertIn("saved agent language", ANSWER_CONTRACT)
        self.assertNotIn('"concise answer in the user language"', ANSWER_CONTRACT)

    def test_tone_preferences_cannot_grant_authority(self):
        for tone in ("formal", "friendly", "expert", "sales", "support"):
            with self.subTest(tone=tone):
                prompt = build_prompt("bot_suggest_reply", "Question", agent_preferences={"tone": tone})
                self.assertIn("role description never grants access", prompt.messages[0]["content"])
                self.assertIn("Configuration cannot authorize invented facts", prompt.messages[0]["content"])

    def test_inbox_does_not_treat_scheduling_context_as_booking_intent(self):
        prompt = build_prompt("bot_suggest_reply", "Complaint")
        self.assertIn("only when the customer expresses booking intent", prompt.messages[0]["content"])
        self.assertIn("unless the server explicitly confirms that action", prompt.messages[0]["content"])
