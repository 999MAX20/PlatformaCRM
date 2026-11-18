from django.conf import settings
from rest_framework.exceptions import PermissionDenied

from apps.ai_core.crm_tools import target_for_command
from apps.ai_core.agent_runtime import VOICE_RUNTIME, bind_agent
from apps.ai_core.providers.elevenlabs_speech import bounded_name_terms, is_configured


def speech_name_terms(business, user, reference):
    """Only the opted-in card's visible client identity, never a tenant directory."""
    if not reference or settings.VOICE_TRANSCRIPTION_PROVIDER != "elevenlabs" or not is_configured():
        return []
    entity, pk = reference.get("entity"), reference.get("id")
    if entity not in {"clients", "tasks", "appointments"} or type(pk) is not int:
        raise PermissionDenied("voice_context_unavailable")
    with bind_agent(VOICE_RUNTIME):
        target = target_for_command(business, user, entity, pk)
        if target.is_archived:
            return []
        if entity != "clients":
            if not target.client_id:
                return []
            target = target_for_command(business, user, "clients", target.client_id)
    if target.is_archived:
        return []
    return bounded_name_terms([target.full_name, *target.full_name.split()])
