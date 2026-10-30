from unittest.mock import patch

from django.test import TestCase
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.businesses.access import (
    Actions, PERMISSION_CATALOG, ROLE_PRESETS, Resources, can, ensure_default_roles,
)
from apps.businesses.models import Business, BusinessMember, BusinessRole, RolePermission
from apps.onboarding.services import apply_niche_template


class OnboardingPresetPreservationTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(username="preset-owner", email="preset-owner@example.test")
        self.actor = User.objects.create_user(username="preset-settings", email="preset-settings@example.test")
        self.business = Business.objects.create(owner=self.owner, name="Preset business", slug="preset-business")
        ensure_default_roles(self.business)
        self.role = self.business.roles.get(preset_key=BusinessMember.Roles.MANAGER)
        self.member = BusinessMember.objects.create(
            business=self.business, user=self.actor, role=BusinessMember.Roles.MANAGER,
            business_role=self.role,
        )
        self.api = APIClient()

    def snapshot(self, role):
        role.refresh_from_db()
        return (
            role.name, role.description, role.preset_key, role.permissions_json,
            role.is_system, role.is_active, role.updated_at,
            list(role.permissions.order_by("pk").values()),
        )

    def restrict(self):
        RolePermission.objects.update_or_create(
            business_role=self.role, resource=Resources.CLIENTS, action=Actions.VIEW,
            defaults={"is_allowed": False, "scope": RolePermission.Scopes.NONE},
        )

    def apply_api(self, actor=None, business=None):
        self.api.force_authenticate(actor or self.owner)
        return self.api.post("/api/onboarding/apply-template/", {
            "business": (business or self.business).pk, "template_key": "other",
        }, format="json")

    def test_helper_preserves_explicit_denial_and_effective_access(self):
        self.restrict()
        before = self.snapshot(self.role)
        self.assertFalse(can(self.actor, self.business, Resources.CLIENTS, Actions.VIEW).allowed)
        ensure_default_roles(self.business)
        self.assertEqual(self.snapshot(self.role), before)
        self.assertFalse(can(self.actor, self.business, Resources.CLIENTS, Actions.VIEW).allowed)

    def test_repeated_onboarding_preserves_settings_only_actor_restrictions(self):
        self.restrict()
        RolePermission.objects.update_or_create(
            business_role=self.role, resource=Resources.SETTINGS, action=Actions.UPDATE,
            defaults={"is_allowed": True, "scope": RolePermission.Scopes.BUSINESS},
        )
        RolePermission.objects.update_or_create(
            business_role=self.role, resource=Resources.TEAM, action=Actions.MANAGE,
            defaults={"is_allowed": False, "scope": RolePermission.Scopes.NONE},
        )
        self.assertTrue(can(self.actor, self.business, Resources.SETTINGS, Actions.UPDATE).allowed)
        self.assertFalse(can(self.actor, self.business, Resources.TEAM, Actions.MANAGE).allowed)
        before = self.snapshot(self.role)
        for _ in range(2):
            response = self.apply_api(self.actor)
            self.assertEqual(response.status_code, 201, response.data)
            self.assertEqual(self.snapshot(self.role), before)
            self.assertFalse(can(self.actor, self.business, Resources.CLIENTS, Actions.VIEW).allowed)
            self.assertFalse(can(self.actor, self.business, Resources.TEAM, Actions.MANAGE).allowed)

    def test_owner_onboarding_preserves_scope_customization(self):
        for scope in [RolePermission.Scopes.OWN, RolePermission.Scopes.TEAM]:
            with self.subTest(scope=scope):
                RolePermission.objects.update_or_create(
                    business_role=self.role, resource=Resources.CLIENTS, action=Actions.VIEW,
                    defaults={"is_allowed": True, "scope": scope},
                )
                before = self.snapshot(self.role)
                self.assertEqual(self.apply_api().status_code, 201)
                self.assertEqual(self.snapshot(self.role), before)
                self.assertEqual(can(self.actor, self.business, Resources.CLIENTS, Actions.VIEW).scope, scope)

    def test_existing_metadata_json_and_deactivation_untouched(self):
        self.role.name = "Custom restricted manager"
        self.role.description = "Owner customization"
        self.role.permissions_json = {"clients": {"view": "none"}}
        self.role.is_active = False
        self.role.is_system = False
        self.role.save()
        before = self.snapshot(self.role)
        apply_niche_template(self.business, "other", actor=self.owner)
        self.assertEqual(self.snapshot(self.role), before)

    def test_missing_permission_is_not_silently_recreated(self):
        self.role.permissions.filter(resource=Resources.CLIENTS, action=Actions.VIEW).delete()
        before = self.snapshot(self.role)
        ensure_default_roles(self.business)
        self.assertEqual(self.snapshot(self.role), before)

    def test_empty_existing_preset_is_not_repopulated(self):
        self.role.permissions.all().delete()
        self.role.permissions_json = {}
        self.role.save()
        before = self.snapshot(self.role)
        ensure_default_roles(self.business)
        self.assertEqual(self.snapshot(self.role), before)

    def test_missing_preset_created_without_touching_other_roles(self):
        self.restrict()
        before = self.snapshot(self.role)
        self.business.roles.get(preset_key=BusinessMember.Roles.OPERATOR).delete()
        ensure_default_roles(self.business)
        self.assertTrue(self.business.roles.get(preset_key=BusinessMember.Roles.OPERATOR).permissions.exists())
        self.assertEqual(self.snapshot(self.role), before)

    def test_initial_setup_creates_complete_defaults_and_is_repeatable(self):
        self.business.roles.all().delete()
        response = self.apply_api()
        self.assertEqual(response.status_code, 201, response.data)
        for key, preset in ROLE_PRESETS.items():
            role = self.business.roles.get(preset_key=key)
            self.assertEqual(role.permissions_json, preset)
            self.assertTrue(role.is_active)
            self.assertTrue(role.is_system)
            expected = {(r, a, "business") for r, actions in PERMISSION_CATALOG.items() for a in actions} if "*" in preset else {(r, a, scope) for r, actions in preset.items() for a, scope in actions.items()}
            self.assertEqual(set(role.permissions.values_list("resource", "action", "scope")), expected)
            self.assertFalse(role.permissions.filter(is_allowed=False).exists())
        before = {r.pk: self.snapshot(r) for r in self.business.roles.all()}
        self.assertEqual(self.apply_api().status_code, 201)
        self.assertEqual({r.pk: self.snapshot(r) for r in self.business.roles.all()}, before)

    def test_other_business_roles_are_untouched(self):
        other = Business.objects.create(owner=self.owner, name="Other", slug="other-preset")
        ensure_default_roles(other)
        before = {r.pk: self.snapshot(r) for r in other.roles.all()}
        self.assertEqual(self.apply_api().status_code, 201)
        self.assertEqual({r.pk: self.snapshot(r) for r in other.roles.all()}, before)

    def test_unauthorized_onboarding_does_not_change_roles(self):
        RolePermission.objects.update_or_create(
            business_role=self.role, resource=Resources.SETTINGS, action=Actions.UPDATE,
            defaults={"is_allowed": False, "scope": "none"},
        )
        self.restrict()
        before = self.snapshot(self.role)
        self.assertEqual(self.apply_api(self.actor).status_code, 403)
        self.assertEqual(self.snapshot(self.role), before)

    def test_failed_new_role_initialization_rolls_back(self):
        self.business.roles.all().delete()
        with patch.object(RolePermission.objects, "update_or_create", side_effect=RuntimeError("synthetic seed failure")):
            with self.assertRaisesRegex(RuntimeError, "synthetic seed failure"):
                ensure_default_roles(self.business)
        self.assertFalse(self.business.roles.exists())
        ensure_default_roles(self.business)
        self.assertEqual(self.business.roles.count(), len(ROLE_PRESETS))

    def test_explicit_permission_edit_still_applies_and_survives_onboarding(self):
        self.restrict()
        permission = self.role.permissions.get(resource=Resources.CLIENTS, action=Actions.VIEW)
        self.api.force_authenticate(self.owner)
        response = self.api.patch(f"/api/team/role-permissions/{permission.pk}/", {"is_allowed": True, "scope": "own"}, format="json")
        self.assertEqual(response.status_code, 200, response.data)
        before = self.snapshot(self.role)
        self.assertEqual(self.apply_api().status_code, 201)
        self.assertEqual(self.snapshot(self.role), before)
        self.assertEqual(can(self.actor, self.business, Resources.CLIENTS, Actions.VIEW).scope, "own")
