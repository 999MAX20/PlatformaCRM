"""Scenario preflight supplements, but never replaces, write-time authorization."""
from django.contrib.auth import get_user_model
from rest_framework.exceptions import ValidationError

from apps.businesses.access import Actions, Resources, can
from apps.businesses.booking_settings import validate_booking_responsible
from apps.core.domain_errors import AssigneeUnavailable


def booking_readiness(bot, profile):
    from apps.conversations.auto_pipeline import resolve_auto_pipeline_config
    from apps.bots.models import BotConversation

    config = resolve_auto_pipeline_config(conversation=BotConversation(bot=bot, business=bot.business))
    tools = (profile.allowed_tools_json or {}).get("tools", []) if profile else []
    enabled = (config.enabled and config.mode in {"lead_task", "draft_deal", "customer_actions"}
               and config.appointment_creation_policy == "automatic" and config.create_appointment
               and "create_appointment" in tools)
    missing = []
    if enabled:
        responsible = bot.business.ai_booking_responsible_user
        try:
            if validate_booking_responsible(bot.business, responsible) is None:
                missing.append("responsible")
        except (ValidationError, AssigneeUnavailable):
            missing.append("responsible")
        actor = get_user_model().objects.filter(
            pk=(bot.settings_json or {}).get("_automatic_actor_id"), is_active=True,
        ).first()
        if actor is None or not all(can(actor, bot.business, resource, action).allowed for resource, action in (
            (Resources.AI_AUTOMATION, Actions.MANAGE),
            (Resources.CONVERSATIONS, Actions.UPDATE),
            (Resources.APPOINTMENTS, Actions.CREATE),
        )):
            missing.append("authorization")
    return {"enabled": enabled, "setup_ready": enabled and not missing, "missing": missing}
