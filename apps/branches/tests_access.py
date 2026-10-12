from unittest.mock import patch

from django.test import TestCase
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.businesses.models import Business, BusinessMember
from apps.core.models import AuditLog
from .models import Branch, BranchAccess


class BranchAccessTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(username="branch-owner", email="branch-owner@example.test")
        self.business = Business.objects.create(owner=self.owner, name="Clinic", slug="branch-clinic")
        self.admin = User.objects.create_user(username="branch-admin", email="branch-admin@example.test")
        self.member = BusinessMember.objects.create(business=self.business, user=self.admin, role="admin")
        self.api = APIClient()
        self.api.force_authenticate(self.owner)

    def create(self, name="First", **overrides):
        return self.api.post("/api/branches/", {"business": self.business.pk, "name": name, "address": "Address", **overrides}, format="json")

    def test_first_branch_preserves_member_location_but_not_future_branches(self):
        first = self.create()
        second = self.create("Second")
        self.assertEqual(first.status_code, 201, first.data)
        self.assertEqual(second.status_code, 201, second.data)
        grant = BranchAccess.objects.get(member=self.member)
        self.assertFalse(grant.all_branches)
        self.assertEqual(list(grant.branches.values_list("pk", flat=True)), [first.data["id"]])
        self.api.force_authenticate(self.admin)
        self.assertEqual(self.api.patch(f'/api/branches/{first.data["id"]}/', {"phone": "123"}).status_code, 200)
        self.assertEqual(self.api.patch(f'/api/branches/{second.data["id"]}/', {"phone": "123"}).status_code, 403)
        self.assertEqual(self.create("Third").status_code, 403)
        Branch.objects.filter(pk=first.data["id"]).update(is_active=False)
        paused = self.api.get(f'/api/branches/{first.data["id"]}/').data
        self.assertTrue(paused["can_work"])
        self.assertFalse(paused["can_book"])
        outside = self.api.get(f'/api/branches/{second.data["id"]}/').data
        self.assertFalse(outside["can_work"])

    def test_grants_cannot_include_foreign_branch_or_escalate(self):
        first = self.create().data["id"]
        second = self.create("Second").data["id"]
        other = Business.objects.create(owner=self.owner, name="Other", slug="branch-other")
        foreign = Branch.objects.create(business=other, name="Foreign")
        response = self.api.post("/api/branches/member-access/", {"member": self.member.pk, "branch_ids": [foreign.pk]}, format="json")
        self.assertEqual(response.status_code, 400)
        self.api.force_authenticate(self.admin)
        response = self.api.post("/api/branches/member-access/", {"member": self.member.pk, "branch_ids": [], "all_branches": True}, format="json")
        self.assertEqual(response.status_code, 403)
        self.api.force_authenticate(self.owner)
        response = self.api.post("/api/branches/member-access/", {"member": self.member.pk, "branch_ids": [first, second]}, format="json")
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(len(response.data["branch_ids"]), 2)

    def test_all_existing_locations_do_not_confer_future_locations(self):
        self.create()
        self.api.force_authenticate(self.admin)
        self.assertEqual(self.create("Escalation").status_code, 403)
        response = self.api.post("/api/branches/member-access/", {
            "member": self.member.pk, "branch_ids": [], "all_branches": True}, format="json")
        self.assertEqual(response.status_code, 403)
        self.assertFalse(BranchAccess.objects.get(member=self.member).all_branches)

    def test_branch_limited_staff_cannot_disable_shared_catalog_or_expand_agent_scope(self):
        from apps.services.models import Service
        from apps.bots.automation_policy import authorize_configuration
        from apps.bots.models import Bot
        from rest_framework.exceptions import PermissionDenied, ValidationError
        first = self.create().data["id"]
        second = self.create("Second").data["id"]
        service = Service.objects.create(business=self.business, name="Shared")
        self.api.force_authenticate(self.admin)
        self.assertEqual(self.api.patch(f"/api/services/{service.pk}/", {"name": "Unauthorized"}).status_code, 403)
        self.assertEqual(self.api.post(f"/api/services/{service.pk}/deactivate/").status_code, 403)
        service.refresh_from_db()
        self.assertTrue(service.is_active)
        self.assertEqual(service.name, "Shared")
        bot = Bot.objects.create(business=self.business, name="Reception")
        with self.assertRaises(PermissionDenied):
            authorize_configuration(bot, {}, [], self.admin)
        with self.assertRaises(ValidationError):
            authorize_configuration(bot, {"branch_ids": [second]}, [], self.admin)
        self.assertEqual(authorize_configuration(bot, {"branch_ids": [first]}, [], self.admin)["branch_ids"], [first])

    def test_tenant_role_and_immutable_business(self):
        first = self.create().data["id"]
        other = Business.objects.create(owner=self.owner, name="Other", slug="branch-other")
        self.assertEqual(self.api.patch(f"/api/branches/{first}/", {"business": other.pk}).status_code, 400)
        outsider = User.objects.create_user(username="branch-outsider")
        self.api.force_authenticate(outsider)
        self.assertEqual(self.create("Foreign write").status_code, 403)
        self.assertEqual(self.api.get(f"/api/branches/{first}/").status_code, 404)
        self.member.role = "specialist"
        self.member.save()
        self.api.force_authenticate(self.admin)
        self.assertEqual(self.api.get(f"/api/branches/{first}/").status_code, 200)
        # Settings is not readable by this role; the tenant viewset conceals the
        # mutation target before the write handler, as for other configuration.
        self.assertEqual(self.api.patch(f"/api/branches/{first}/", {"phone": "123"}).status_code, 404)
        self.assertEqual(Branch.objects.get(pk=first).phone, "")

    def test_audit_failure_rolls_back_branch_and_grants(self):
        with patch("apps.branches.services.write_actor_audit_log", side_effect=RuntimeError("audit failed")):
            self.assertEqual(self.create().status_code, 500)
        self.assertFalse(Branch.objects.exists())
        self.assertFalse(BranchAccess.objects.exists())
        self.create()
        self.assertTrue(AuditLog.objects.filter(metadata__kind="branch").exists())
