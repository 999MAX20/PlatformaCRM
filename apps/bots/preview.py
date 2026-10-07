"""Agent setup rehearsal: saved configuration, shared AI policy, no CRM writes."""
from rest_framework.exceptions import ValidationError

from apps.bots.ai import suggest_bot_reply
from apps.bots.lifecycle import get_bot_readiness
from apps.bots.models import BotConversation
from apps.bots.safety_content import obvious_risk, safety_text
from apps.bots.safety_policy import safety_policy
from apps.conversations.ai_qualification import qualify_conversation
from apps.conversations.auto_pipeline import (
    allows_automatic_reply, decide_qualified_pipeline, resolve_auto_pipeline_config,
)


def preview_agent_dialogue(*, bot, user, messages):
    if bot.scenario != "inbox":
        raise ValidationError({"scenario": "Customer dialogue preview is only available for inbox agents."})
    readiness = get_bot_readiness(bot)
    if not readiness["profile_ready"]:
        raise ValidationError({"profile": "Save an active agent profile before testing."})
    # Deliberately unsaved. AI logs/usage are the only persisted preview effects.
    conversation = BotConversation(business=bot.business, bot=bot, channel="website")
    context = [{"id": None, **message} for message in messages]
    policy = safety_policy(bot)
    latest = context[-1]["text"]
    reason = "message_too_long" if len(latest) > policy["max_message_chars"] else obvious_risk(latest)
    if reason:
        return _blocked_preview(conversation, readiness, reason)
    qualification, qualification_log = qualify_conversation(
        conversation=conversation, user=user, message_context=context,
    )
    config = resolve_auto_pipeline_config(conversation=conversation)
    decision = decide_qualified_pipeline(
        config=config, qualification=qualification, ai_log_id=qualification_log.id,
    )
    handoff = qualification.requires_human_review or qualification.intent in {"spam", "support", "complaint"} or decision.status in {
        "needs_review", "blocked_low_confidence", "blocked_risky_intent", "blocked_fallback",
    }
    if qualification.request_kind in {"security", "private_record", "uncertain"}:
        return _blocked_preview(conversation, readiness, {
            "security": "security_request", "private_record": "private_record_request",
            "uncertain": "uncertain",
        }[qualification.request_kind], qualification_log)
    if qualification.request_kind == "off_topic" and policy["off_topic_handoff_after"] == 1:
        return _blocked_preview(conversation, readiness, "off_topic", qualification_log)
    log = qualification_log
    reply = ""
    sources = []
    if not handoff:
        if qualification.request_kind == "off_topic" and not policy["allow_first_off_topic"]:
            reply = safety_text(conversation, "boundary")
        else:
            result, log, _, sources = suggest_bot_reply(
                conversation=conversation, user=user, auto_mode=True,
                qualification=qualification, message_context=context,
            )
            reply = result.output_text[:config.max_auto_reply_chars].rstrip()
    return {
        "reply": reply,
        "handoff_required": handoff,
        "decision": decision.status,
        "summary": qualification.summary,
        "automatic_reply_enabled": allows_automatic_reply(config=config, decision=decision),
        "automation_enabled": config.enabled and config.mode != "off",
        "readiness": readiness,
        "provider_state": log.input_json.get("provider_state", "mock"),
        "sources": sources,
        "log_id": log.id,
        "model": log.model,
        "provider": log.input_json.get("ai_provider", ""),
    }


def _blocked_preview(conversation, readiness, reason, log=None):
    # Rehearsal reports a decision; it never claims an actual operator notification.
    return {
        "reply": "", "handoff_required": True, "decision": "safety_handoff",
        "summary": safety_text(conversation, reason), "automatic_reply_enabled": False,
        "automation_enabled": False, "readiness": readiness, "sources": [],
        "provider_state": log.input_json.get("provider_state", "mock") if log else "not_called",
        "log_id": log.id if log else None, "model": log.model if log else "",
        "provider": log.input_json.get("ai_provider", "") if log else "",
    }
