"""Remove an agent from use without cascading away its business history."""
from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from apps.activities.services import create_activity_event
from apps.ai_core.models import AgentProfile, AIJob, AIToolCallLog, ApprovalRequest
from apps.automations.engine import cancel_automation_run
from apps.automations.models import AutomationRun
from apps.bots.models import Bot, BotChannel, BotConversation, BotMessage
from apps.businesses.access import Actions, Resources, assert_can
from apps.businesses.models import Business
from apps.core.audit import write_actor_audit_log
from apps.core.models import AuditLog


@transaction.atomic
def delete_agent(*, bot, actor):
    assert_can(actor, bot.business, Resources.AI_AUTOMATION, Actions.DELETE, obj=bot)
    Business.objects.select_for_update().get(pk=bot.business_id)
    bot = Bot.all_objects.select_for_update().get(pk=bot.pk, business_id=bot.business_id)
    if bot.is_deleted:
        return bot
    now = timezone.now()
    bot.status = Bot.Statuses.PAUSED
    bot.settings_json = {**bot.settings_json, "_deleted_at": now.isoformat()}
    bot.settings_json.pop("_automatic_actor_id", None)
    bot.save(update_fields=["status", "settings_json", "updated_at"])
    BotChannel.objects.filter(bot=bot).update(status=BotChannel.Statuses.PAUSED, updated_at=now)
    AgentProfile.objects.filter(bot=bot).update(is_active=False, updated_at=now)
    conversations = BotConversation.objects.filter(bot=bot, business=bot.business)
    conversations.update(bot_enabled=False, updated_at=now)
    # Existing workers also recheck the paused agent/fingerprint before effects.
    reason = "AI agent deleted; pending work stopped."
    from apps.ai_core.models import AgentTurn
    from apps.ai_core.conversation_state import OPEN, stop_turn
    for turn in AgentTurn.objects.filter(conversation__agent=bot, status__in=OPEN).select_related("conversation"):
        stop_turn(turn, actor)
    AIJob.objects.filter(business=bot.business, input_json__runtime_context___agent__agent_id=bot.pk,
        status__in=[AIJob.Statuses.PENDING, AIJob.Statuses.RUNNING, AIJob.Statuses.RETRY_SCHEDULED]
    ).update(status=AIJob.Statuses.FAILED, error=reason, next_retry_at=None, locked_at=None, completed_at=now, updated_at=now)
    commands = AIToolCallLog.objects.filter(business=bot.business).filter(
        Q(input_json___agent__agent_id=bot.pk) | Q(conversation__in=conversations))
    pending = commands.filter(status=AIToolCallLog.Statuses.SUGGESTED)
    ApprovalRequest.objects.filter(ai_tool_call_log__in=pending,
        status__in=[ApprovalRequest.Statuses.PENDING, ApprovalRequest.Statuses.APPROVED]
    ).update(status=ApprovalRequest.Statuses.REJECTED, rejected_by=actor, rejected_at=now, reason=reason, updated_at=now)
    pending.update(status=AIToolCallLog.Statuses.REJECTED, error=reason)
    BotMessage.objects.filter(conversation__in=conversations, sender_type=BotMessage.SenderTypes.BOT,
        status__in=[BotMessage.Statuses.QUEUED, BotMessage.Statuses.RETRY_SCHEDULED]
    ).update(status=BotMessage.Statuses.FAILED, error_text=reason, delivery_next_retry_at=None, delivery_locked_at=None)
    runs = AutomationRun.objects.filter(business=bot.business, entity_type="BotConversation",
        entity_id__in=[str(pk) for pk in conversations.values_list("pk", flat=True)],
        status__in=[AutomationRun.Statuses.PENDING, AutomationRun.Statuses.RUNNING,
                    AutomationRun.Statuses.WAITING, AutomationRun.Statuses.RETRY_SCHEDULED])
    for run in runs:
        cancel_automation_run(run)
    metadata = {"kind": "agent_deletion", "history_preserved": True}
    write_actor_audit_log(actor=actor, action=AuditLog.Actions.DELETE, instance=bot, metadata=metadata)
    create_activity_event(business=bot.business, actor=actor, event_type="bot.deleted", instance=bot, metadata=metadata)
    return bot
