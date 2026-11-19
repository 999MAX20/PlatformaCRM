from datetime import timedelta
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient
from apps.accounts.models import User
from apps.businesses.access import ensure_default_roles
from apps.businesses.models import Business, BusinessInvitation, BusinessRole, RolePermission


class InvitationPreviewAccessTests(TestCase):
    def setUp(self):
        owner = User.objects.create_user(username="preview-owner", email="preview@example.invalid")
        self.business = Business.objects.create(owner=owner, name="Preview business", slug="preview-business")
        ensure_default_roles(self.business)
        self.role = BusinessRole.objects.get(business=self.business, preset_key="operator")
        self.invite = BusinessInvitation.objects.create(business=self.business, email="recipient@example.invalid", role="operator",
            business_role=self.role, expires_at=timezone.now() + timedelta(hours=24))
        self.api = APIClient()

    def preview(self):
        response = self.api.get(f"/api/team/invitations/preview/{self.invite.token}/")
        self.assertEqual(response.status_code, 200)
        return response.data

    def test_public_preview_contains_configured_grants_not_role_records(self):
        RolePermission.objects.update_or_create(business_role=self.role, resource="clients", action="view",
            defaults={"scope": "own", "is_allowed": True})
        RolePermission.objects.update_or_create(business_role=self.role, resource="appointments", action="view",
            defaults={"scope": "none", "is_allowed": False})
        data = self.preview()
        self.assertIn({"resource": "clients", "action": "view", "scope": "own"}, data["access_summary"])
        self.assertFalse(any(p["resource"] == "appointments" and p["action"] == "view" for p in data["access_summary"]))
        self.assertTrue(all(set(p) == {"resource", "action", "scope"} for p in data["access_summary"]))
        self.assertIsNone(data["role_name"])

    def test_terminal_and_inactive_roles_do_not_advertise_access(self):
        self.role.is_active = False
        self.role.save(update_fields=["is_active"])
        self.assertEqual(self.preview()["access_summary"], [])
        self.role.is_active = True
        self.role.save(update_fields=["is_active"])
        self.invite.revoked_at = timezone.now()
        self.invite.save(update_fields=["revoked_at"])
        self.assertEqual(self.preview()["access_summary"], [])

    def test_custom_role_name_and_foreign_role_isolation(self):
        self.role.is_system = False
        self.role.name = "Custom reception"
        self.role.save(update_fields=["is_system", "name"])
        self.assertEqual(self.preview()["role_name"], "Custom reception")
        other = Business.objects.create(owner=self.business.owner, name="Other", slug="preview-other")
        self.role.business = other
        self.role.save(update_fields=["business"])
        data = self.preview()
        self.assertEqual(data["access_summary"], [])
        self.assertIsNone(data["role_name"])
