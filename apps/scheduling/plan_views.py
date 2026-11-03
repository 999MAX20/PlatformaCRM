from django.shortcuts import get_object_or_404
from rest_framework import serializers, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.businesses.models import Business
from apps.core.permissions import user_can_access_business
from apps.scheduling.plan_selectors import readable_plans
from apps.scheduling.plan_serializers import PlanCreateInput, PlanCommandInput, plan_projection
from apps.scheduling.plan_services import create_plan, change_plan
from apps.scheduling.record_workspace import RecordWorkspacePagination


class PlanListInput(serializers.Serializer):
    business = serializers.IntegerField(min_value=1)
    client = serializers.IntegerField(min_value=1, required=False)
    branch = serializers.IntegerField(min_value=1, required=False)
    archived = serializers.BooleanField(default=False)
    page = serializers.IntegerField(min_value=1, required=False)
    page_size = serializers.IntegerField(min_value=1, max_value=100, required=False)


class VisitPlanViewSet(viewsets.GenericViewSet):
    permission_classes = [IsAuthenticated]
    pagination_class = RecordWorkspacePagination

    def business(self, pk):
        business = get_object_or_404(Business, pk=pk)
        if not user_can_access_business(self.request.user, business):
            raise PermissionDenied("Business is not available.")
        return business

    def get_queryset(self):
        query = PlanListInput(data=self.request.query_params)
        query.is_valid(raise_exception=True)
        values = query.validated_data
        business = self.business(values["business"])
        plans = readable_plans(business=business, actor=self.request.user)
        if self.action == "list":
            plans = plans.filter(is_archived=values["archived"])
            if values.get("client"):
                plans = plans.filter(client_id=values["client"])
            if values.get("branch"):
                from django.db.models import Q
                from apps.scheduling.plan_selectors import readable_plan_steps
                steps = readable_plan_steps(business=business, actor=self.request.user).filter(
                    Q(appointment__branch_id=values["branch"]) |
                    Q(appointment__isnull=True, branch_id=values["branch"]))
                plans = plans.filter(pk__in=steps.values("plan_id"))
        return plans

    def list(self, request):
        page = self.paginate_queryset(self.get_queryset())
        return self.get_paginated_response([plan_projection(plan, request.user) for plan in page])

    def retrieve(self, request, pk=None):
        return Response(plan_projection(self.get_object(), request.user))

    @action(detail=True, methods=["get"])
    def history(self, request, pk=None):
        from apps.activities.models import ActivityEvent
        plan = self.get_object()
        events = ActivityEvent.objects.filter(business=plan.business, entity_type="VisitPlan", entity_id=str(plan.pk)).select_related("actor").order_by("-created_at", "-pk")
        page = self.paginate_queryset(events)
        return self.get_paginated_response([{"id": event.pk, "created_at": event.created_at,
            "command": event.metadata.get("command", ""), "actor_name": event.actor.full_name if event.actor else ""}
            for event in page])

    def create(self, request):
        serializer = PlanCreateInput(data=request.data)
        serializer.is_valid(raise_exception=True)
        values = dict(serializer.validated_data)
        values["business"] = self.business(values["business"])
        plan, replayed = create_plan(actor=request.user, idempotency_key=request.headers.get("Idempotency-Key"), **values)
        return self.result(plan, replayed, created=True)

    def result(self, plan, replayed, *, created=False):
        current = readable_plans(business=plan.business, actor=self.request.user).filter(pk=plan.pk).first()
        data = plan_projection(current, self.request.user) if current else {"read_restricted": True}
        return Response(data, status=201 if created and not replayed else 200)

    @action(detail=True, methods=["post"], url_path="commands/(?P<command>schedule|revise|archive|restore|responsible)")
    def command(self, request, pk=None, command=None):
        plan = self.get_object()
        serializer = PlanCommandInput(data=request.data)
        serializer.is_valid(raise_exception=True)
        values = dict(serializer.validated_data)
        revision = values.pop("expected_revision")
        if command == "schedule" and not {"step_id", "start_at", "expected_price", "expected_duration_minutes"}.issubset(values):
            raise serializers.ValidationError("Step, time and current booking terms are required.")
        plan, replayed = change_plan(plan=plan, actor=request.user, command=command,
            expected_revision=revision, idempotency_key=request.headers.get("Idempotency-Key"), data=values)
        return self.result(plan, replayed)
