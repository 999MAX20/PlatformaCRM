"""Atomic configuration writes, separate from automation execution."""
from contextlib import contextmanager
from copy import deepcopy

from django.db import transaction
from rest_framework.exceptions import ValidationError

from apps.activities.services import write_activity_event
from apps.automations.action_validation import validate_action_list
from apps.automations.condition_fields import validate_condition_field
from apps.automations.models import AutomationAction, AutomationCondition, AutomationRule
from apps.billing.entitlements import EntitlementMetrics, assert_entitlement_allows
from apps.businesses.access import Actions, Resources, assert_can
from apps.businesses.capabilities import assert_resource_enabled
from apps.businesses.models import Business
from apps.core.audit import write_audit_log
from apps.core.models import AuditLog


@contextmanager
def configuration_write(business):
    # One lock for rule/child writes also serializes activation against deletion.
    with transaction.atomic():
        Business.objects.select_for_update().get(pk=business.pk)
        yield


def validate_configuration(*, business, trigger_type, actions, conditions, actor):
    validate_action_list(actions, business=business, trigger_type=trigger_type, actor=actor)
    for index, condition in enumerate(conditions):
        try:
            validate_condition_field(condition["field"], trigger_type=trigger_type)
        except ValueError as exc:
            raise ValidationError({"conditions": {index: {"field": str(exc)}}}) from exc


def validate_active_configuration(rule_id, actor):
    rule = AutomationRule.objects.filter(pk=rule_id, is_active=True).select_related("business").first()
    if rule is not None:
        validate_configuration(
            business=rule.business, trigger_type=rule.trigger_type, actor=actor,
            actions=list(rule.actions.values("action_type", "config", "delay_seconds")),
            conditions=list(rule.conditions.values("field")),
        )


def save_configuration(*, request, business, payload, rule=None):
    """Save a validated complete composition; history shares the same transaction."""
    payload = deepcopy(payload)
    with configuration_write(business):
        creating = rule is None
        if not creating:
            rule = AutomationRule.objects.get(pk=rule.pk, business=business)
        assert_resource_enabled(business, Resources.AUTOMATIONS)
        assert_can(request.user, business, Resources.AUTOMATIONS,
                   Actions.CREATE if creating else Actions.UPDATE, obj=rule)
        if creating:
            assert_entitlement_allows(business, EntitlementMetrics.AUTOMATIONS)
        validate_configuration(business=business, trigger_type=payload["trigger_type"],
                               actions=payload["actions"], conditions=payload.get("conditions", []),
                               actor=request.user)
        values = {"name": payload["name"], "trigger_type": payload["trigger_type"],
                  "description": payload.get("description", ""), "is_active": payload.get("is_active", False),
                  "priority": payload.get("priority", 100)}
        if creating:
            rule = AutomationRule.objects.create(business=business, **values)
        else:
            for field, value in values.items():
                setattr(rule, field, value)
            rule.save(update_fields=[*values, "updated_at"])
            rule.conditions.all().delete()
            rule.actions.all().delete()
        for condition in payload.get("conditions", []):
            AutomationCondition.objects.create(rule=rule, **condition)
        for order, action_data in enumerate(payload["actions"]):
            AutomationAction.objects.create(rule=rule, order=order, **action_data)
        write_audit_log(request, AuditLog.Actions.CREATE if creating else AuditLog.Actions.UPDATE, rule)
        write_activity_event(request, "automationrule.created" if creating else "automationrule.updated", rule)
        return rule
