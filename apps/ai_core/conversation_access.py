"""Conversation identity and memory visibility, separate from model decisions."""
import hashlib
import json

from django.contrib.auth import get_user_model
from rest_framework.exceptions import NotFound, PermissionDenied, ValidationError

from apps.ai_core.agent_runtime import bind_agent
from apps.ai_core.knowledge import agent_knowledge, available_agent
from apps.ai_core.models import AgentConversation
from apps.ai_core.workflows import assert_workflow_enabled
from apps.bots.models import Bot
from apps.businesses.access import Actions, ROLE_PRESETS, Resources, assert_can, can, team_user_ids_for
from apps.businesses.models import Business, BusinessMember, RolePermission
from apps.businesses.capabilities import default_capabilities


def staff_agent(*, business, agent_id, user, write=False):
    if not user or not get_user_model().objects.filter(pk=user.pk, is_active=True).exists():
        raise PermissionDenied("Your account is unavailable.")
    if not (can(user, business, Resources.AI_ASSISTANT, Actions.SUGGEST if write else Actions.VIEW).allowed
            or can(user, business, Resources.AI_ANALYST, Actions.VIEW).allowed):
        raise PermissionDenied("Your role cannot access agent conversations.")
    agent = available_agent(business=business, agent_id=agent_id)
    if agent.scenario != Bot.Scenarios.CRM:
        raise PermissionDenied("Employee conversations require a CRM agent.")
    return agent


def staff_conversations(*, business, agent_id, user):
    agent = staff_agent(business=business, agent_id=agent_id, user=user)
    return AgentConversation.objects.filter(business=business, agent=agent, owner=user, kind=AgentConversation.Kinds.STAFF)


def staff_conversation(*, conversation_id, user, lock=False, write=False):
    query = AgentConversation.objects.select_related("business", "agent", "owner")
    if lock:
        query = query.select_for_update(of=("self",))
    thread = query.filter(pk=conversation_id, owner=user, kind=AgentConversation.Kinds.STAFF).first()
    if thread is None:
        raise NotFound("Conversation is unavailable.")
    staff_agent(business=thread.business, agent_id=thread.agent_id, user=user, write=write)
    if write and thread.is_archived:
        raise ValidationError("Start a new conversation or restore this one.")
    return thread


def create_staff_conversation(*, business, agent_id, user, title="", mode="work"):
    agent = staff_agent(business=business, agent_id=agent_id, user=user, write=True)
    assert_can(user, business, Resources.AI_ANALYST if mode == "analytics" else Resources.AI_ASSISTANT,
               Actions.VIEW if mode == "analytics" else Actions.SUGGEST)
    with bind_agent(agent.pk):
        assert_workflow_enabled(business, "analyst" if mode == "analytics" else "employee")
    return AgentConversation.objects.create(business=business, agent=agent, owner=user,
                                           kind=AgentConversation.Kinds.STAFF, title=title[:120])


def inbox_memory_conversation(conversation):
    if not conversation.pk:
        return None  # Setup previews never create operational customer memory.
    if conversation.bot.business_id != conversation.business_id or conversation.bot.scenario != Bot.Scenarios.INBOX or conversation.bot.is_deleted:
        raise PermissionDenied("Customer memory is unavailable.")
    thread, _ = AgentConversation.objects.get_or_create(inbox_conversation=conversation,
        defaults={"business": conversation.business, "agent": conversation.bot, "kind": AgentConversation.Kinds.INBOX})
    if thread.business_id != conversation.business_id or thread.agent_id != conversation.bot_id or thread.owner_id is not None:
        raise PermissionDenied("Customer memory scope is invalid.")
    return thread


def memory_access_fingerprint(*, business, agent, user=None):
    """Only access/source changes invalidate memory; tone edits preserve continuity."""
    from apps.ai_core.models import AgentProfile
    profile = AgentProfile.objects.filter(business=business, bot=agent, is_active=True).order_by("-updated_at", "-id").first()
    knowledge = list(agent_knowledge(business=business, agent=agent).filter(is_active=True).order_by("pk").values("id", "title", "content", "category"))
    payload = {"business": business.pk, "agent": agent.pk, "user": getattr(user, "pk", None),
               "knowledge": knowledge, "sources": (profile.rules_json or {}).get("sources") if profile else [],
               "active_profile": profile.pk if profile else None,
               "analyst_enabled": (profile.rules_json or {}).get("analyst_enabled", True) if profile else False}
    if user is not None:
        # Snapshot authority inputs in bounded queries. Actual reads/actions
        # still use existing permission services, never this hash as a grant.
        membership = BusinessMember.objects.filter(business=business, user=user).values(
            "role", "is_active", "business_role_id", "business_role__is_active").first()
        payload["membership"] = membership
        payload["owner"] = Business.objects.filter(pk=business.pk).values_list("owner_id", flat=True).first()
        payload["account"] = get_user_model().objects.filter(pk=user.pk).values("is_active", "role", "is_staff", "is_superuser").first()
        payload["preset"] = ROLE_PRESETS.get(membership["role"], {}) if membership else {}
        payload["permissions"] = list(RolePermission.objects.filter(business_role_id=membership["business_role_id"]).order_by("resource", "action").values("resource", "action", "scope", "is_allowed")) if membership else []
        payload["team"] = sorted(team_user_ids_for(user, business))
        payload["capabilities"] = {**default_capabilities(business.business_type),
                                   **dict(business.capabilities.values_list("module_key", "is_enabled"))}
    return hashlib.sha256(json.dumps(payload, sort_keys=True, ensure_ascii=False, default=str).encode()).hexdigest()


def references_visible(*, thread, user, references):
    from apps.ai_core.crm_tools import ENTITIES, scoped_entities
    with bind_agent(thread.agent_id):
        for reference in references:
            entity, entity_id = reference.get("entity"), reference.get("id")
            if entity not in ENTITIES or type(entity_id) is not int:
                return False
            try:
                if not scoped_entities(thread.business, user, entity, include_archived=True).filter(pk=entity_id).exists():
                    return False
            except PermissionDenied:
                return False
    return True
