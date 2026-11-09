"""Conversational replies have no CRM facts or executable tools."""
import json

from apps.ai_core.ai_client import AIClientError
from apps.ai_core.services import run_ai_request


def prepare_voice_chat(turn, language):
    history = list(turn.conversation.turns.filter(
        status="completed", sequence__lt=turn.sequence,
        memory_epoch=turn.memory_epoch, plan_json__intent__in=["greeting", "chat"],
        access_fingerprint=turn.access_fingerprint,
    ).order_by("-sequence")[:6])
    messages = [{"user": item.message[:2000], "assistant": item.response[:2000]} for item in reversed(history)]
    result, log = run_ai_request(
        business=turn.conversation.business, user=turn.conversation.owner,
        prompt_type="voice_chat", user_input=turn.message,
        input_json={"chat_history": messages}, response_language=language,
        model="openai/gpt-4o-mini", allow_mock=False,
        response_contract=' Return only JSON with exactly one key: {"reply":"your natural response"}.',
    )
    if result.is_mock:
        raise AIClientError(code="provider_unavailable", retryable=False)
    try:
        value = json.loads(result.output_text)
        if (not isinstance(value, dict) or set(value) != {"reply"}
                or not isinstance(value["reply"], str) or not 1 <= len(value["reply"].strip()) <= 4000):
            raise ValueError
    except (ValueError, TypeError):
        raise AIClientError(code="invalid_action_plan", retryable=False) from None
    return {"response": value["reply"].strip(), "sources": [], "references": [], "request_log_id": log.pk}
