from django.test import TestCase
from rest_framework.test import APIClient
from django.utils import timezone

from apps.accounts.models import User
from apps.businesses.models import Business, BusinessInvitation, BusinessMember


class RevokedBusinessAccessTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(username="access-owner", email="owner@example.test")
        self.employee = User.objects.create_user(username="access-employee", email="employee@example.test")
        self.business = Business.objects.create(owner=self.owner, name="Access business", slug="access-business")
        self.member = BusinessMember.objects.create(
            business=self.business, user=self.employee, role="operator", is_active=False
        )
        self.api = APIClient()
        self.api.force_authenticate(self.employee)

    def profile(self):
        response = self.api.get("/api/auth/me/")
        self.assertEqual(response.status_code, 200)
        return response.data

    def test_revoked_employee_has_explicit_state_without_business_data(self):
        profile = self.profile()
        self.assertIs(profile["business_access_revoked"], True)
        self.assertEqual(profile["businesses"], [])
        self.assertEqual(profile["memberships"], [])
        self.assertEqual(profile["effective_permissions"], {})
        self.assertEqual(self.api.get(f"/api/businesses/{self.business.pk}/").status_code, 404)

    def test_new_user_is_not_mistaken_for_revoked_employee(self):
        newcomer = User.objects.create_user(username="newcomer", email="new@example.test")
        self.api.force_authenticate(newcomer)
        self.assertIs(self.profile()["business_access_revoked"], False)

    def test_removed_invited_employee_keeps_no_access_state(self):
        BusinessInvitation.objects.create(business=self.business, email=self.employee.email, role="operator",
            accepted_at=timezone.now(), expires_at=timezone.now())
        self.member.delete()
        profile = self.profile()
        self.assertIs(profile["business_access_revoked"], True)
        self.assertEqual(profile["businesses"], [])
        self.assertEqual(profile["memberships"], [])

    def test_reenabled_employee_returns_to_accessible_business(self):
        self.member.is_active = True
        self.member.save(update_fields=["is_active"])
        profile = self.profile()
        self.assertIs(profile["business_access_revoked"], False)
        self.assertEqual([b["id"] for b in profile["businesses"]], [self.business.pk])

    def test_other_active_membership_is_preserved(self):
        other = Business.objects.create(owner=self.owner, name="Other business", slug="other-access")
        BusinessMember.objects.create(business=other, user=self.employee, role="operator")
        profile = self.profile()
        self.assertIs(profile["business_access_revoked"], False)
        self.assertEqual([b["id"] for b in profile["businesses"]], [other.pk])

    def test_owner_is_not_blocked_by_an_inactive_membership(self):
        BusinessMember.objects.create(business=self.business, user=self.owner, role="owner", is_active=False)
        self.api.force_authenticate(self.owner)
        self.assertIs(self.profile()["business_access_revoked"], False)
