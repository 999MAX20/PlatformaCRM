"""Saved internal AI scenarios, independent of messenger profiles and user rights."""
import hashlib
import json

from rest_framework.exceptions import PermissionDenied
from apps.ai_core.models import AgentProfile

SCENARIOS = {"employee", "analyst"}
SOURCES = {"clients", "leads", "deals", "tasks", "appointments", "knowledge"}


def workflow_profile(business, scenario):
    return AgentProfile.objects.filter(business=business, bot__isnull=True,
        rules_json__scenario=scenario).order_by("-updated_at", "-id").first()


def workflow_settings(business, scenario):
    profile = workflow_profile(business, scenario)
    if profile is None:
        return {"enabled": True, "sources": sorted(SOURCES), "tools": None}
    return {"id": profile.id, "enabled": profile.is_active, "language": profile.language,
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
