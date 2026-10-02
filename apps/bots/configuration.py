"""The editor commits bot runtime settings and its profile as one unit."""
from django.db import transaction
from rest_framework.exceptions import ValidationError

from apps.ai_core.models import AgentProfile
from apps.businesses.access import Actions, Resources, assert_can
from apps.core.audit import write_actor_audit_log
from apps.core.models import AuditLog
from apps.bots.models import Bot


@transaction.atomic
def save_agent_configuration(*, bot, actor, data):
    from apps.ai_core.serializers import AgentProfileSerializer
    from apps.bots.serializers import BotSerializer
    from apps.bots.lifecycle import update_bot

    bot = Bot.objects.select_for_update().get(pk=bot.pk)
    assert_can(actor, bot.business, Resources.AI_AUTOMATION, Actions.MANAGE, obj=bot)
    if not isinstance(data, dict) or not isinstance(data.get("bot"), dict) or not isinstance(data.get("profile"), dict):
        raise ValidationError("Both bot and profile settings are required.")
    bot_fields = {"name", "default_language", "settings_json"}
    profile_fields = {"id", "name", "role_description", "tone", "language", "is_active", "system_prompt", "rules_json", "allowed_tools_json", "escalation_rules_json"}
    if set(data["bot"]) - bot_fields or set(data["profile"]) - profile_fields:
        raise ValidationError("Unsupported agent configuration fields.")
    profile_data = dict(data["profile"])
    profile_id = profile_data.pop("id", None)
    if profile_id is not None and (isinstance(profile_id, bool) or not isinstance(profile_id, int)):
        raise ValidationError({"profile": "Invalid profile identifier."})
    profiles = AgentProfile.objects.filter(business=bot.business, bot=bot)
    profile = profiles.filter(pk=profile_id).first() if profile_id else profiles.order_by("-is_active", "-updated_at", "-id").first()
    if profile_id and profile is None:
        raise ValidationError({"profile": "Profile does not belong to this agent."})
    bot_input = BotSerializer(bot, data=data["bot"], partial=True)
    bot_input.is_valid(raise_exception=True)
    language = bot_input.validated_data.get("default_language", bot.default_language)
    profile_input = AgentProfileSerializer(profile, data={**profile_data, "business": bot.business_id, "bot": bot.id, "language": language}, partial=profile is not None)
    profile_input.is_valid(raise_exception=True)
    from apps.bots.automation_policy import authorize_configuration
    tools = profile_input.validated_data.get("allowed_tools_json", profile.allowed_tools_json if profile else {}).get("tools", [])
    bot_input.validated_data["settings_json"] = authorize_configuration(
        bot, bot_input.validated_data.get("settings_json", bot.settings_json), tools, actor,
    )
    bot = update_bot(bot=bot, validated_data=dict(bot_input.validated_data))
    profile = profile_input.save()
    for instance in (bot, profile):
        write_actor_audit_log(actor=actor, action=AuditLog.Actions.UPDATE, instance=instance,
                              metadata={"kind": "agent_configuration", "bot_id": bot.id})
    return bot, profile
