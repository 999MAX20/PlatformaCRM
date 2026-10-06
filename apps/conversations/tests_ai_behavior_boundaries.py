"""Decision boundaries complement real-provider samples without paying for randomness."""
from django.test import SimpleTestCase

from apps.conversations.ai_qualification import ConversationQualification
from apps.conversations.auto_pipeline import AutoPipelineConfig, allows_automatic_reply, decide_qualified_pipeline


class AIBehaviorBoundaryTests(SimpleTestCase):
    def decision(self, config, **values):
        qualification = ConversationQualification(intent="purchase_interest", summary="Synthetic request", **values)
        return decide_qualified_pipeline(config=config, qualification=qualification, ai_log_id=None)

    def test_confidence_thresholds_are_inclusive_and_separate(self):
        config = AutoPipelineConfig(enabled=True, mode="draft_deal", min_lead_confidence=.7, min_deal_confidence=.8)
        for confidence, expected in ((.699, "blocked_low_confidence"), (.7, "proposed_lead_task"),
                                     (.799, "proposed_lead_task"), (.8, "proposed_draft_deal")):
            with self.subTest(confidence=confidence):
                self.assertEqual(self.decision(config, confidence=confidence).status, expected)

    def test_explicit_review_blocks_both_policies_even_at_full_confidence(self):
        for policy in ("staff_confirmation", "automatic"):
            config = AutoPipelineConfig(enabled=True, mode="draft_deal", creation_policy=policy, auto_send_reply=True)
            decision = self.decision(config, confidence=1, requires_human_review=True)
            self.assertEqual(decision.status, "needs_review")
            self.assertFalse(allows_automatic_reply(config=config, decision=decision))

    def test_fallback_toggle_changes_mock_fallback_only(self):
        for review, expected in ((True, "blocked_fallback"), (False, "proposed_lead_task")):
            config = AutoPipelineConfig(enabled=True, mode="lead_task", require_review_on_fallback=review, auto_send_reply=True)
            decision = self.decision(config, confidence=.9, requires_human_review=True,
                                     reason="Fallback qualification used because AI output was not valid JSON. Provider=mock.")
            self.assertEqual(decision.status, expected)
            self.assertEqual(allows_automatic_reply(config=config, decision=decision), not review)

    def test_auto_reply_toggle_and_risky_intents_remain_independent_of_creation_mode(self):
        for mode in ("off", "triage", "lead_task", "draft_deal"):
            for enabled in (False, True):
                config = AutoPipelineConfig(enabled=True, mode=mode, auto_send_reply=enabled)
                ordinary = self.decision(config, confidence=.9)
                self.assertEqual(allows_automatic_reply(config=config, decision=ordinary), enabled and mode != "off")
                for intent in ("complaint", "support", "spam"):
                    qualification = ConversationQualification(intent=intent, confidence=1, summary="Risky request")
                    decision = decide_qualified_pipeline(config=config, qualification=qualification, ai_log_id=None)
                    self.assertFalse(allows_automatic_reply(config=config, decision=decision))
