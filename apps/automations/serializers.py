from rest_framework import serializers

from apps.automations.condition_fields import validate_condition_field
from apps.automations.models import AutomationAction, AutomationCondition, AutomationRule, AutomationRun
from apps.automations.action_validation import validate_action_config, validate_action_list, SUPPORTED_AUTOMATION_ACTION_TYPES
from apps.businesses.models import Business
from apps.integrations.sanitization import sanitize_config, sanitize_error_payload, sanitize_error_text


class AutomationListQuerySerializer(serializers.Serializer):
    business = serializers.IntegerField(required=False, min_value=1, max_value=9223372036854775807)


class AutomationHistoryQuerySerializer(AutomationListQuerySerializer):
    status = serializers.ChoiceField(required=False, allow_blank=True,
                                     choices=[*AutomationRun.Statuses.values, 'error', 'blocked'])
    trigger_type = serializers.ChoiceField(required=False, allow_blank=True,
                                           choices=AutomationRule.TriggerTypes.values)


class AutomationConditionSerializer(serializers.ModelSerializer):
    class Meta:
        model = AutomationCondition
        fields = ["id", "rule", "field", "operator", "value"]

    def validate(self, attrs):
        rule = attrs.get("rule") or getattr(self.instance, "rule", None)
        field = attrs.get("field", getattr(self.instance, "field", ""))
        if rule is not None:
            try:
                attrs["field"] = validate_condition_field(field, trigger_type=rule.trigger_type)
            except ValueError as exc:
                raise serializers.ValidationError({"field": str(exc)}) from exc
        return attrs


class AutomationActionSerializer(serializers.ModelSerializer):
    class Meta:
        model = AutomationAction
        fields = ["id", "rule", "action_type", "config", "order", "delay_seconds"]

    def validate(self, attrs):
        action_type = attrs.get("action_type") or getattr(self.instance, "action_type", None)
        delay_seconds = attrs.get("delay_seconds", getattr(self.instance, "delay_seconds", 0))
        rule = attrs.get("rule", getattr(self.instance, "rule", None))
        attrs["config"] = validate_action_config(
            action_type=action_type, config=attrs.get("config", getattr(self.instance, "config", {})),
            delay_seconds=delay_seconds, business=rule.business, trigger_type=rule.trigger_type,
            actor=getattr(self.context.get("request"), "user", None),
        )
        return attrs


class AutomationRuleSerializer(serializers.ModelSerializer):
    conditions = AutomationConditionSerializer(many=True, read_only=True)
    actions = AutomationActionSerializer(many=True, read_only=True)

    def validate(self, attrs):
        active = attrs.get("is_active", getattr(self.instance, "is_active", False))
        trigger_changed = self.instance is not None and attrs.get("trigger_type", self.instance.trigger_type) != self.instance.trigger_type
        if active or trigger_changed:
            business = attrs.get("business", getattr(self.instance, "business", None))
            trigger = attrs.get("trigger_type", getattr(self.instance, "trigger_type", None))
            actions = list(self.instance.actions.values("action_type", "config", "delay_seconds")) if self.instance else []
            if actions or active:
                validate_action_list(actions, business=business, trigger_type=trigger,
                                     actor=getattr(self.context.get("request"), "user", None))
            for condition in self.instance.conditions.all():
                try:
                    validate_condition_field(condition.field, trigger_type=trigger)
                except ValueError as exc:
                    raise serializers.ValidationError({"conditions": str(exc)}) from exc
        return attrs

    class Meta:
        model = AutomationRule
        fields = [
            "id",
            "business",
            "name",
            "trigger_type",
            "description",
            "is_active",
            "priority",
            "conditions",
            "actions",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["conditions", "actions", "created_at", "updated_at"]


class AutomationRunSerializer(serializers.ModelSerializer):
    rule_name = serializers.CharField(source="rule.name", read_only=True)
    protected_state_fields = {
        "status",
        "payload",
        "action_results",
        "error",
        "attempts",
        "max_attempts",
        "next_retry_at",
        "locked_at",
        "started_at",
        "finished_at",
    }

    class Meta:
        model = AutomationRun
        fields = [
            "id",
            "business",
            "rule",
            "rule_name",
            "trigger_type",
            "entity_type",
            "entity_id",
            "idempotency_key",
            "status",
            "payload",
            "action_results",
            "error",
            "attempts",
            "max_attempts",
            "run_after",
            "next_retry_at",
            "locked_at",
            "started_at",
            "finished_at",
            "created_at",
        ]
        read_only_fields = fields

    def validate(self, attrs):
        attempted_state_fields = sorted(self.protected_state_fields.intersection((self.initial_data or {}).keys()))
        if attempted_state_fields:
            raise serializers.ValidationError(
                {
                    "detail": "Use automation runtime services for run state changes.",
                    "fields": attempted_state_fields,
                }
            )
        return attrs

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data["payload"] = sanitize_config(data.get("payload") or {})
        data["action_results"] = sanitize_error_payload(sanitize_config(data.get("action_results") or []))
        data["error"] = sanitize_error_text(data.get("error"))
        return data


class AutomationTemplateSerializer(serializers.Serializer):
    key = serializers.CharField()
    name = serializers.CharField()
    description = serializers.CharField()
    trigger_type = serializers.CharField()
    actions = serializers.ListField(child=serializers.DictField())
    conditions = serializers.ListField(child=serializers.DictField(), required=False)


class ApplyAutomationTemplateSerializer(serializers.Serializer):
    business = serializers.IntegerField()
    template_key = serializers.CharField()
    is_active = serializers.BooleanField(default=False)


class AutomationConditionInputSerializer(serializers.Serializer):
    field = serializers.CharField(max_length=128)
    operator = serializers.ChoiceField(choices=AutomationCondition.Operators.choices, default=AutomationCondition.Operators.EQ)
    value = serializers.JSONField(default=dict)


class AutomationActionInputSerializer(serializers.Serializer):
    action_type = serializers.ChoiceField(choices=AutomationAction.ActionTypes.choices)
    config = serializers.JSONField(default=dict)
    delay_seconds = serializers.IntegerField(default=0, min_value=0)


class ManualAutomationRuleSerializer(serializers.Serializer):
    business = serializers.IntegerField()
    name = serializers.CharField(max_length=255)
    trigger_type = serializers.ChoiceField(choices=AutomationRule.TriggerTypes.choices)
    description = serializers.CharField(required=False, allow_blank=True)
    is_active = serializers.BooleanField(default=False)
    priority = serializers.IntegerField(default=100, min_value=0)
    conditions = AutomationConditionInputSerializer(many=True, required=False)
    actions = AutomationActionInputSerializer(many=True)

    def validate(self, attrs):
        trigger_type = attrs.get("trigger_type")
        condition_errors = {}
        for index, condition in enumerate(attrs.get("conditions", [])):
            try:
                condition["field"] = validate_condition_field(
                    condition.get("field"),
                    trigger_type=trigger_type,
                )
            except ValueError as exc:
                condition_errors[index] = {"field": str(exc)}
        if condition_errors:
            raise serializers.ValidationError({"conditions": condition_errors})
        business = Business.objects.filter(pk=attrs["business"]).first()
        if business is None:
            raise serializers.ValidationError({"business": "Business was not found."})
        attrs["actions"] = validate_action_list(
            attrs["actions"], business=business, trigger_type=trigger_type,
            actor=getattr(self.context.get("request"), "user", None),
        )
        return attrs
