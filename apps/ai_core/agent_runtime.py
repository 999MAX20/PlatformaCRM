"""Request-local agent identity; permissions remain enforced by domain services."""
from contextlib import contextmanager
from contextvars import ContextVar
from functools import wraps

from rest_framework import serializers
from rest_framework.exceptions import PermissionDenied

from apps.bots.models import Bot


_agent_id = ContextVar("crm_agent_id", default=None)
_conversation_id = ContextVar("private_agent_conversation_id", default=None)


@contextmanager
def bind_conversation(conversation_id):
    token = _conversation_id.set(str(conversation_id))
    try:
        yield
    finally:
        _conversation_id.reset(token)


def conversation_binding():
    value = _conversation_id.get()
    return {"_conversation": value} if value else {}


@contextmanager
def bind_agent(agent_id):
    token = _agent_id.set(agent_id)
    try:
        yield
    finally:
        _agent_id.reset(token)


def agent_request(method):
    """Bind only identity; each workflow lookup scopes it to the authorized business."""
    @wraps(method)
    def wrapped(self, request, *args, **kwargs):
        data = request.query_params if request.method == "GET" else request.data
        agent_id = None
        if "agent" in data:
            agent_id = serializers.IntegerField(min_value=1).run_validation(data["agent"])
        with bind_agent(agent_id):
            return method(self, request, *args, **kwargs)
    return wrapped


def resolve_agent(business):
    agents = Bot.objects.filter(business=business, settings_json__scenario=Bot.Scenarios.CRM)
    selected = _agent_id.get()
    if selected is not None:
        agent = agents.filter(pk=selected).first()
        if agent is None:
            raise PermissionDenied("CRM agent is unavailable for this business.")
        return agent
    # Compatibility for existing business-level callers, including owner briefs.
    # Once configured, they also respect this business's CRM agent and its pause.
    agent = agents.order_by("pk").first()
    if agent is None and Bot.all_objects.filter(business=business, settings_json__scenario=Bot.Scenarios.CRM,
                                                settings_json__has_key="_deleted_at").exists():
        raise PermissionDenied("This CRM agent has been deleted.")
    return agent


def agent_binding(business):
    from apps.ai_core.workflows import workflow_fingerprint
    agent = resolve_agent(business)
    if agent is None:
        return {}
    return {"agent_id": agent.pk, "agent_fingerprint": workflow_fingerprint(business, "employee")}


def bind_command(business, payload):
    binding = agent_binding(business)
    return {**payload, **({"_agent": binding} if binding else {})}


@contextmanager
def command_agent(log):
    from apps.ai_core.workflows import workflow_fingerprint
    binding = (log.input_json or {}).get("_agent", {})
    with bind_agent(binding.get("agent_id")):
        if binding and binding.get("agent_fingerprint") != workflow_fingerprint(log.business, "employee"):
            raise PermissionDenied("Agent settings changed. Prepare and confirm a new command.")
        yield


def agent_command(method):
    @wraps(method)
    def wrapped(log, *args, **kwargs):
        with command_agent(log):
            return method(log, *args, **kwargs)
    return wrapped
