"""Explicit, revocable creation consent using existing business permissions."""
from django.contrib.auth import get_user_model
from django.db import transaction
from rest_framework.exceptions import PermissionDenied

from apps.bots.ai import get_agent_profile
from apps.bots.lifecycle import conversation_ai_block_reason
from apps.bots.runtime_configuration import agent_runtime_fingerprint
from apps.businesses.access import Actions, Resources, assert_can


CREATE_RESOURCES = {
    "create_client": Resources.CLIENTS, "create_lead": Resources.LEADS,
    "create_task": Resources.TASKS, "create_deal": Resources.DEALS,
    "create_appointment": Resources.APPOINTMENTS,
}


def authorize_configuration(bot, settings, tools, actor):
    value = dict(settings)
    value.pop("_automatic_actor_id", None)
    pipeline = value.get("auto_crm_pipeline") or {}
    if pipeline.get("creation_policy") == "automatic":
        assert_can(actor, bot.business, Resources.AI_AUTOMATION, Actions.MANAGE)
        for tool in tools:
            if tool in CREATE_RESOURCES:
                assert_can(actor, bot.business, CREATE_RESOURCES[tool], Actions.CREATE)
        value["_automatic_actor_id"] = actor.id
    return value


@transaction.atomic
def automatic_creation_actor(conversation, actions, *, expected_fingerprint=None):
    """Called again inside the domain transaction immediately before writes."""
    from apps.conversations.auto_pipeline import resolve_auto_pipeline_config
    from apps.bots.models import Bot
    from apps.ai_core.inbox_runtime import assert_current_inbound

    assert_current_inbound(conversation)

    conversation.bot = Bot.objects.select_for_update().get(pk=conversation.bot_id, business_id=conversation.business_id)

    if conversation_ai_block_reason(conversation):
        raise PermissionDenied("Agent is no longer eligible for automatic actions.")
    if expected_fingerprint and expected_fingerprint != agent_runtime_fingerprint(conversation):
        raise PermissionDenied("Agent configuration changed. Automatic work was stopped.")
    conversation.bot.refresh_from_db()
    channel = conversation.bot.channels.filter(channel=conversation.channel).first()
    config = resolve_auto_pipeline_config(conversation=conversation, channel=channel)
    # A channel override can restrict behavior; it cannot grant autonomous creation.
    own = (conversation.bot.settings_json or {}).get("auto_crm_pipeline") or {}
    if own.get("creation_policy") != "automatic" or not config.enabled or config.mode == "off":
        raise PermissionDenied("Automatic creation is not enabled.")
    profile = get_agent_profile(conversation)
    tools = (profile.allowed_tools_json or {}).get("tools", []) if profile else []
    actor = get_user_model().objects.filter(pk=(conversation.bot.settings_json or {}).get("_automatic_actor_id"), is_active=True).first()
    if actor is None:
        raise PermissionDenied("Automatic creation has no active authorizing member.")
    assert_can(actor, conversation.business, Resources.AI_AUTOMATION, Actions.MANAGE)
    assert_can(actor, conversation.business, Resources.CONVERSATIONS, Actions.UPDATE, obj=conversation)
    for action in actions:
        if action not in CREATE_RESOURCES or action not in tools:
            raise PermissionDenied("The agent capability is disabled.")
        if action == "create_appointment" and not config.create_appointment:
            raise PermissionDenied("Automatic booking is disabled.")
        if action == "create_deal" and config.mode != "draft_deal":
            raise PermissionDenied("Automatic deals are disabled.")
        assert_can(actor, conversation.business, CREATE_RESOURCES[action], Actions.CREATE)
    return actor
