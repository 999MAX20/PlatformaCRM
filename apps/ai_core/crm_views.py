"""Thin API boundaries for the employee's CRM reads and historical analyst."""
from datetime import timedelta

from rest_framework import serializers
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.ai_core.assistant import assert_business_access
from apps.ai_core.crm_tools import ENTITIES, read_entities
from apps.ai_core.history import build_history_report
from apps.businesses.access import Actions, Resources, assert_can
from apps.businesses.models import Business


class CRMReadSerializer(serializers.Serializer):
    business = serializers.PrimaryKeyRelatedField(queryset=Business.objects.all())
    entity = serializers.ChoiceField(choices=list(ENTITIES))
    query = serializers.CharField(required=False, default="", allow_blank=True, max_length=200)
    entity_id = serializers.IntegerField(required=False, min_value=1)
    offset = serializers.IntegerField(required=False, default=0, min_value=0, max_value=1000000)
    limit = serializers.IntegerField(required=False, default=20, min_value=1, max_value=50)
    include_archived = serializers.BooleanField(required=False, default=False)


class CRMReadView(APIView):
    def get(self, request):
        serializer = CRMReadSerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        values = serializer.validated_data
        business = values["business"]
        assert_can(request.user, business, Resources.AI_ASSISTANT, Actions.VIEW)
        return Response(read_entities(user=request.user, **values))


class CRMPlanSerializer(serializers.Serializer):
    business = serializers.PrimaryKeyRelatedField(queryset=Business.objects.all())
    entity = serializers.ChoiceField(choices=list(ENTITIES))
    entity_id = serializers.IntegerField(required=False, min_value=1)
    message = serializers.CharField(max_length=4000)


class CRMPlanView(APIView):
    def post(self, request):
        serializer = CRMPlanSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        values = serializer.validated_data
        assert_can(request.user, values["business"], Resources.AI_PIPELINE, Actions.SUGGEST)
        from apps.ai_core.crm_planner import plan_command
        return Response(plan_command(user=request.user, **values))


class HistorySerializer(serializers.Serializer):
    business = serializers.PrimaryKeyRelatedField(queryset=Business.objects.all())
    start = serializers.DateField()
    end = serializers.DateField()

    def validate(self, attrs):
        if attrs["start"] > attrs["end"] or (attrs["end"] - attrs["start"]).days > 3660:
            raise serializers.ValidationError("Select an ordered period of at most ten years.")
        if attrs["start"].year < 1901 or attrs["end"].year > 9998:
            raise serializers.ValidationError("Select a period beginning after 1900.")
        return attrs


class AIHistoryView(APIView):
    def get(self, request):
        serializer = HistorySerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        values = serializer.validated_data
        assert_can(request.user, values["business"], Resources.AI_ANALYST, Actions.VIEW)
        return Response(build_history_report(user=request.user, **values))

    def post(self, request):
        serializer = HistoryQuestionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        from apps.ai_core.history import explain_history
        return Response(explain_history(user=request.user, **serializer.validated_data))


class HistoryQuestionSerializer(HistorySerializer):
    question = serializers.CharField(max_length=4000)
