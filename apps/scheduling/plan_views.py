from django.shortcuts import get_object_or_404
from rest_framework import serializers, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.businesses.models import Business
from apps.core.permissions import user_can_access_business
from apps.scheduling.plan_selectors import readable_plans
from apps.scheduling.plan_serializers import PlanCreateInput, PlanCommandInput, PlanMoneyInput, plan_projection
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

    @action(detail=True, methods=["post"], url_path="preview-terms")
    def preview_terms(self, request, pk=None):
        from apps.payments.plan_pricing import preview_terms
        from apps.core.domain_errors import InvalidTransition
        plan = self.get_object()
        serializer = PlanMoneyInput(data=request.data)
        serializer.is_valid(raise_exception=True)
        if plan.revision != serializer.validated_data["expected_revision"]:
            raise InvalidTransition("The plan changed. Refresh before reviewing terms.")
        return Response(preview_terms(plan, request.user, serializer.validated_data))

    @action(detail=True, methods=["get"], url_path="credit-options")
    def credit_options(self, request, pk=None):
        from apps.businesses.access import Actions
        from apps.payments.plan_balances import assert_plan_money, plan_sources, retained_balance
        from apps.scheduling.plan_access import assert_plan_change
        plan = self.get_object()
        assert_plan_money(plan, request.user, Actions.CREATE)
        options = []
        for source in readable_plans(business=plan.business, actor=request.user).filter(client=plan.client).exclude(pk=plan.pk):
            try:
                assert_plan_money(source, request.user, Actions.MANAGE)
                assert_plan_change(source, request.user)
            except PermissionDenied:
                continue
            for receipt in plan_sources(source):
                retained = retained_balance(source, receipt)
                if retained > 0:
                    options.append({"source_plan": source.pk, "source_revision": source.revision,
                        "receipt": receipt.pk, "amount": str(retained), "currency": receipt.currency})
        return self.get_paginated_response(self.paginate_queryset(options))

    @action(detail=True, methods=["get"], url_path="terms-history")
    def terms_history(self, request, pk=None):
        from apps.payments.plan_balances import assert_plan_money
        plan = self.get_object()
        assert_plan_money(plan, request.user)
        page = self.paginate_queryset(plan.payment_terms.select_related("actor").order_by("-revision"))
        return self.get_paginated_response([{"id": row.pk, "revision": row.revision,
            "mode": row.mode, "currency": row.currency, "total": str(row.total), "lines": row.lines,
            "reason": row.reason, "created_at": row.created_at,
            "actor_name": row.actor.full_name if row.actor else ""} for row in page])

    @action(detail=True, methods=["get"], url_path="legacy-payment-options")
    def legacy_payment_options(self, request, pk=None):
        from django.db.models import F
        from apps.payments.plan_corrections import legacy_options
        page = self.paginate_queryset(legacy_options(self.get_object(), request.user).filter(amount__gt=F("refunded_amount")))
        return self.get_paginated_response([{"id": row.pk, "amount": str(row.amount),
            "refunded": str(row.refunded_amount), "available": str(row.amount - row.refunded_amount),
            "occurred_at": row.occurred_at, "method": row.method, "currency": row.currency} for row in page])

    @action(detail=True, methods=["post"], url_path="preview-correction/(?P<correction>annul-completion|attach-legacy)")
    def preview_correction(self, request, pk=None, correction=None):
        from apps.payments.plan_corrections import preview_correction
        from apps.core.domain_errors import InvalidTransition
        plan = self.get_object()
        serializer = PlanMoneyInput(data=request.data)
        serializer.is_valid(raise_exception=True)
        if plan.revision != serializer.validated_data["expected_revision"]:
            raise InvalidTransition("The plan changed. Refresh before reviewing the correction.")
        return Response(preview_correction(plan, request.user, correction, serializer.validated_data))

    @action(detail=True, methods=["post"], url_path="commands/(?P<command>schedule|revise|archive|restore|responsible|accept-terms|settle-remainder|use-credit|annul-completion|attach-legacy|create-replacement)")
    def command(self, request, pk=None, command=None):
        plan = self.get_object()
        input_type = PlanMoneyInput if command in {"accept-terms", "settle-remainder", "use-credit", "annul-completion", "attach-legacy", "create-replacement"} else PlanCommandInput
        serializer = input_type(data=request.data)
        serializer.is_valid(raise_exception=True)
        values = dict(serializer.validated_data)
        revision = values.pop("expected_revision")
        if command == "schedule" and not {"step_id", "start_at", "expected_price", "expected_duration_minutes"}.issubset(values):
            raise serializers.ValidationError("Step, time and current booking terms are required.")
        plan, replayed = change_plan(plan=plan, actor=request.user, command=command,
            expected_revision=revision, idempotency_key=request.headers.get("Idempotency-Key"), data=values)
        return self.result(plan, replayed)
