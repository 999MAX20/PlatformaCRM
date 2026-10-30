from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.businesses.models import Business, BusinessMember, BusinessRole
from apps.clients.models import Client
from apps.core.models import AuditLog


class BusinessDeleteBoundaryTests(TestCase):
    def setUp(self):
        self.api = APIClient()
        self.owner = User.objects.create_user(username="delete-owner", email="delete-owner@example.invalid")
        self.member_user = User.objects.create_user(username="delete-member", email="delete-member@example.invalid")
        self.business = Business.objects.create(owner=self.owner, name="Delete boundary", slug="delete-boundary")
        self.role = BusinessRole.objects.create(business=self.business, name="No permissions")
        self.member = BusinessMember.objects.create(
            business=self.business, user=self.member_user, role=BusinessMember.Roles.OPERATOR,
            business_role=self.role,
        )
        self.client_record = Client.objects.create(business=self.business, full_name="Synthetic client")
        self.url = f"/api/businesses/{self.business.pk}/"

    def assert_business_preserved(self):
        self.assertTrue(Business.objects.filter(pk=self.business.pk).exists())
        self.assertTrue(BusinessMember.objects.filter(pk=self.member.pk).exists())
        self.assertTrue(Client.objects.filter(pk=self.client_record.pk).exists())

    def test_member_cannot_delete_business_and_cascading_data(self):
        self.api.force_authenticate(self.member_user)
        response = self.api.delete(self.url)
        self.assertEqual(
            (response.status_code,
             Business.objects.filter(pk=self.business.pk).exists(),
             BusinessMember.objects.filter(pk=self.member.pk).exists(),
             Client.objects.filter(pk=self.client_record.pk).exists()),
            (405, True, True, True),
        )
        self.assert_business_preserved()

    def test_hard_delete_flag_and_body_do_not_enable_generic_deletion(self):
        self.api.force_authenticate(self.member_user)
        response = self.api.delete(
            f"{self.url}?hard_delete=true&business={self.business.pk}",
            {"business": self.business.pk, "owner": self.member_user.pk}, format="json",
        )
        self.assertEqual(response.status_code, 405)
        self.assert_business_preserved()

    @override_settings(SUPPORT_REQUIRES_GRANT=False)
    def test_generic_delete_is_not_a_privileged_lifecycle_workflow(self):
        platform_admin = User.objects.create_user(
            username="delete-platform", email="delete-platform@example.invalid", role=User.Roles.PLATFORM_ADMIN,
        )
        admin = User.objects.create_user(username="delete-admin", email="delete-admin@example.invalid")
        BusinessMember.objects.create(business=self.business, user=admin, role=BusinessMember.Roles.ADMIN)
        for actor in (self.owner, admin, platform_admin):
            with self.subTest(actor=actor.username):
                self.api.force_authenticate(actor)
                self.assertEqual(self.api.delete(self.url).status_code, 405)
                self.assert_business_preserved()

    def test_member_can_still_read_but_cannot_update_business(self):
        self.api.force_authenticate(self.member_user)
        self.assertEqual(self.api.get(self.url).status_code, 200)
        self.assertEqual(self.api.patch(self.url, {"name": "Denied"}, format="json").status_code, 403)
        self.business.refresh_from_db()
        self.assertEqual(self.business.name, "Delete boundary")

    def test_owner_can_still_list_retrieve_and_update_with_audit(self):
        self.api.force_authenticate(self.owner)
        self.assertEqual(self.api.get("/api/businesses/").status_code, 200)
        self.assertEqual(self.api.get(self.url).status_code, 200)
        for method, name in ((self.api.patch, "Patched"), (self.api.put, "Replaced")):
            response = method(self.url, {"name": name, "slug": self.business.slug}, format="json")
            self.assertEqual(response.status_code, 200)
            self.business.refresh_from_db()
            self.assertEqual(self.business.name, name)
        self.assertEqual(AuditLog.objects.filter(business=self.business, action=AuditLog.Actions.UPDATE).count(), 2)

    def test_business_creation_still_creates_owner_membership_and_audit(self):
        self.api.force_authenticate(self.owner)
        response = self.api.post("/api/businesses/", {"name": "Created", "slug": "delete-control-created"}, format="json")
        self.assertEqual(response.status_code, 201)
        created = Business.objects.get(pk=response.data["id"])
        self.assertEqual(created.owner_id, self.owner.pk)
        self.assertTrue(created.members.filter(user=self.owner, role=BusinessMember.Roles.OWNER, is_active=True).exists())
        self.assertTrue(AuditLog.objects.filter(business=created, action=AuditLog.Actions.CREATE).exists())

    def test_foreign_tenant_remains_unreadable_and_immutable(self):
        outsider = User.objects.create_user(username="delete-outsider", email="delete-outsider@example.invalid")
        self.api.force_authenticate(outsider)
        self.assertEqual(self.api.get(self.url).status_code, 404)
        self.assertEqual(self.api.patch(self.url, {"name": "Foreign"}, format="json").status_code, 404)
        self.assertEqual(self.api.delete(self.url).status_code, 405)
        self.assert_business_preserved()

    def test_options_does_not_advertise_delete(self):
        self.api.force_authenticate(self.owner)
        response = self.api.options(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertNotIn("DELETE", response["Allow"])
        self.assertEqual(self.api.head(self.url).status_code, 200)
