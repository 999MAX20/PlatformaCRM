"""Minimal agent navigation for staff without configuration privileges."""
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.ai_core.serializers import AIAssistantStatusSerializer
from apps.bots.lifecycle import get_bot_readiness
from apps.bots.models import Bot
from apps.businesses.access import Actions, Resources, can


class AIRuntimeAgentsView(APIView):
    def get(self, request):
        query = AIAssistantStatusSerializer(data=request.query_params)
        query.is_valid(raise_exception=True)
        business = query.validated_data["business"]
        if not any(can(request.user, business, resource, Actions.VIEW).allowed
                   for resource in (Resources.AI_ASSISTANT, Resources.AI_ANALYST)):
            raise PermissionDenied()
        agents = Bot.objects.filter(business=business, settings_json__scenario=Bot.Scenarios.CRM).prefetch_related("agent_profiles")
        return Response([{"id": agent.pk, "business": business.pk, "name": agent.name,
                          "scenario": agent.scenario, "status": agent.status,
                          "readiness": get_bot_readiness(agent)} for agent in agents])
