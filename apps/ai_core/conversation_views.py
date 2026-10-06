"""Owner-scoped employee conversations; source-aware history and exact actions."""
from django.utils import timezone
from rest_framework import serializers
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from apps.ai_core.conversation_access import create_staff_conversation, memory_access_fingerprint, references_visible, staff_conversation, staff_conversations
from apps.ai_core.conversation_actions import confirm_turn
from apps.ai_core.conversation_state import OPEN, cancel_turn, dispatch_conversation_job, locked_conversation, recover_interrupted, reset_memory, retry_turn, start_turn, stop_turn
from apps.ai_core.serializers import AIToolCallLogSerializer
from apps.ai_core.tool_registry import tool_call_fingerprint
from apps.businesses.models import Business


class ConversationScopeSerializer(serializers.Serializer):
    business = serializers.PrimaryKeyRelatedField(queryset=Business.objects.all())
    agent = serializers.IntegerField(min_value=1)
    archived = serializers.BooleanField(default=False)
    mode = serializers.ChoiceField(choices=["work", "analytics"], default="work")


class PeriodSerializer(serializers.Serializer):
    start = serializers.DateField()
    end = serializers.DateField()

    def validate(self, values):
        if values["start"] > values["end"] or (values["end"] - values["start"]).days > 3660:
            raise serializers.ValidationError("Select an ordered period of at most ten years.")
        return values


class TurnSerializer(serializers.Serializer):
    message = serializers.CharField(max_length=4000, allow_blank=False)
    idempotency_key = serializers.CharField(max_length=128)
    mode = serializers.ChoiceField(choices=["work", "analytics"], default="work")
    period = PeriodSerializer(required=False)


class HistoryPageSerializer(serializers.Serializer):
    before = serializers.IntegerField(min_value=1, required=False)
    limit = serializers.IntegerField(min_value=1, max_value=50, default=30)


class ConversationPageSerializer(serializers.Serializer):
    offset = serializers.IntegerField(min_value=0, default=0)


class ConfirmedActionSerializer(serializers.Serializer):
    id = serializers.IntegerField(min_value=1)
    fingerprint = serializers.RegexField(r"^[0-9a-f]{64}$")


class ConfirmTurnSerializer(serializers.Serializer):
    actions = ConfirmedActionSerializer(many=True, allow_empty=False, max_length=6)
    expected_revision = serializers.IntegerField(min_value=1)


class RetryTurnSerializer(serializers.Serializer):
    idempotency_key = serializers.CharField(max_length=128)


def turn_payload(turn, user, *, fingerprint=None):
    thread = turn.conversation
    fingerprint = fingerprint or memory_access_fingerprint(business=thread.business, agent=thread.agent, user=user)
    visible = turn.access_fingerprint == fingerprint and references_visible(thread=thread, user=user, references=turn.references_json)
    current_ids = {step.get("tool_call_id") for step in turn.plan_json.get("steps", [])}
    actions = []
    if visible:
        for log in turn.tool_calls.all().order_by("pk"):
            if log.pk in current_ids or log.status == "executed":
                actions.append({**AIToolCallLogSerializer(log).data, "fingerprint": tool_call_fingerprint(log)})
    return {"id": turn.pk, "sequence": turn.sequence, "status": turn.status, "mode": turn.mode,
            "message": turn.message if visible else "", "response": turn.response if visible else "",
            "redacted": not visible, "sources": turn.sources_json if visible else [], "actions": actions,
            "error_code": turn.error_code, "provider_state": turn.context_json.get("provider_state", ""),
            "completed_steps": sum(bool(step.get("completed")) for step in turn.plan_json.get("steps", [])) if visible else 0,
            "total_steps": len(turn.plan_json.get("steps", [])) if visible else 0,
            "created_at": turn.created_at, "updated_at": turn.updated_at}


def thread_payload(thread, user, *, fingerprint=None):
    last = thread.turns.order_by("-sequence").first()
    title_turn = thread.turns.order_by("sequence").first()
    fingerprint = fingerprint or memory_access_fingerprint(business=thread.business, agent=thread.agent, user=user)
    visible = title_turn is None or (title_turn.access_fingerprint == fingerprint and references_visible(thread=thread, user=user, references=title_turn.references_json))
    return {"id": str(thread.pk), "business": thread.business_id, "agent": thread.agent_id,
            "title": thread.title if visible else "", "is_archived": thread.is_archived,
            "revision": thread.revision, "memory_enabled": thread.agent.settings_json.get("memory_enabled", True),
            "memory_epoch": thread.memory_epoch, "status": last.status if last else "empty", "updated_at": thread.updated_at}


class AgentConversationListView(APIView):
    def get(self, request):
        serializer = ConversationScopeSerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        values = serializer.validated_data
        page = ConversationPageSerializer(data=request.query_params)
        page.is_valid(raise_exception=True)
        offset = page.validated_data["offset"]
        queryset = staff_conversations(business=values["business"], agent_id=values["agent"], user=request.user).filter(
            is_archived=values["archived"]).select_related("business", "agent").order_by("-updated_at", "-pk")
        threads = list(queryset[offset:offset + 51])
        has_more = len(threads) > 50
        threads = threads[:50]
        fingerprint = memory_access_fingerprint(business=values["business"], agent=threads[0].agent, user=request.user) if threads else None
        return Response({"results": [thread_payload(thread, request.user, fingerprint=fingerprint) for thread in threads],
                         "next_offset": offset + 50 if has_more else None})

    def post(self, request):
        serializer = ConversationScopeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        values = serializer.validated_data
        thread = create_staff_conversation(business=values["business"], agent_id=values["agent"], user=request.user, mode=values["mode"])
        return Response(thread_payload(thread, request.user), status=201)


class AgentConversationDetailView(APIView):
    def get(self, request, conversation_id):
        thread = staff_conversation(conversation_id=conversation_id, user=request.user)
        recover_interrupted(thread)
        serializer = HistoryPageSerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        values = serializer.validated_data
        query = thread.turns.all()
        if values.get("before"):
            query = query.filter(sequence__lt=values["before"])
        rows = list(query.order_by("-sequence")[:values["limit"]])
        fingerprint = memory_access_fingerprint(business=thread.business, agent=thread.agent, user=request.user)
        return Response({"conversation": thread_payload(thread, request.user, fingerprint=fingerprint),
            "turns": [turn_payload(turn, request.user, fingerprint=fingerprint) for turn in reversed(rows)],
            "has_more": bool(rows and query.filter(sequence__lt=rows[-1].sequence).exists()),
            "next_before": rows[-1].sequence if rows else None})

    def patch(self, request, conversation_id):
        value = serializers.BooleanField().run_validation(request.data.get("is_archived"))
        with locked_conversation(conversation_id, request.user, write=False) as thread:
            if value:
                for turn in thread.turns.filter(status__in=OPEN):
                    stop_turn(turn, request.user)
            thread.is_archived = value
            thread.save(update_fields=["is_archived", "updated_at"])
        return Response(thread_payload(thread, request.user))


class AgentConversationTurnsView(APIView):
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "ai_assistant"

    def post(self, request, conversation_id):
        serializer = TurnSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        values = dict(serializer.validated_data)
        period = values.pop("period", None)
        context = {"period": {key: value.isoformat() for key, value in period.items()}} if period else {}
        turn, job = start_turn(conversation_id=conversation_id, user=request.user, context=context, **values)
        if job is not None:
            dispatch_conversation_job(job)
        turn.refresh_from_db()
        return Response(turn_payload(turn, request.user), status=202 if turn.status == "preparing" else 200)


class AgentConversationResetView(APIView):
    def post(self, request, conversation_id):
        return Response(thread_payload(reset_memory(conversation_id=conversation_id, user=request.user), request.user))


class AgentTurnCancelView(APIView):
    def post(self, request, conversation_id, turn_id):
        turn = cancel_turn(conversation_id=conversation_id, turn_id=turn_id, user=request.user)
        return Response(turn_payload(turn, request.user))


class AgentTurnRetryView(APIView):
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "ai_assistant"

    def post(self, request, conversation_id, turn_id):
        serializer = RetryTurnSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        turn, job = retry_turn(conversation_id=conversation_id, turn_id=turn_id, user=request.user, **serializer.validated_data)
        if job is not None:
            dispatch_conversation_job(job)
        turn.refresh_from_db()
        return Response(turn_payload(turn, request.user), status=202 if turn.status == "preparing" else 200)


class AgentTurnConfirmView(APIView):
    def post(self, request, conversation_id, turn_id):
        serializer = ConfirmTurnSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        turn, job = confirm_turn(conversation_id=conversation_id, turn_id=turn_id, user=request.user, **serializer.validated_data)
        if job is not None:
            dispatch_conversation_job(job)
        turn.refresh_from_db()
        return Response(turn_payload(turn, request.user), status=202 if turn.status == "preparing" else 200)
