from unittest.mock import patch

from django.test import TestCase
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.businesses.models import Business, BusinessMember, BusinessRole, RolePermission, Team
from apps.core.models import AuditLog


class SettingsTeamBoundaryTests(TestCase):
    def setUp(self):
        self.api = APIClient()
        self.owner = User.objects.create_user(username="team-settings-owner", email="team-settings-owner@example.com")
        self.viewer = User.objects.create_user(username="team-settings-viewer", email="team-settings-viewer@example.com")
        self.business = Business.objects.create(owner=self.owner, name="Team settings", slug="team-settings")
        self.owned_by_viewer = Business.objects.create(owner=self.viewer, name="Other", slug="team-settings-other")
        self.viewer_role = BusinessRole.objects.create(business=self.business, name="Team reader")
        RolePermission.objects.create(business_role=self.viewer_role, resource="team", action="view", scope="business")
        self.member = BusinessMember.objects.create(business=self.business, user=self.viewer, role="operator", business_role=self.viewer_role)
        self.role = BusinessRole.objects.create(business=self.business, name="Target")
        self.permission = RolePermission.objects.create(business_role=self.role, resource="clients", action="view", scope="own")
        self.team = Team.objects.create(business=self.business, name="Target team")

    def test_body_business_cannot_authorize_changes_in_read_only_business(self):
        self.api.force_authenticate(self.viewer)
        for url, payload in (
            (f"/api/team/roles/{self.role.pk}/", {"description": "changed"}),
            (f"/api/team/role-permissions/{self.permission.pk}/", {"scope": "business"}),
            (f"/api/team/departments/{self.team.pk}/", {"description": "changed"}),
            (f"/api/team/members/{self.member.pk}/", {"is_active": False}),
        ):
            with self.subTest(url=url):
                response = self.api.patch(url, {**payload, "business": self.owned_by_viewer.pk}, format="json")
                self.assertIn(response.status_code, (400, 403))
        self.permission.refresh_from_db()
        self.member.refresh_from_db()
        self.assertEqual(self.permission.scope, "own")
        self.assertTrue(self.member.is_active)

    def test_owner_cannot_reparent_role_or_department_between_owned_businesses(self):
        other = Business.objects.create(owner=self.owner, name="Also owned", slug="team-settings-owned")
        target_role = BusinessRole.objects.create(business=other, name="Move target")
        self.api.force_authenticate(self.owner)
        for url, payload in (
            (f"/api/team/roles/{self.role.pk}/", {"business": other.pk}),
            (f"/api/team/departments/{self.team.pk}/", {"business": other.pk}),
            (f"/api/team/role-permissions/{self.permission.pk}/", {"business_role": target_role.pk}),
        ):
            self.assertEqual(self.api.patch(url, payload, format="json").status_code, 400)

    def test_member_change_rolls_back_when_audit_fails(self):
        self.api.force_authenticate(self.owner)
        with patch("apps.businesses.views.write_audit_log", side_effect=RuntimeError("audit unavailable")):
            response = self.api.patch(f"/api/team/members/{self.member.pk}/", {"is_active": False}, format="json")
        self.assertEqual(response.status_code, 500)
        self.member.refresh_from_db()
        self.assertTrue(self.member.is_active)

    def test_profile_validates_timezone_and_preserves_inert_metadata(self):
        self.business.brand_color = "#123456"
        self.business.booking_buffer_minutes = 15
        self.business.save(update_fields=["brand_color", "booking_buffer_minutes"])
        self.api.force_authenticate(self.owner)
        url = f"/api/businesses/{self.business.pk}/"
        self.assertEqual(self.api.patch(url, {"timezone": "Invalid/Zone"}, format="json").status_code, 400)
        self.assertEqual(self.api.patch(url, {"timezone": "Asia/Almaty", "name": "Updated"}, format="json").status_code, 200)
        self.business.refresh_from_db()
        self.assertEqual(self.business.timezone, "Asia/Almaty")
        self.assertEqual(self.business.brand_color, "#123456")
        self.assertEqual(self.business.booking_buffer_minutes, 15)

    def test_missing_permission_creation_is_audited_and_validates_scope_and_duplicate(self):
        self.api.force_authenticate(self.owner)
        payload = {"business_role": self.role.pk, "resource": "clients", "action": "update", "scope": "own", "is_allowed": True}
        audit_count = AuditLog.objects.filter(business=self.business).count()
        response = self.api.post("/api/team/role-permissions/", payload, format="json")
        self.assertEqual(response.status_code, 201)
        self.assertEqual(AuditLog.objects.filter(business=self.business).count(), audit_count + 1)
        self.permission.refresh_from_db()
        self.assertEqual(self.permission.scope, "own")
        self.assertEqual(self.api.post("/api/team/role-permissions/", payload, format="json").status_code, 400)
        self.assertEqual(self.api.post("/api/team/role-permissions/", {**payload, "action": "delete", "scope": "invalid"}, format="json").status_code, 400)
        self.assertEqual(self.role.permissions.count(), 2)

    def test_missing_permission_creation_cannot_use_body_business_to_bypass_role_access(self):
        self.api.force_authenticate(self.viewer)
        payload = {"business": self.owned_by_viewer.pk, "business_role": self.role.pk, "resource": "clients", "action": "update", "scope": "business", "is_allowed": True}
        self.assertEqual(self.api.post("/api/team/role-permissions/", payload, format="json").status_code, 403)
        foreign_role = BusinessRole.objects.create(business=self.owned_by_viewer, name="Foreign role")
        self.api.force_authenticate(self.owner)
        self.assertEqual(self.api.post("/api/team/role-permissions/", {**payload, "business": self.business.pk, "business_role": foreign_role.pk}, format="json").status_code, 403)
        self.assertFalse(foreign_role.permissions.exists())
        self.assertFalse(self.role.permissions.filter(action="update").exists())

    def test_missing_permission_creation_rolls_back_when_audit_fails(self):
        self.api.force_authenticate(self.owner)
        with patch("apps.businesses.views.write_audit_log", side_effect=RuntimeError("audit unavailable")):
            response = self.api.post("/api/team/role-permissions/", {
                "business_role": self.role.pk, "resource": "clients", "action": "update", "scope": "business", "is_allowed": True,
            }, format="json")
        self.assertEqual(response.status_code, 500)
        self.assertFalse(self.role.permissions.filter(resource="clients", action="update").exists())
