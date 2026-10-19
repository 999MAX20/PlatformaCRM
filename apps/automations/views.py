from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

from apps.automations.engine import cancel_automation_run, retry_automation_run
from apps.automations.configuration import save_configuration
from apps.automations.configuration_views import AtomicConfigurationMixin
from apps.automations.models import AutomationAction, AutomationCondition, AutomationRule, AutomationRun
from apps.automations.permissions import IsAutomationRuleMember
from apps.billing.entitlements import EntitlementMetrics, assert_entitlement_allows
from apps.automations.serializers import (
    ApplyAutomationTemplateSerializer,
    AutomationActionSerializer,
    AutomationConditionSerializer,
    AutomationRuleSerializer,
    AutomationRunSerializer,
    AutomationTemplateSerializer,
    ManualAutomationRuleSerializer,
)
from apps.businesses.access import Actions, Resources, assert_can
from apps.businesses.models import Business
from apps.core.viewsets import TenantModelViewSet


AUTOMATION_TEMPLATES = [
    {
        "key": "new_lead_create_task",
        "name": "Новая заявка -> задача менеджеру",
        "description": "Когда появляется новая заявка, CRM создает follow-up задачу с высоким приоритетом.",
        "trigger_type": AutomationRule.TriggerTypes.LEAD_CREATED,
        "conditions": [],
        "actions": [
            {
                "action_type": AutomationAction.ActionTypes.CREATE_TASK,
                "config": {"title": "Связаться с новой заявкой", "priority": "high"},
                "delay_seconds": 0,
            }
        ],
    },
    {
        "key": "appointment_created_prepare",
        "name": "Новая запись -> подготовить визит",
        "description": "После создания записи добавляет задачу подготовить клиента, услугу или ресурс.",
        "trigger_type": AutomationRule.TriggerTypes.APPOINTMENT_CREATED,
        "conditions": [],
        "actions": [
            {
                "action_type": AutomationAction.ActionTypes.CREATE_TASK,
                "config": {"title": "Подготовить запись клиента", "priority": "normal"},
                "delay_seconds": 0,
            }
        ],
    },
    {
        "key": "message_received_handoff_task",
        "name": "Новое сообщение -> задача ответить",
        "description": "Когда клиент пишет в подключенный канал, CRM создает задачу для ручного ответа.",
        "trigger_type": AutomationRule.TriggerTypes.BOT_MESSAGE_RECEIVED,
        "conditions": [],
        "actions": [
            {
                "action_type": AutomationAction.ActionTypes.CREATE_TASK,
                "config": {"title": "Ответить клиенту в чате", "priority": "normal"},
                "delay_seconds": 0,
            }
        ],
    },
]


class AutomationRuleViewSet(AtomicConfigurationMixin, TenantModelViewSet):
    queryset = AutomationRule.objects.prefetch_related("conditions", "actions").select_related("business")
    serializer_class = AutomationRuleSerializer
    action_permission_map = {**TenantModelViewSet.action_permission_map, "configuration": Actions.UPDATE}

    def perform_create(self, serializer):
        business = serializer.validated_data["business"]
        assert_entitlement_allows(business, EntitlementMetrics.AUTOMATIONS)
        super().perform_create(serializer)

    @action(detail=False, methods=["get"])
    def templates(self, request):
        return Response(AutomationTemplateSerializer(AUTOMATION_TEMPLATES, many=True).data)

    @action(detail=False, methods=["post"], url_path="apply-template")
    def apply_template(self, request):
        serializer = ApplyAutomationTemplateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        business = Business.objects.filter(id=serializer.validated_data["business"]).first()
        if business is None:
            raise ValidationError({"business": "Business was not found."})
        assert_can(request.user, business, Resources.AUTOMATIONS, Actions.CREATE)
        assert_entitlement_allows(business, EntitlementMetrics.AUTOMATIONS)

        template = next((item for item in AUTOMATION_TEMPLATES if item["key"] == serializer.validated_data["template_key"]), None)
        if template is None:
            raise ValidationError({"template_key": "Unknown automation template."})

        payload = {key: value for key, value in template.items() if key != "key"}
        payload["is_active"] = serializer.validated_data["is_active"]
        rule = save_configuration(request=request, business=business, payload=payload)

        return Response(self.get_serializer(rule).data, status=201)

    @action(detail=False, methods=["post"], url_path="preview")
    def preview(self, request):
        serializer = ManualAutomationRuleSerializer(data=request.data, context=self.get_serializer_context())
        serializer.is_valid(raise_exception=True)
        business = self._business_for_manual_payload(serializer.validated_data)
        assert_can(request.user, business, Resources.AUTOMATIONS, Actions.CREATE)
        assert_entitlement_allows(business, EntitlementMetrics.AUTOMATIONS)
        return Response(self._manual_preview(serializer.validated_data))

    @action(detail=False, methods=["post"], url_path="create-manual")
    def create_manual(self, request):
        serializer = ManualAutomationRuleSerializer(data=request.data, context=self.get_serializer_context())
        serializer.is_valid(raise_exception=True)
        business = self._business_for_manual_payload(serializer.validated_data)
        assert_can(request.user, business, Resources.AUTOMATIONS, Actions.CREATE)
        assert_entitlement_allows(business, EntitlementMetrics.AUTOMATIONS)

        rule = save_configuration(request=request, business=business, payload=serializer.validated_data)

        return Response(self.get_serializer(rule).data, status=201)

    def _business_for_manual_payload(self, payload):
        business = Business.objects.filter(id=payload["business"]).first()
        if business is None:
            raise ValidationError({"business": "Business was not found."})
        return business

    @action(detail=True, methods=["put"])
    def configuration(self, request, pk=None):
        rule = self.get_object()
        serializer = ManualAutomationRuleSerializer(data=request.data, context=self.get_serializer_context())
        serializer.is_valid(raise_exception=True)
        if serializer.validated_data["business"] != rule.business_id:
            raise ValidationError({"business": "The owning business cannot be changed."})
        rule = save_configuration(request=request, business=rule.business,
                                  payload=serializer.validated_data, rule=rule)
        return Response(self.get_serializer(rule).data)

    def _manual_preview(self, payload):
        trigger_label = dict(AutomationRule.TriggerTypes.choices).get(payload["trigger_type"], payload["trigger_type"])
        return {
            "valid": True,
            "name": payload["name"],
            "trigger_type": payload["trigger_type"],
            "trigger_label": trigger_label,
            "conditions_count": len(payload.get("conditions", [])),
            "actions_count": len(payload["actions"]),
            "will_run_when": f"{trigger_label} event is emitted and all conditions match.",
            "steps": [
                {
                    "order": index,
                    "action_type": action["action_type"],
                    "delay_seconds": action.get("delay_seconds", 0),
                    "config": action.get("config", {}),
                }
                for index, action in enumerate(payload["actions"])
            ],
        }


class AutomationConditionViewSet(AtomicConfigurationMixin, TenantModelViewSet):
    permission_classes = [IsAutomationRuleMember]
    queryset = AutomationCondition.objects.select_related("rule", "rule__business")
    serializer_class = AutomationConditionSerializer
    business_lookup = "rule__business"


class AutomationActionViewSet(AtomicConfigurationMixin, TenantModelViewSet):
    permission_classes = [IsAutomationRuleMember]
    queryset = AutomationAction.objects.select_related("rule", "rule__business")
    serializer_class = AutomationActionSerializer
    business_lookup = "rule__business"


class AutomationRunViewSet(TenantModelViewSet):
    queryset = AutomationRun.objects.select_related("business", "rule")
    serializer_class = AutomationRunSerializer

    @action(detail=True, methods=["post"])
    def retry(self, request, pk=None):
        run = self.get_object()
        assert_can(request.user, run.business, Resources.AUTOMATIONS, Actions.MANAGE, obj=run)
        retry_automation_run(run)
        run.refresh_from_db()
        return Response(self.get_serializer(run).data)

    @action(detail=True, methods=["post"])
    def cancel(self, request, pk=None):
        run = self.get_object()
        assert_can(request.user, run.business, Resources.AUTOMATIONS, Actions.MANAGE, obj=run)
        cancel_automation_run(run)
        run.refresh_from_db()
        return Response(self.get_serializer(run).data)
