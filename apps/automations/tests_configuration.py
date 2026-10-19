from unittest.mock import patch

from django.test import TestCase
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.activities.models import ActivityEvent
from apps.automations.models import AutomationAction, AutomationCondition, AutomationRule
from apps.core.models import AuditLog
from apps.businesses.models import Business, BusinessMember, BusinessRole, RolePermission


class AutomationConfigurationTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.owner = User.objects.create_user(username="config-owner", email="config-owner@example.test", role="business_owner")
        cls.business = Business.objects.create(owner=cls.owner, name="Configuration", slug="configuration")

    def setUp(self):
        self.api = APIClient()
        self.api.force_authenticate(self.owner)

    def payload(self):
        return {"business": self.business.pk, "name": "Atomic rule", "trigger_type": "lead_created", "is_active": True,
                "conditions": [{"field": "status", "operator": "eq", "value": {"value": "new"}}],
                "actions": [{"action_type": "create_task", "config": {"title": "First"}},
                            {"action_type": "create_task", "config": {"title": "Second"}}]}

    def counts(self):
        return tuple(model.objects.count() for model in (AutomationRule, AutomationCondition, AutomationAction, AuditLog, ActivityEvent))

    def test_manual_second_action_failure_rolls_back_everything(self):
        before = self.counts()
        create = AutomationAction.objects.create
        calls = 0

        def fail_second(**kwargs):
            nonlocal calls
            calls += 1
            if calls == 2:
                raise RuntimeError("injected action write failure")
            return create(**kwargs)

        with patch.object(AutomationAction.objects, "create", side_effect=fail_second):
            response = self.api.post("/api/automation-rules/create-manual/", self.payload(), format="json")
            self.assertEqual(response.status_code, 500)
        self.assertEqual(self.counts(), before)

    def test_template_action_failure_rolls_back_rule(self):
        before = self.counts()
        with patch.object(AutomationAction.objects, "create", side_effect=RuntimeError("injected action failure")):
            response = self.api.post("/api/automation-rules/apply-template/", {
                "business": self.business.pk, "template_key": "new_lead_create_task", "is_active": True,
            }, format="json")
            self.assertEqual(response.status_code, 500)
        self.assertEqual(self.counts(), before)

    def test_active_rule_cannot_lose_its_last_action(self):
        rule = AutomationRule.objects.create(business=self.business, name="Active", trigger_type="lead_created", is_active=True)
        action = AutomationAction.objects.create(rule=rule, action_type="create_task", config={})
        before = self.counts()
        response = self.api.delete(f"/api/automation-actions/{action.pk}/")
        self.assertEqual(response.status_code, 400, response.data)
        self.assertEqual(self.counts(), before)

    def saved_rule(self):
        response = self.api.post("/api/automation-rules/create-manual/", self.payload(), format="json")
        self.assertEqual(response.status_code, 201, response.data)
        return AutomationRule.objects.get(pk=response.data["id"])

    def snapshot(self, rule):
        rule.refresh_from_db()
        return (rule.name, rule.trigger_type, rule.is_active, rule.priority,
                list(rule.conditions.values()), list(rule.actions.values()), self.counts())

    def test_full_replace_and_create_have_atomic_history_and_order(self):
        rule = self.saved_rule()
        self.assertEqual(list(rule.actions.values_list("order", flat=True)), [0, 1])
        self.assertEqual(AuditLog.objects.filter(entity_type="AutomationRule", entity_id=str(rule.pk), action="create").count(), 1)
        self.assertEqual(ActivityEvent.objects.filter(entity_type="AutomationRule", entity_id=str(rule.pk)).count(), 1)
        payload = self.payload()
        payload.update(name="Replaced", priority=9, conditions=[], actions=[{"action_type": "wait", "delay_seconds": 10}])
        response = self.api.put(f"/api/automation-rules/{rule.pk}/configuration/", payload, format="json")
        self.assertEqual(response.status_code, 200, response.data)
        rule.refresh_from_db()
        self.assertEqual(rule.name, "Replaced")
        self.assertEqual(rule.priority, 9)
        self.assertEqual(rule.actions.get().action_type, "wait")
        self.assertEqual(rule.actions.get().order, 0)
        self.assertFalse(rule.conditions.exists())
        self.assertEqual(AuditLog.objects.filter(entity_type="AutomationRule", entity_id=str(rule.pk), action="update").count(), 1)
        self.assertEqual(ActivityEvent.objects.filter(entity_type="AutomationRule", entity_id=str(rule.pk)).count(), 2)

    def test_replace_failure_restores_original_rows_and_history(self):
        rule = self.saved_rule()
        before = self.snapshot(rule)
        payload = self.payload()
        payload.update(name="Must roll back", trigger_type="deal_created", conditions=[])
        create = AutomationAction.objects.create
        calls = 0

        def fail_second(**kwargs):
            nonlocal calls
            calls += 1
            if calls == 2:
                raise RuntimeError("injected replacement failure")
            return create(**kwargs)

        with patch.object(AutomationAction.objects, "create", side_effect=fail_second):
            response = self.api.put(f"/api/automation-rules/{rule.pk}/configuration/", payload, format="json")
        self.assertEqual(response.status_code, 500)
        self.assertEqual(self.snapshot(rule), before)

    def test_condition_failure_rolls_back_creation(self):
        before = self.counts()
        with patch.object(AutomationCondition.objects, "create", side_effect=RuntimeError("injected condition failure")):
            response = self.api.post("/api/automation-rules/create-manual/", self.payload(), format="json")
        self.assertEqual(response.status_code, 500)
        self.assertEqual(self.counts(), before)

    def test_history_failure_rolls_back_create_and_replace_including_audit(self):
        before = self.counts()
        with patch("apps.automations.configuration.write_activity_event", side_effect=RuntimeError("injected history failure")):
            response = self.api.post("/api/automation-rules/create-manual/", self.payload(), format="json")
        self.assertEqual(response.status_code, 500)
        self.assertEqual(self.counts(), before)
        rule = self.saved_rule()
        before = self.snapshot(rule)
        payload = self.payload()
        payload["name"] = "Must roll back"
        with patch("apps.automations.configuration.write_activity_event", side_effect=RuntimeError("injected history failure")):
            response = self.api.put(f"/api/automation-rules/{rule.pk}/configuration/", payload, format="json")
        self.assertEqual(response.status_code, 500)
        self.assertEqual(self.snapshot(rule), before)

    def test_invalid_replace_does_not_touch_existing_configuration(self):
        rule = self.saved_rule()
        before = self.snapshot(rule)
        for delta in ({"actions": []}, {"actions": [{"action_type": "assign_user", "config": {}}]},
                      {"conditions": [{"field": "secret", "value": {}}]}):
            response = self.api.put(f"/api/automation-rules/{rule.pk}/configuration/", {**self.payload(), **delta}, format="json")
            self.assertEqual(response.status_code, 400, response.data)
            self.assertEqual(self.snapshot(rule), before)

    def test_replace_requires_update_and_original_business(self):
        rule = self.saved_rule()
        before = self.snapshot(rule)
        other = Business.objects.create(owner=self.owner, name="Other", slug="other-config")
        response = self.api.put(f"/api/automation-rules/{rule.pk}/configuration/", {**self.payload(), "business": other.pk}, format="json")
        self.assertEqual(response.status_code, 400, response.data)
        user = User.objects.create_user(username="config-reader", email="config-reader@example.test", role="business_operator")
        role = BusinessRole.objects.create(business=self.business, name="Configuration reader")
        RolePermission.objects.create(business_role=role, resource="automations", action="view", scope="business")
        RolePermission.objects.create(business_role=role, resource="automations", action="update", is_allowed=False, scope="business")
        BusinessMember.objects.create(business=self.business, user=user, role="operator", business_role=role)
        self.api.force_authenticate(user)
        response = self.api.put(f"/api/automation-rules/{rule.pk}/configuration/", self.payload(), format="json")
        self.assertEqual(response.status_code, 403, response.data)
        outsider = User.objects.create_user(username="config-outsider", email="config-outsider@example.test")
        self.api.force_authenticate(outsider)
        response = self.api.put(f"/api/automation-rules/{rule.pk}/configuration/", self.payload(), format="json")
        self.assertEqual(response.status_code, 404, response.data)
        self.assertEqual(self.snapshot(rule), before)

    def test_child_reparent_cannot_empty_active_source(self):
        rule = self.saved_rule()
        rule.actions.last().delete()
        target = AutomationRule.objects.create(business=self.business, name="Target", trigger_type="lead_created")
        action = rule.actions.get()
        before = self.snapshot(rule)
        response = self.api.patch(f"/api/automation-actions/{action.pk}/", {"rule": target.pk}, format="json")
        self.assertEqual(response.status_code, 400, response.data)
        self.assertEqual(self.snapshot(rule), before)
        self.assertFalse(target.actions.exists())

    def test_child_delete_and_generic_rule_update_roll_back_on_history_failure(self):
        rule = self.saved_rule()
        before = self.snapshot(rule)
        with patch("apps.core.viewsets.write_activity_event", side_effect=RuntimeError("injected generic history failure")):
            response = self.api.patch(f"/api/automation-rules/{rule.pk}/", {"name": "Rollback"}, format="json")
        self.assertEqual(response.status_code, 500)
        self.assertEqual(self.snapshot(rule), before)
        with patch("apps.core.viewsets.write_activity_event", side_effect=RuntimeError("injected generic history failure")):
            response = self.api.delete(f"/api/automation-actions/{rule.actions.first().pk}/")
        self.assertEqual(response.status_code, 500)
        self.assertEqual(self.snapshot(rule), before)

    def test_allowed_child_removal_and_draft_edit_remain_usable(self):
        rule = self.saved_rule()
        response = self.api.delete(f"/api/automation-actions/{rule.actions.first().pk}/")
        self.assertEqual(response.status_code, 204)
        self.assertEqual(rule.actions.count(), 1)
        response = self.api.patch(f"/api/automation-rules/{rule.pk}/", {"is_active": False}, format="json")
        self.assertEqual(response.status_code, 200, response.data)
        response = self.api.delete(f"/api/automation-actions/{rule.actions.get().pk}/")
        self.assertEqual(response.status_code, 204)
        response = self.api.patch(f"/api/automation-rules/{rule.pk}/", {"is_active": True}, format="json")
        self.assertEqual(response.status_code, 400, response.data)
