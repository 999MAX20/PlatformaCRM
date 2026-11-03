from rest_framework import serializers
from rest_framework.exceptions import PermissionDenied

from apps.accounts.models import User
from apps.branches.models import Branch
from apps.clients.models import Client
from apps.scheduling.models import Resource
from apps.scheduling.plan_access import assert_plan_change, visible_steps
from apps.services.models import Service


class PlanStepInput(serializers.Serializer):
    id = serializers.IntegerField(min_value=1, required=False)
    service = serializers.PrimaryKeyRelatedField(queryset=Service.objects.all(), required=False)
    resource = serializers.PrimaryKeyRelatedField(queryset=Resource.objects.all(), allow_null=True, required=False)
    branch = serializers.PrimaryKeyRelatedField(queryset=Branch.objects.all(), allow_null=True, required=False)
    responsible_user = serializers.PrimaryKeyRelatedField(queryset=User.objects.all(), allow_null=True, required=False)


class PlanCreateInput(serializers.Serializer):
    business = serializers.IntegerField(min_value=1)
    client = serializers.PrimaryKeyRelatedField(queryset=Client.objects.all())
    responsible_user = serializers.PrimaryKeyRelatedField(queryset=User.objects.all(), required=False)
    steps = PlanStepInput(many=True, max_length=100)


class PlanCommandInput(serializers.Serializer):
    expected_revision = serializers.IntegerField(min_value=1)
    responsible_user = serializers.PrimaryKeyRelatedField(queryset=User.objects.all(), required=False)
    step_ids = serializers.ListField(child=serializers.IntegerField(min_value=1), required=False, max_length=100)
    step_id = serializers.IntegerField(min_value=1, required=False)
    start_at = serializers.DateTimeField(required=False)
    resource = serializers.PrimaryKeyRelatedField(queryset=Resource.objects.all(), required=False)
    branch = serializers.PrimaryKeyRelatedField(queryset=Branch.objects.all(), required=False, allow_null=True)
    expected_price = serializers.DecimalField(max_digits=10, decimal_places=2, required=False, allow_null=True)
    expected_duration_minutes = serializers.IntegerField(min_value=1, required=False)
    add = PlanStepInput(many=True, required=False, max_length=100)
    changes = PlanStepInput(many=True, required=False, max_length=100)
    remove = serializers.ListField(child=serializers.IntegerField(min_value=1), required=False, max_length=100)
    consent = serializers.BooleanField(required=False)
    reason = serializers.CharField(max_length=500, required=False)
    notes = serializers.CharField(max_length=2000, required=False, allow_blank=True)


def plan_projection(plan, actor):
    steps = visible_steps(plan, actor)
    try:
        assert_plan_change(plan, actor)
        can_change = True
    except PermissionDenied:
        can_change = False
    return {"id": plan.pk, "business": plan.business_id, "client": plan.client_id,
            "client_name": plan.client.full_name, "revision": plan.revision,
            "responsible_user": plan.responsible_user_id,
            "responsible_user_name": plan.responsible_user.full_name,
            "is_archived": plan.is_archived, "can_change": can_change,
            "created_at": plan.created_at, "steps": [step_projection(step) for step in steps]}


def step_projection(step):
    appointment = step.appointment
    return {"id": step.pk, "service": appointment.service_id if appointment else step.service_id,
            "service_name": appointment.service.name if appointment else step.service.name,
            "resource": appointment.resource_id if appointment else step.resource_id,
            "resource_name": (appointment.resource.name if appointment.resource_id else "") if appointment else (step.resource.name if step.resource_id else ""),
            "branch": appointment.branch_id if appointment else step.branch_id,
            "responsible_user": step.responsible_user_id,
            "appointment": step.appointment_id, "start_at": appointment.start_at if appointment else None,
            "status": appointment.status if appointment else "unscheduled",
            "removed_at": step.removed_at}
