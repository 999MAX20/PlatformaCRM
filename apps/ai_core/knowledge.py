"""Agent-owned knowledge and explicitly connected shared business materials."""
from django.db import transaction
from django.db.models import Q
from rest_framework.exceptions import NotFound, ValidationError

from apps.activities.services import create_activity_event
from apps.ai_core.models import BusinessKnowledgeItem
from apps.bots.models import Bot
from apps.businesses.access import Actions, Resources, assert_can
from apps.businesses.models import Business
from apps.core.audit import write_actor_audit_log
from apps.core.models import AuditLog


def available_agent(*, business, agent_id, lock=False):
    agents = Bot.objects.filter(business=business)
    if lock:
        agents = agents.select_for_update()
    agent = agents.filter(pk=agent_id).first()
    if agent is None:
        raise NotFound("Agent is unavailable.")
    return agent


def agent_knowledge(*, business, agent):
    if agent is None or agent.business_id != business.pk or agent.is_deleted:
        return BusinessKnowledgeItem.objects.none()
    items = BusinessKnowledgeItem.objects.filter(business=business).filter(
        Q(bot=agent) | Q(bot__isnull=True, connected_agents=agent)
    ).distinct()
    return items.filter(customer_visible=True) if agent.scenario == Bot.Scenarios.INBOX else items


def _audit(*, actor, item, action, metadata):
    write_actor_audit_log(actor=actor, action=action, instance=item, metadata=metadata)
    create_activity_event(business=item.business, actor=actor,
        event_type=f"businessknowledgeitem.{action}d", instance=item, metadata=metadata)


@transaction.atomic
def save_knowledge(*, actor, data, item=None):
    business = item.business if item else data["business"]
    assert_can(actor, business, Resources.AI_AUTOMATION, Actions.UPDATE if item else Actions.CREATE, obj=item)
    Business.objects.select_for_update().get(pk=business.pk)
    if item:
        item = BusinessKnowledgeItem.objects.select_for_update().get(pk=item.pk, business=business)
        if data.get("business", business) != business or data.get("bot", item.bot) != item.bot:
            raise ValidationError("Knowledge ownership cannot change.")
    bot = data.get("bot", item.bot if item else None)
    if bot:
        available_agent(business=business, agent_id=bot.pk, lock=True)
    if data.get("customer_visible", item.customer_visible if item else False):
        from apps.bots.safety_content import contains_secret
        if contains_secret({key: data.get(key, getattr(item, key, "")) for key in ("title", "content")}):
            raise ValidationError("Remove credentials from customer-facing materials before saving.")
    if item is None:
        item = BusinessKnowledgeItem.objects.create(**data)
        action = AuditLog.Actions.CREATE
    else:
        for field, value in data.items():
            setattr(item, field, value)
        item.save()
        action = AuditLog.Actions.UPDATE
    _audit(actor=actor, item=item, action=action, metadata={"kind": "agent_knowledge", "bot_id": item.bot_id})
    return item


@transaction.atomic
def connect_shared_knowledge(*, actor, item, agent_id, connected, allow_customer_use=False):
    assert_can(actor, item.business, Resources.AI_AUTOMATION, Actions.MANAGE)
    Business.objects.select_for_update().get(pk=item.business_id)
    agent = available_agent(business=item.business, agent_id=agent_id, lock=True)
    item = BusinessKnowledgeItem.objects.select_for_update().get(pk=item.pk, business=agent.business)
    if item.bot_id is not None:
        raise ValidationError("Only shared materials can be connected.")
    if connected and agent.scenario == Bot.Scenarios.INBOX:
        if not item.customer_visible and not allow_customer_use:
            raise ValidationError("Explicitly allow this material in customer answers before connecting it.")
        from apps.bots.safety_content import contains_secret
        if contains_secret([item.title, item.content]):
            raise ValidationError("Credentials cannot be published to customer agents.")
        if not item.customer_visible:
            item.customer_visible = True
            item.save(update_fields=["customer_visible", "updated_at"])
            _audit(actor=actor, item=item, action=AuditLog.Actions.UPDATE,
                   metadata={"kind": "customer_knowledge_visibility", "customer_visible": True})
    exists = item.connected_agents.filter(pk=agent.pk).exists()
    if exists != connected:
        if connected:
            item.connected_agents.add(agent)
        else:
            item.connected_agents.remove(agent)
        _audit(actor=actor, item=item, action=AuditLog.Actions.UPDATE,
               metadata={"kind": "knowledge_connection", "bot_id": agent.pk, "connected": connected})
    return item
