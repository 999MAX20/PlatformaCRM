from unittest.mock import patch

from django.test import TestCase
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.businesses.models import Business, BusinessMember, BusinessRole, RolePermission
from apps.core.models import AuditLog


class RoleVisibilityTests(TestCase):
    def setUp(self):
        self.api = APIClient()
        self.owner = User.objects.create_user(username="visibility-owner", email="visibility-owner@example.com")
        self.business = Business.objects.create(owner=self.owner, name="Visibility", slug="visibility")
        self.role = BusinessRole.objects.create(business=self.business, name="Custom")
        self.allowed = RolePermission.objects.create(business_role=self.role, resource="clients", action="view", scope="own")
        self.denied = RolePermission.objects.create(business_role=self.role, resource="clients", action="delete", is_allowed=False, scope="none")
        self.url = f"/api/team/roles/{self.role.pk}/visibility/"
        self.api.force_authenticate(self.owner)

    def change(self, **overrides):
        return self.api.post(self.url, {"permission_ids": [self.allowed.pk, self.denied.pk], "scope": "business", **overrides}, format="json")

    def test_scope_preserves_action_grants_and_replay_is_noop(self):
        for scope in ("business", "none", "own"):
            self.assertEqual(self.change(scope=scope).status_code, 200)
            self.allowed.refresh_from_db()
            self.denied.refresh_from_db()
            self.assertTrue(self.allowed.is_allowed)
            self.assertFalse(self.denied.is_allowed)
            self.assertEqual(self.allowed.scope, scope)
            self.assertEqual(self.denied.scope, scope)
        count = AuditLog.objects.filter(entity_type="BusinessRole", entity_id=str(self.role.pk)).count()
        self.assertEqual(count, 3)
        self.assertEqual(self.change(scope="own").status_code, 200)
        self.assertEqual(AuditLog.objects.filter(entity_type="BusinessRole", entity_id=str(self.role.pk)).count(), count)

    def test_validation_rejects_whole_batch_without_partial_write(self):
        other_role = BusinessRole.objects.create(business=self.business, name="Other")
        other_permission = RolePermission.objects.create(business_role=other_role, resource="clients", action="view")
        for payload in ({"scope": "invalid"}, {"permission_ids": []}, {"permission_ids": [self.allowed.pk, self.allowed.pk]}, {"permission_ids": [self.allowed.pk, other_permission.pk]}):
            with self.subTest(payload=payload):
                self.assertEqual(self.change(**payload).status_code, 400)
                self.allowed.refresh_from_db()
                self.assertEqual(self.allowed.scope, "own")
        self.assertFalse(AuditLog.objects.filter(entity_type="BusinessRole", entity_id=str(self.role.pk)).exists())

    def test_role_denial_and_foreign_tenant(self):
        viewer = User.objects.create_user(username="visibility-viewer", email="visibility-viewer@example.com")
        BusinessMember.objects.create(business=self.business, user=viewer, role=BusinessMember.Roles.ACCOUNTANT)
        self.api.force_authenticate(viewer)
        self.assertIn(self.change().status_code, (403, 404))
        outsider = User.objects.create_user(username="visibility-outsider", email="visibility-outsider@example.com")
        foreign = Business.objects.create(owner=outsider, name="Foreign", slug="visibility-foreign")
        self.api.force_authenticate(outsider)
        # A business selector owned by the actor cannot authorize a different role.
        self.assertEqual(self.change(business=foreign.pk).status_code, 404)
        self.allowed.refresh_from_db()
        self.assertEqual(self.allowed.scope, "own")

    def test_audit_failure_rolls_back_all_permissions(self):
        with patch("apps.businesses.role_services.write_audit_log", side_effect=RuntimeError("audit unavailable")):
            self.assertEqual(self.change().status_code, 500)
        self.allowed.refresh_from_db()
        self.denied.refresh_from_db()
        self.assertEqual(self.allowed.scope, "own")
        self.assertEqual(self.denied.scope, "none")
