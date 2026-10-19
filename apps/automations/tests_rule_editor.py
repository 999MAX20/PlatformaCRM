from unittest.mock import patch

from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.automations.engine import run_automations_for_event
from apps.automations.models import AutomationRule, AutomationRun
from apps.businesses.models import Business, BusinessMember, BusinessRole, RolePermission
from apps.clients.models import Client
from apps.leads.models import Lead
from apps.tasks.models import Task


class AutomationRuleEditorTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.owner = User.objects.create_user(username="editor-owner", email="editor-owner@example.test", role="business_owner")
        cls.business = Business.objects.create(owner=cls.owner, name="Editor", slug="editor")
        cls.rule = AutomationRule.objects.create(business=cls.business, name="Draft", trigger_type="lead_created")

    def setUp(self):
        self.api = APIClient()
        self.api.force_authenticate(self.owner)

    def payload(self):
        return {"business": self.business.pk, "name": "Configured", "trigger_type": "lead_created", "is_active": False,
                "actions": [{"action_type": "create_task", "config": {"title": "Editor follow-up"}}], "conditions": []}

    def test_existing_preview_is_read_only_and_rejects_invalid_composition(self):
        response = self.api.post(f"/api/automation-rules/{self.rule.pk}/preview/", self.payload(), format="json")
        self.assertEqual(response.status_code, 200, response.data)
        self.rule.refresh_from_db()
        self.assertEqual(self.rule.name, "Draft")
        self.assertFalse(self.rule.actions.exists())
        self.assertFalse(AutomationRun.objects.exists())
        response = self.api.post(f"/api/automation-rules/{self.rule.pk}/preview/", {**self.payload(), "actions": []}, format="json")
        self.assertEqual(response.status_code, 400, response.data)

    def test_update_only_role_can_preview_without_create_permission_or_creation_quota(self):
        user = User.objects.create_user(username="rule-editor", email="rule-editor@example.test", role="business_operator")
        role = BusinessRole.objects.create(business=self.business, name="Rule editor")
        for resource, action in (("automations", "view"), ("automations", "update"), ("tasks", "create")):
            RolePermission.objects.create(business_role=role, resource=resource, action=action, scope="business")
        RolePermission.objects.create(business_role=role, resource="automations", action="create", is_allowed=False, scope="business")
        BusinessMember.objects.create(business=self.business, user=user, role="operator", business_role=role)
        self.api.force_authenticate(user)
        with patch("apps.automations.views.assert_entitlement_allows", side_effect=RuntimeError("Creation quota is not an edit gate")):
            response = self.api.post(f"/api/automation-rules/{self.rule.pk}/preview/", self.payload(), format="json")
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(self.api.post("/api/automation-rules/preview/", self.payload(), format="json").status_code, 403)
        RolePermission.objects.filter(business_role=role, resource="automations", action="update").update(is_allowed=False)
        self.assertEqual(self.api.post(f"/api/automation-rules/{self.rule.pk}/preview/", self.payload(), format="json").status_code, 403)

    def test_preview_does_not_cross_business_or_expose_foreign_rule(self):
        other = Business.objects.create(owner=self.owner, name="Other", slug="editor-other")
        response = self.api.post(f"/api/automation-rules/{self.rule.pk}/preview/", {**self.payload(), "business": other.pk}, format="json")
        self.assertEqual(response.status_code, 400, response.data)
        outsider = User.objects.create_user(username="rule-outsider", email="rule-outsider@example.test")
        self.api.force_authenticate(outsider)
        self.assertEqual(self.api.post(f"/api/automation-rules/{self.rule.pk}/preview/", self.payload(), format="json").status_code, 404)

    @override_settings(AUTOMATIONS_RUN_INLINE=True)
    def test_draft_configure_preview_enable_executes_one_real_task(self):
        draft = self.api.post("/api/automation-rules/", {"business": self.business.pk, "name": "Simple draft", "trigger_type": "lead_created"}, format="json")
        self.assertEqual(draft.status_code, 201, draft.data)
        rule_id = draft.data["id"]
        self.assertEqual(self.api.patch(f"/api/automation-rules/{rule_id}/", {"is_active": True}, format="json").status_code, 400)
        self.assertEqual(self.api.post(f"/api/automation-rules/{rule_id}/preview/", self.payload(), format="json").status_code, 200)
        saved = self.api.put(f"/api/automation-rules/{rule_id}/configuration/", self.payload(), format="json")
        self.assertEqual(saved.status_code, 200, saved.data)
        self.assertEqual(self.api.patch(f"/api/automation-rules/{rule_id}/", {"is_active": True}, format="json").status_code, 200)
        client = Client.objects.create(business=self.business, full_name="Editor client")
        lead = Lead.objects.create(business=self.business, client=client)
        for _ in range(2):
            run_automations_for_event(business=self.business, trigger_type="lead_created", entity=lead)
        self.assertEqual(Task.objects.filter(business=self.business, lead=lead, title="Editor follow-up").count(), 1)
