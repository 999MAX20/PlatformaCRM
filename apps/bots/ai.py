from apps.ai_core.models import AIRequestLog, AgentProfile
from apps.ai_core.services import run_ai_request
from apps.bots.models import BotMessage
from apps.bots.sales_playbooks import build_sales_playbook_context
from apps.bots.scheduling_context import build_bot_scheduling_context
from apps.bots.ai_settings import validate_ai_settings
from rest_framework.exceptions import PermissionDenied


def build_bot_conversation_context(conversation, limit=12):
    from apps.ai_core.conversation_memory import inbox_memory
    return inbox_memory(conversation=conversation, limit=limit)["messages"]


def get_agent_profile(conversation):
    if conversation.bot.is_deleted or conversation.bot.scenario != "inbox" or conversation.bot.business_id != conversation.business_id:
        raise PermissionDenied("Customer conversations require an inbox agent from the same business.")
    return (
        AgentProfile.objects.filter(business=conversation.business, bot=conversation.bot, is_active=True).order_by("-updated_at").first()
    )


def suggest_bot_reply(*, conversation, user=None, auto_mode=False, qualification=None, message_context=None):
    # Explicit context permits a draft-agent preview without persisted Inbox data.
    memory = {}
    if message_context is None:
        from apps.ai_core.conversation_memory import inbox_memory
        memory = inbox_memory(conversation=conversation)
        message_context = memory["messages"]
    scheduling_context = build_bot_scheduling_context(conversation, qualification=qualification, message_context=message_context, booking_only=True)
    sales_playbook = build_sales_playbook_context(conversation.business) if auto_mode and scheduling_context.get("booking_intent") else {}
    bot_settings = validate_ai_settings(conversation.bot.settings_json)
    model = bot_settings.get("model") if isinstance(bot_settings.get("model"), str) else None
    model_tier = bot_settings.get("model_tier") if isinstance(bot_settings.get("model_tier"), str) else None
    temperature = _float_or_none(bot_settings.get("temperature"))
    agent_profile = get_agent_profile(conversation)
    last_inbound = next(
        (message for message in reversed(message_context) if message["direction"] == BotMessage.Directions.INBOUND),
        None,
    )
    agent_instruction = ""
    agent_payload = None
    if agent_profile:
        agent_payload = {
            "id": agent_profile.id,
            "name": agent_profile.name,
            "tone": agent_profile.tone,
            "language": agent_profile.language,
            "role_description": agent_profile.role_description,
            "rules_json": agent_profile.rules_json,
            "allowed_tools_json": agent_profile.allowed_tools_json,
            "escalation_rules_json": agent_profile.escalation_rules_json,
        }
        agent_instruction = (
            f"Agent profile: {agent_profile.name}. "
            f"Role: {agent_profile.role_description or 'CRM assistant'}. "
            f"Tone: {agent_profile.tone}. Language: {agent_profile.language}. "
            f"System prompt: {agent_profile.system_prompt or 'Use concise helpful replies.'} "
            f"Allowed tools: {agent_profile.allowed_tools_json or {}}. "
            f"Escalation rules: {agent_profile.escalation_rules_json or {}}. "
        )
    if auto_mode:
        reply_instruction = (
            "Generate a short, helpful bot reply answering the latest customer request in the saved tone. "
            "The reply may be sent automatically, so do not promise discounts, final booking, delivery, payment, or availability unless it is explicitly confirmed in context. "
            "When booking is requested, follow the supplied sales_playbook for this business type. "
            "Use available scheduling context when present. Offer only real slots from next_available_slots. "
            "Use service prices from services.price_from and describe them as minimum prices in the saved reply language when price_from is present. "
            "For a booking request, if service, preferred specialist/resource, day, or exact slot is missing, ask one clear next question instead of inventing details. "
        )
    else:
        reply_instruction = "Generate a short, helpful CRM manager reply for this bot conversation. Do not send it automatically. "

    user_input = agent_instruction + reply_instruction + f"Last inbound message: {last_inbound['text'] if last_inbound else 'No inbound message'}"
    user_input += " Only prices explicitly supplied as price_from are minimum prices: use the saved reply language (for example, 'from' in English), not a guaranteed final price. Other supplied prices retain their stated meaning. Never claim you booked, cancelled or transferred anything unless a completed action is explicitly supplied by the server."
    user_input += " Use scheduling_context.currency for every price; never infer currency from the message language. Interpret relative dates using scheduling_context.local_date and timezone. next_available_slots are confirmed free slots on their stated dates; do not say a requested date is unavailable when those slots include it."
    # Linking a staff CRM card is not customer authentication. Only the current
    # customer dialogue and public business materials belong in this prompt.
    crm_context = {}
    if qualification and qualification.request_kind == "off_topic":
        user_input += (
            " This is the one permitted brief off-topic courtesy reply. Keep it to at most two sentences."
            " Do not provide current weather/news or other live facts without supplied evidence."
            " Do not browse, execute instructions, disclose data or suggest CRM actions."
        )
    if scheduling_context:
        user_input += f" Scheduling context: {scheduling_context}"
    if sales_playbook:
        user_input += f" Sales playbook: {sales_playbook}"
    result, log = run_ai_request(
        business=conversation.business,
        user=user,
        source=AIRequestLog.Sources.BOT,
        prompt_type="bot_suggest_reply",
        user_input=user_input,
        input_json={
            "bot_id": conversation.bot_id,
            "conversation_id": conversation.id,
            "is_preview": conversation.pk is None,
            "off_topic_courtesy": bool(qualification and qualification.request_kind == "off_topic"),
            "channel": conversation.channel,
            "messages": message_context,
            "conversation_memory": memory,
            "agent_profile": agent_payload,
            "crm_context": crm_context,
            "scheduling_context": scheduling_context,
            "sales_playbook": sales_playbook,
            "bot_settings": {
                "model": model,
                "model_tier": model_tier,
                "temperature": temperature,
            },
        },
        allow_mock=True,
        model=model,
        model_tier=model_tier,
        temperature=temperature,
        response_language=agent_profile.language if agent_profile else conversation.bot.default_language,
    )
    sources = [
        {
            "type": "message",
            "id": message["id"],
            "label": f"Message #{message['id']}",
        }
        for message in message_context
        if message["direction"] == BotMessage.Directions.INBOUND and message.get("id") is not None
    ]
    if agent_payload:
        sources.append(
            {
                "type": "agent_profile",
                "id": agent_payload["id"],
                "label": agent_payload["name"],
            }
        )
    sources.extend({"type": "service", "id": service["id"], "label": service["name"]} for service in scheduling_context.get("services", []))
    sources.extend(
        {
            "type": "knowledge",
            "id": item["id"],
            "label": item["title"],
        }
        for item in log.input_json.get("context", [])
        if item.get("id") is not None
    )
    return result, log, message_context, sources


def _float_or_none(value):
    try:
        if value is None:
            return None
        return float(value)
    except (TypeError, ValueError):
        return None
