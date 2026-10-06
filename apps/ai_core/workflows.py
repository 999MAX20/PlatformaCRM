"""Saved internal AI scenarios, independent of messenger profiles and user rights."""
import hashlib
import json

from rest_framework.exceptions import PermissionDenied
from apps.ai_core.models import AgentProfile

SCENARIOS = {"employee", "analyst"}
SOURCES = {"clients", "leads", "deals", "tasks", "appointments", "knowledge"}


def _workflow_profile(business, scenario, agent):
    if agent is not None:
        return AgentProfile.objects.filter(business=business, bot=agent).order_by("-is_active", "-updated_at", "-id").first()
    return None


def workflow_settings(business, scenario):
    from apps.ai_core.agent_runtime import resolve_agent
    agent = resolve_agent(business)
    profile = _workflow_profile(business, scenario, agent)
    if profile is None:
        return {"enabled": agent is None, "sources": sorted(SOURCES) if agent is None else [], "tools": None if agent is None else []}
    enabled = profile.is_active
    runtime = {}
    if agent is not None:
        enabled = enabled and agent.status == "active" and (scenario != "analyst" or profile.rules_json.get("analyst_enabled", True))
        runtime = {"agent_id": agent.pk, "agent_updated": agent.updated_at.isoformat(),
            "profile_updated": profile.updated_at.isoformat(), "role": profile.role_description,
            "rules": profile.rules_json, "model": agent.settings_json.get("model"),
            "model_tier": agent.settings_json.get("model_tier"), "temperature": agent.settings_json.get("temperature")}
    return {**runtime, "id": profile.id, "enabled": enabled, "language": profile.language,
        "tone": profile.tone, "instructions": profile.system_prompt,
        "sources": profile.rules_json.get("sources", sorted(SOURCES)),
        "tools": profile.allowed_tools_json.get("tools", [])}


def assert_workflow_enabled(business, scenario):
    config = workflow_settings(business, scenario)
    if not config["enabled"]:
        raise PermissionDenied("This AI scenario is disabled by the business.")
    return config


def workflow_fingerprint(business, scenario):
    return hashlib.sha256(json.dumps(workflow_settings(business, scenario), sort_keys=True).encode()).hexdigest()


def assert_employee_tool(business, tool_name):
    config = assert_workflow_enabled(business, "employee")
    if config["tools"] is not None and tool_name not in config["tools"]:
        raise PermissionDenied("This employee assistant capability is disabled.")
