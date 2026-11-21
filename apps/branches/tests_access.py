from unittest.mock import patch

from django.test import TestCase
from django.utils import timezone
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

    def capabilities(self, member=None):
        return self.api.get("/api/branches/member-access/", {"member": (member or self.member).pk})

    def test_grant_capabilities_match_limited_admin_write_scope(self):
        first = self.create().data["id"]
        second = self.create("Second").data["id"]
        self.api.force_authenticate(self.admin)
        response = self.capabilities()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data, {"can_edit": True, "can_grant_all": False, "branch_ids": [first], "reason": ""})
        payload = {"member": self.member.pk, "branch_ids": [first], "all_branches": False}
        self.assertEqual(self.api.post("/api/branches/member-access/", payload, format="json").status_code, 200)
        before = AuditLog.objects.count()
        self.assertEqual(self.api.post("/api/branches/member-access/", {**payload, "branch_ids": [second]}, format="json").status_code, 400)
        self.assertEqual(AuditLog.objects.count(), before)
        self.assertEqual(list(BranchAccess.objects.get(member=self.member).branches.values_list("pk", flat=True)), [first])

    def test_capabilities_refuse_changes_to_existing_outside_grant(self):
        first = self.create().data["id"]
        second = self.create("Second").data["id"]
        user = User.objects.create_user(username="grant-target", email="grant-target@example.test")
        target = BusinessMember.objects.create(business=self.business, user=user, role="operator")
        grant = BranchAccess.objects.create(member=target)
        grant.branches.set([second])
        self.api.force_authenticate(self.admin)
        response = self.capabilities(target)
        self.assertFalse(response.data["can_edit"])
        self.assertEqual(response.data["reason"], "outside_branch_scope")
        self.assertEqual(self.api.post("/api/branches/member-access/", {"member": target.pk, "branch_ids": [first]}, format="json").status_code, 400)
        self.assertEqual(list(grant.branches.values_list("pk", flat=True)), [second])
        Branch.objects.filter(pk=second).update(is_active=False, archived_at=timezone.now())
        self.assertFalse(self.capabilities(target).data["can_edit"])
        self.assertEqual(self.api.post("/api/branches/member-access/", {"member": target.pk, "branch_ids": []}, format="json").status_code, 400)

    def test_owner_and_network_admin_can_grant_future_branches(self):
        self.create()
        self.assertTrue(self.capabilities().data["can_grant_all"])
        grant = BranchAccess.objects.get(member=self.member)
        grant.all_branches = True
        grant.save()
        self.api.force_authenticate(self.admin)
        self.assertTrue(self.capabilities().data["can_grant_all"])
        response = self.api.post("/api/branches/member-access/", {"member": self.member.pk, "branch_ids": [], "all_branches": True}, format="json")
        self.assertEqual(response.status_code, 200)

    def test_owner_target_and_foreign_member_capabilities_are_safe(self):
        self.create()
        owner_member = BusinessMember.objects.create(business=self.business, user=self.owner, role="owner")
        response = self.capabilities(owner_member)
        self.assertFalse(response.data["can_edit"])
        self.assertEqual(response.data["reason"], "owner_access")
        other = Business.objects.create(owner=self.owner, name="Other", slug="grant-other")
        foreign = BusinessMember.objects.create(business=other, user=self.owner, role="owner")
        self.api.force_authenticate(self.admin)
        self.assertEqual(self.capabilities(foreign).status_code, 404)
        self.member.role = "operator"
        self.member.save()
        self.assertEqual(self.capabilities().status_code, 403)
        self.assertEqual(self.api.get("/api/branches/member-access/").status_code, 400)
        self.assertEqual(self.api.get("/api/branches/member-access/", {"member": "9" * 30}).status_code, 400)

    def test_failed_grant_audit_rolls_back_selection(self):
        first = self.create().data["id"]
        with patch("apps.branches.services.write_actor_audit_log", side_effect=RuntimeError("synthetic audit failure")):
            response = self.api.post("/api/branches/member-access/", {"member": self.member.pk, "branch_ids": []}, format="json")
        self.assertEqual(response.status_code, 500)
        self.assertEqual(list(BranchAccess.objects.get(member=self.member).branches.values_list("pk", flat=True)), [first])
