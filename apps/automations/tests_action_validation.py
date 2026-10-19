from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.automations.models import AutomationAction, AutomationRule
from apps.businesses.models import Business, BusinessMember, BusinessRole, RolePermission
from apps.automations.engine import run_automations_for_event
from apps.automations.models import AutomationRun
from apps.clients.models import Client
from apps.leads.models import Lead
from apps.tasks.models import Task
from apps.activities.models import Note


class AutomationActionValidationTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.owner = User.objects.create_user(username="action-owner", email="action-owner@example.test", role="business_owner")
        cls.business = Business.objects.create(owner=cls.owner, name="Actions", slug="action-validation")

    def setUp(self):
        self.api = APIClient()
        self.api.force_authenticate(self.owner)

    def payload(self, action_type="assign_user", config=None):
        return {"business": self.business.pk, "name": "Validated action", "trigger_type": "lead_created",
                "actions": [{"action_type": action_type, "config": {} if config is None else config}]}

    def test_preview_and_save_reject_assignment_without_user(self):
        for route in ("preview", "create-manual"):
            response = self.api.post(f"/api/automation-rules/{route}/", self.payload(), format="json")
            self.assertEqual(response.status_code, 400, response.data)
        self.assertFalse(AutomationRule.objects.exists())

    def test_action_crud_rejects_non_object_config(self):
        rule = AutomationRule.objects.create(business=self.business, name="Draft", trigger_type="lead_created")
        response = self.api.post("/api/automation-actions/", {
            "rule": rule.pk, "action_type": "create_task", "config": ["invalid"],
        }, format="json")
        self.assertEqual(response.status_code, 400, response.data)
        self.assertFalse(rule.actions.exists())

    def test_activation_rejects_invalid_saved_action(self):
        rule = AutomationRule.objects.create(business=self.business, name="Legacy draft", trigger_type="lead_created")
        AutomationAction.objects.create(rule=rule, action_type="assign_user", config={})
        response = self.api.patch(f"/api/automation-rules/{rule.pk}/", {"is_active": True}, format="json")
        self.assertEqual(response.status_code, 400, response.data)
        rule.refresh_from_db()
        self.assertFalse(rule.is_active)

    def test_action_config_matrix_is_rejected_by_preview_and_save(self):
        invalid = [
            ("create_task", {"priority": "invented"}), ("create_task", {"title": 42}),
            ("create_task", {"title": " "}), ("create_task", {"description": []}),
            ("create_task", {"due_at": "yesterday"}), ("create_task", {"due_at": None}),
            ("create_task", {"status": "done"}), ("create_task", {"assignee_id": True}),
            ("create_follow_up", {"due_in_days": -1}), ("create_follow_up", {"due_in_days": 1.5}),
            ("create_notification", {"channel": "fax"}), ("create_notification", {"category": "unknown"}),
            ("create_notification", {"priority": 1}), ("create_notification", {"include_owner": "false"}),
            ("create_notification", {"action_url": "javascript:alert(1)"}),
            ("add_note", {"text": {"raw": "object"}}), ("assign_user", {"user_id": "abc"}),
            ("wait", {}), ("wait", {"title": "unused"}),
        ]
        for action_type, config in invalid:
            for route in ("preview", "create-manual"):
                with self.subTest(action=action_type, config=config, route=route):
                    response = self.api.post(f"/api/automation-rules/{route}/", self.payload(action_type, config), format="json")
                    self.assertEqual(response.status_code, 400, response.data)
        self.assertFalse(AutomationRule.objects.exists())

    def test_assignment_requires_compatible_trigger_and_active_eligible_member(self):
        user = User.objects.create_user(username="action-member", email="action-member@example.test", role="business_manager")
        member = BusinessMember.objects.create(business=self.business, user=user, role="manager")
        payload = self.payload("assign_user", {"user_id": user.pk})
        payload["trigger_type"] = "appointment_created"
        self.assertEqual(self.api.post("/api/automation-rules/preview/", payload, format="json").status_code, 400)
        payload["trigger_type"] = "deal_created"
        self.assertEqual(self.api.post("/api/automation-rules/preview/", payload, format="json").status_code, 200)
        member.role = "operator"
        member.save()
        self.assertEqual(self.api.post("/api/automation-rules/preview/", payload, format="json").status_code, 400)
        member.role = "manager"
        member.save()
        user.is_active = False
        user.save()
        self.assertEqual(self.api.post("/api/automation-rules/preview/", payload, format="json").status_code, 400)

    def test_foreign_or_inactive_user_is_not_silently_replaced_with_fallback(self):
        user = User.objects.create_user(username="outside-action", email="outside-action@example.test")
        for action_type, key in (("create_task", "assignee_id"), ("create_notification", "recipient_id"), ("assign_user", "user_id")):
            response = self.api.post("/api/automation-rules/preview/", self.payload(action_type, {key: user.pk}), format="json")
            self.assertEqual(response.status_code, 400, response.data)
        BusinessMember.objects.create(business=self.business, user=user, role="manager", is_active=False)
        response = self.api.post("/api/automation-rules/preview/", self.payload("create_task", {"assignee_id": user.pk}), format="json")
        self.assertEqual(response.status_code, 400, response.data)

    def test_builder_needs_action_permission_as_well_as_automation_permission(self):
        actor = User.objects.create_user(username="action-builder", email="action-builder@example.test", role="business_operator")
        role = BusinessRole.objects.create(business=self.business, name="Rules only")
        for action in ("view", "create", "update"):
            RolePermission.objects.create(business_role=role, resource="automations", action=action, scope="business")
        RolePermission.objects.create(business_role=role, resource="tasks", action="create", is_allowed=False, scope="business")
        BusinessMember.objects.create(business=self.business, user=actor, role="operator", business_role=role)
        self.api.force_authenticate(actor)
        for route in ("preview", "create-manual"):
            response = self.api.post(f"/api/automation-rules/{route}/", self.payload("create_task"), format="json")
            self.assertEqual(response.status_code, 403, response.data)
        self.assertFalse(AutomationRule.objects.exists())

    def test_all_supported_actions_keep_valid_config_and_activate(self):
        for action_type, config in (
            ("create_task", {"title": "Call", "due_at": "2027-01-20T10:00:00+05:00", "assignee_id": self.owner.pk}),
            ("create_follow_up", {"due_in_days": 2}),
            ("create_notification", {"channel": "system", "include_owner": True, "action_url": "/app/leads"}),
            ("add_note", {"text": "A note"}), ("assign_user", {"user_id": self.owner.pk}), ("wait", {}),
        ):
            payload = self.payload(action_type, config)
            if action_type == "wait":
                payload["actions"][0]["delay_seconds"] = 10
            preview = self.api.post("/api/automation-rules/preview/", payload, format="json")
            self.assertEqual(preview.status_code, 200, preview.data)
            saved = self.api.post("/api/automation-rules/create-manual/", payload, format="json")
            self.assertEqual(saved.status_code, 201, saved.data)
            response = self.api.patch(f"/api/automation-rules/{saved.data['id']}/", {"is_active": True}, format="json")
            self.assertEqual(response.status_code, 200, response.data)

    def test_action_partial_edit_revalidates_type_config_and_rule(self):
        rule = AutomationRule.objects.create(business=self.business, name="Draft", trigger_type="lead_created")
        action = AutomationAction.objects.create(rule=rule, action_type="create_task", config={"title": "Keep"})
        response = self.api.patch(f"/api/automation-actions/{action.pk}/", {"action_type": "assign_user"}, format="json")
        self.assertEqual(response.status_code, 400, response.data)
        action.refresh_from_db()
        self.assertEqual(action.action_type, "create_task")
        response = self.api.patch(f"/api/automation-actions/{action.pk}/", {"config": {"priority": "high"}}, format="json")
        self.assertEqual(response.status_code, 200, response.data)

    def test_empty_rule_cannot_be_enabled_but_invalid_rule_can_be_disabled(self):
        rule = AutomationRule.objects.create(business=self.business, name="Empty", trigger_type="lead_created")
        response = self.api.patch(f"/api/automation-rules/{rule.pk}/", {"is_active": True}, format="json")
        self.assertEqual(response.status_code, 400, response.data)
        rule.is_active = True
        rule.save()
        response = self.api.patch(f"/api/automation-rules/{rule.pk}/", {"is_active": False}, format="json")
        self.assertEqual(response.status_code, 200, response.data)

    @override_settings(AUTOMATIONS_RUN_INLINE=True)
    def test_runtime_rechecks_member_and_has_no_partial_effect_for_invalid_pending_config(self):
        user = User.objects.create_user(username="stale-action", email="stale-action@example.test", role="business_manager")
        member = BusinessMember.objects.create(business=self.business, user=user, role="manager")
        payload = self.payload("create_task", {"title": "Must not exist"})
        payload["actions"].append({"action_type": "assign_user", "config": {"user_id": user.pk}})
        payload["is_active"] = True
        saved = self.api.post("/api/automation-rules/create-manual/", payload, format="json")
        self.assertEqual(saved.status_code, 201, saved.data)
        member.is_active = False
        member.save()
        client = Client.objects.create(business=self.business, full_name="Runtime client")
        lead = Lead.objects.create(business=self.business, client=client, responsible_user=self.owner)
        run = run_automations_for_event(business=self.business, trigger_type="lead_created", entity=lead)[0]
        run.refresh_from_db()
        self.assertEqual(run.status, AutomationRun.Statuses.RETRY_SCHEDULED)
        self.assertFalse(Task.objects.filter(title="Must not exist").exists())
        self.assertEqual(run.current_action_index, 0)
        member.is_active = True
        member.save()
        response = self.api.post(f"/api/automation-runs/{run.pk}/retry/")
        self.assertEqual(response.status_code, 200, response.data)
        lead.refresh_from_db()
        self.assertEqual(lead.responsible_user_id, user.pk)
        self.assertEqual(Task.objects.filter(title="Must not exist").count(), 1)

    @override_settings(AUTOMATIONS_RUN_INLINE=True)
    def test_runtime_blocks_legacy_invalid_config_and_foreign_entity(self):
        rule = AutomationRule.objects.create(business=self.business, name="Legacy", trigger_type="lead_created", is_active=True)
        action = AutomationAction.objects.create(rule=rule, action_type="add_note", config={"text": ["invalid"]})
        run = run_automations_for_event(business=self.business, trigger_type="lead_created", payload={"attempt": 1})[0]
        run.refresh_from_db()
        self.assertEqual(run.status, AutomationRun.Statuses.RETRY_SCHEDULED)
        self.assertFalse(Note.objects.exists())

        action.config = {"text": "No foreign note"}
        action.save()
        foreign = Business.objects.create(owner=self.owner, name="Foreign", slug="foreign-runtime")
        client = Client.objects.create(business=foreign, full_name="Foreign")
        lead = Lead.objects.create(business=foreign, client=client)
        run = run_automations_for_event(business=self.business, trigger_type="lead_created", entity=lead)[0]
        run.refresh_from_db()
        self.assertEqual(run.status, AutomationRun.Statuses.RETRY_SCHEDULED)
        self.assertFalse(Note.objects.exists())

    def test_draft_trigger_change_revalidates_existing_actions(self):
        rule = AutomationRule.objects.create(business=self.business, name="Draft", trigger_type="lead_created")
        AutomationAction.objects.create(rule=rule, action_type="assign_user", config={"user_id": self.owner.pk})
        response = self.api.patch(f"/api/automation-rules/{rule.pk}/", {"trigger_type": "appointment_created"}, format="json")
        self.assertEqual(response.status_code, 400, response.data)
        rule.refresh_from_db()
        self.assertEqual(rule.trigger_type, "lead_created")

    def test_derived_rule_permission_allows_own_action_and_hides_foreign_action(self):
        rule = AutomationRule.objects.create(business=self.business, name="Own", trigger_type="lead_created")
        action = AutomationAction.objects.create(rule=rule, action_type="create_task", config={})
        self.assertEqual(self.api.get(f"/api/automation-actions/{action.pk}/").status_code, 200)
        foreign_owner = User.objects.create_user(username="foreign-builder", email="foreign-builder@example.test")
        foreign = Business.objects.create(owner=foreign_owner, name="Foreign builder", slug="foreign-builder")
        foreign_rule = AutomationRule.objects.create(business=foreign, name="Foreign", trigger_type="lead_created")
        foreign_action = AutomationAction.objects.create(rule=foreign_rule, action_type="create_task", config={})
        self.assertEqual(self.api.get(f"/api/automation-actions/{foreign_action.pk}/").status_code, 404)
        self.assertEqual(self.api.patch(f"/api/automation-actions/{foreign_action.pk}/", {"config": {}}, format="json").status_code, 404)
