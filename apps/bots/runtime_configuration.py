"""Fingerprint persisted inputs so old AI work cannot outlive configuration changes."""
import hashlib
import json

from apps.ai_core.models import AgentProfile, BusinessKnowledgeItem
from apps.bots.models import Bot, BotChannel


def agent_runtime_fingerprint(conversation):
    bot = Bot.objects.filter(pk=conversation.bot_id, business_id=conversation.business_id).values(
        "id", "name", "status", "default_language", "settings_json",
    ).first()
    from apps.bots.ai import get_agent_profile
    selected = get_agent_profile(conversation)
    fields = ("id", "name", "role_description", "tone", "language", "system_prompt", "rules_json", "allowed_tools_json", "escalation_rules_json")
    profile = {field: getattr(selected, field) for field in fields} if selected else None
    knowledge = list(BusinessKnowledgeItem.objects.filter(business_id=conversation.business_id, is_active=True).order_by("id").values("id", "title", "category", "content"))
    channel = BotChannel.objects.filter(bot_id=conversation.bot_id, channel=conversation.channel).first()
    channel_settings = {"id": channel.id, "status": channel.status, "pipeline": (channel.config_json or {}).get("auto_crm_pipeline")} if channel else None
    content = json.dumps([bot, profile, knowledge, channel_settings], sort_keys=True, ensure_ascii=False, default=str)
    return hashlib.sha256(content.encode("utf-8")).hexdigest()
