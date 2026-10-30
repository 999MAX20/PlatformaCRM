from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework.exceptions import PermissionDenied

from apps.accounts.models import User
from apps.automations.models import AutomationAction, AutomationRule
from apps.automations.action_validation import validate_action_config
from apps.branches.models import BranchAccess
from apps.businesses.models import Business, BusinessMember, BusinessRole, RolePermission


class ConfigurationAuthorityTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(username="authority-owner", email="authority-owner@example.invalid")
        self.actor = User.objects.create_user(username="authority-actor", email="authority-actor@example.invalid")
        self.business = Business.objects.create(owner=self.owner, name="Authority", slug="authority")
        self.role = BusinessRole.objects.create(business=self.business, name="Configurator")
        self.member = BusinessMember.objects.create(business=self.business, user=self.actor, role="operator", business_role=self.role)
        self.grant = BranchAccess.objects.create(member=self.member, all_branches=True)
        for action in ["view", "create", "update", "delete"]:
            RolePermission.objects.create(business_role=self.role, resource="automations", action=action, scope="business")
        self.permission = RolePermission.objects.create(business_role=self.role, resource="leads", action="update", scope="own")
        self.api = APIClient()
        self.api.force_authenticate(self.actor)

    def payload(self):
        return {"business": self.business.pk, "name": "Delegated assignment", "trigger_type": "lead_created", "is_active": True,
                "actions": [{"action_type": "assign_user", "config": {"user_id": self.actor.pk}}]}

    def test_own_and_team_configurators_cannot_delegate_owner_assignment(self):
        for scope in ["own", "team"]:
            with self.subTest(scope=scope):
                self.permission.scope = scope
                self.permission.save()
                response = self.api.post("/api/automation-rules/create-manual/", self.payload(), format="json")
                self.assertEqual(response.status_code, 403, response.data)
                self.assertFalse(AutomationRule.objects.exists())
                self.assertFalse(AutomationAction.objects.exists())

    def test_branch_restricted_configurator_cannot_delegate_businesswide_action(self):
        self.permission.scope = "business"
        self.permission.save()
        self.grant.all_branches = False
        self.grant.save()
        response = self.api.post("/api/automation-rules/create-manual/", self.payload(), format="json")
        self.assertEqual(response.status_code, 403, response.data)
        self.assertFalse(AutomationRule.objects.exists())

    def test_businesswide_action_and_network_grant_allow_configuration(self):
        self.permission.scope = "business"
        self.permission.save()
        response = self.api.post("/api/automation-rules/create-manual/", self.payload(), format="json")
        self.assertEqual(response.status_code, 201, response.data)

    def saved_rule(self, active=True):
        rule = AutomationRule.objects.create(business=self.business, name="Owner rule", trigger_type="lead_created", is_active=active)
        action = AutomationAction.objects.create(rule=rule, action_type="assign_user", config={"user_id": self.actor.pk})
        return rule, action

    def test_preview_replace_activation_and_action_writes_enforce_same_authority(self):
        rule, action = self.saved_rule(active=False)
        cases = [
            ("post", "/api/automation-rules/preview/", self.payload()),
            ("post", f"/api/automation-rules/{rule.pk}/preview/", self.payload()),
            ("put", f"/api/automation-rules/{rule.pk}/configuration/", self.payload()),
            ("patch", f"/api/automation-rules/{rule.pk}/", {"is_active": True}),
            ("post", "/api/automation-actions/", {"rule": rule.pk, "action_type": "assign_user", "config": {"user_id": self.actor.pk}}),
            ("patch", f"/api/automation-actions/{action.pk}/", {"config": {"user_id": self.actor.pk}}),
        ]
        for method, path, payload in cases:
            with self.subTest(path=path, method=method):
                response = getattr(self.api, method)(path, payload, format="json")
                self.assertEqual(response.status_code, 403, response.data)
                rule.refresh_from_db()
                self.assertFalse(rule.is_active)
                self.assertEqual(rule.actions.count(), 1)

    def test_safe_deactivation_still_works_after_action_authority_revoked(self):
        rule, _ = self.saved_rule()
        response = self.api.patch(f"/api/automation-rules/{rule.pk}/", {"is_active": False}, format="json")
        self.assertEqual(response.status_code, 200, response.data)
        rule.refresh_from_db()
        self.assertFalse(rule.is_active)

    def test_active_composition_change_rolls_back_when_remaining_action_exceeds_scope(self):
        rule, _ = self.saved_rule()
        wait = AutomationAction.objects.create(rule=rule, action_type="wait", config={}, delay_seconds=1)
        response = self.api.delete(f"/api/automation-actions/{wait.pk}/")
        self.assertEqual(response.status_code, 403, response.data)
        self.assertEqual(rule.actions.count(), 2)

    def test_each_owner_effect_requires_its_corresponding_full_action_right(self):
        for action_type, resource, action, config in [
            ("create_task", "tasks", "create", {}),
            ("create_follow_up", "tasks", "create", {}),
            ("create_notification", "notifications", "manage", {}),
            ("add_note", "clients", "create", {"text": "Note"}),
        ]:
            with self.subTest(action_type=action_type):
                permission, _ = RolePermission.objects.update_or_create(business_role=self.role, resource=resource, action=action, defaults={"scope": "own"})
                with self.assertRaises(PermissionDenied):
                    validate_action_config(action_type=action_type, config=config, business=self.business, trigger_type="lead_created", actor=self.actor)
                permission.scope = "business"
                permission.save()
        self.permission.scope = "business"
        self.permission.save()
        for action_type in ["create_task", "create_follow_up", "create_notification", "add_note"]:
            validate_action_config(action_type=action_type, config={}, business=self.business, trigger_type="lead_created", actor=self.actor)
        self.grant.all_branches = False
        self.grant.save()
        # Wait has no privileged effect; it does not need an invented action grant.
        validate_action_config(action_type="wait", config={}, delay_seconds=1, business=self.business, trigger_type="lead_created", actor=self.actor)
