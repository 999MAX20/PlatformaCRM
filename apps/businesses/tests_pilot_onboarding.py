"""Synthetic two-business acceptance through public auth and team APIs."""
from django.core.cache import cache
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.businesses.models import Business, BusinessInvitation, BusinessMember, BusinessRole
from apps.clients.models import Client
from apps.scheduling.models import Resource
from apps.tasks.models import Task


@override_settings(AUTH_PRIVILEGED_MFA_REQUIRED=False)
class TwoBusinessOnboardingTests(TestCase):
    password = "SyntheticPilotAccess123!"

    def setUp(self):
        cache.clear()
        self.owner_a, self.a = self.signup("pilot-owner-a@example.invalid", "Pilot A")
        self.owner_b, self.b = self.signup("pilot-owner-b@example.invalid", "Pilot B")

    def cookie_post(self, api, path, data):
        bootstrap = api.get("/api/auth/csrf/")
        self.assertEqual(bootstrap.status_code, 200)
        return api.post(path, data, format="json", HTTP_X_CSRFTOKEN=bootstrap.json()["csrf_token"], HTTP_ORIGIN="http://testserver")

    def signup(self, email, name):
        api = APIClient(enforce_csrf_checks=True)
        response = self.cookie_post(api, "/api/auth/signup/owner/", {
            "email": email, "password": self.password, "business_name": name,
            "accepted_documents": ["terms", "privacy", "personal-data", "company-data"],
        })
        self.assertEqual(response.status_code, 201, response.data)
        api.credentials(HTTP_AUTHORIZATION=f"Bearer {response.data['access']}")
        business = Business.objects.get(owner__email=email)
        self.assertTrue(business.members.filter(user=business.owner, role="owner", is_active=True).exists())
        self.assertTrue(business.roles.filter(preset_key="specialist", is_active=True).exists())
        return api, business

    def login(self, email):
        api = APIClient(enforce_csrf_checks=True)
        response = self.cookie_post(api, "/api/auth/token/", {"email": email, "password": self.password})
        self.assertEqual(response.status_code, 200, response.data)
        api.credentials(HTTP_AUTHORIZATION=f"Bearer {response.data['access']}")
        return api

    def invite(self, api, business, email, role="admin"):
        response = api.post("/api/team/invitations/", {
            "business": business.pk, "email": email, "role": role, "delivery_channel": "manual",
        }, format="json")
        self.assertEqual(response.status_code, 201, response.data)
        return response.data

    def accept_new(self, invitation):
        api = APIClient(enforce_csrf_checks=True)
        response = api.post("/api/team/invitations/accept/", {"token": invitation["token"], "password": self.password}, format="json")
        self.assertEqual(response.status_code, 200, response.data)
        return self.login(invitation["email"])

    def test_two_owners_invited_admin_and_revocation_preserve_other_business_and_work(self):
        invitation = self.invite(self.owner_a, self.a, "pilot-admin@example.invalid")
        staff_api = self.accept_new(invitation)
        staff = User.objects.get(email=invitation["email"])
        member = self.a.members.get(user=staff)
        own = Client.objects.create(business=self.a, full_name="Pilot A synthetic client")
        foreign = Client.objects.create(business=self.b, full_name="Pilot B synthetic client")
        specialist = Resource.objects.create(business=self.a, name="Synthetic specialist", linked_user=staff)
        work = Task.objects.create(business=self.a, title="Retained assignment", assignee=staff)
        self.assertEqual(staff_api.get(f"/api/clients/{own.pk}/").status_code, 200)
        self.assertEqual(staff_api.get(f"/api/clients/{foreign.pk}/").status_code, 404)
        self.assertEqual(self.owner_b.get(f"/api/team/members/{member.pk}/").status_code, 404)
        self.assertEqual(self.owner_b.patch(f"/api/team/members/{member.pk}/", {"is_active": False}, format="json").status_code, 404)
        # The same account may join a second business only by accepting its invitation.
        second = self.invite(self.owner_b, self.b, staff.email)
        self.assertEqual(staff_api.post("/api/team/invitations/accept/", {"token": second["token"]}, format="json").status_code, 200)
        self.assertEqual(staff_api.get(f"/api/clients/{foreign.pk}/").status_code, 200)
        for active, expected in [(False, 404), (True, 200)]:
            response = self.owner_a.patch(f"/api/team/members/{member.pk}/", {"is_active": active}, format="json")
            self.assertEqual(response.status_code, 200, response.data)
            self.assertEqual(staff_api.get(f"/api/clients/{own.pk}/").status_code, expected)
            self.assertEqual(staff_api.get(f"/api/clients/{foreign.pk}/").status_code, 200)
            staff.refresh_from_db(); specialist.refresh_from_db(); work.refresh_from_db()
            self.assertTrue(staff.is_active)
            self.assertEqual(specialist.linked_user_id, staff.pk)
            self.assertEqual(work.assignee_id, staff.pk)
        # Current role applies to the already-issued token, without a new login.
        role = BusinessRole.objects.get(business=self.a, preset_key="specialist")
        response = self.owner_a.patch(f"/api/team/members/{member.pk}/", {"role": "specialist", "business_role": role.pk}, format="json")
        self.assertEqual(response.status_code, 200, response.data)
        denied = staff_api.post("/api/team/invitations/", {"business": self.a.pk, "email": "forbidden@example.invalid", "role": "admin"}, format="json")
        self.assertEqual(denied.status_code, 403, denied.data)

    def test_existing_account_cannot_be_claimed_by_wrong_account_or_token_replay(self):
        invitation = self.invite(self.owner_a, self.a, self.b.owner.email, "operator")
        before = self.b.owner.password
        anon = APIClient()
        self.assertEqual(anon.post("/api/team/invitations/accept/", {"token": invitation["token"], "password": self.password}, format="json").status_code, 401)
        self.assertEqual(self.owner_a.post("/api/team/invitations/accept/", {"token": invitation["token"]}, format="json").status_code, 403)
        accepted = self.owner_b.post("/api/team/invitations/accept/", {"token": invitation["token"]}, format="json")
        self.assertEqual(accepted.status_code, 200, accepted.data)
        self.assertEqual(self.owner_b.post("/api/team/invitations/accept/", {"token": invitation["token"]}, format="json").status_code, 400)
        self.b.owner.refresh_from_db()
        self.assertEqual(self.b.owner.password, before)
        self.assertEqual(self.a.members.filter(user=self.b.owner).count(), 1)

    def test_expired_revoked_and_foreign_role_invitations_cannot_create_access(self):
        api = APIClient()
        for reason in ["expired", "revoked"]:
            row = self.invite(self.owner_a, self.a, f"{reason}@example.invalid", "operator")
            if reason == "expired":
                BusinessInvitation.objects.filter(pk=row["id"]).update(expires_at=timezone.now()-timezone.timedelta(seconds=1))
            else:
                self.assertEqual(self.owner_a.post(f"/api/team/invitations/{row['id']}/revoke/", {}).status_code, 200)
            result = api.post("/api/team/invitations/accept/", {"token": row["token"], "password": self.password}, format="json")
            self.assertEqual(result.status_code, 400, result.data)
            self.assertFalse(User.objects.filter(email=row["email"]).exists())
        result = self.owner_a.post("/api/team/invitations/", {
            "business": self.a.pk, "email": "foreign-role@example.invalid", "role": "admin",
            "business_role": self.b.roles.get(preset_key="admin").pk,
        }, format="json")
        self.assertEqual(result.status_code, 400, result.data)
        self.assertFalse(BusinessMember.objects.filter(business=self.a, user__email="foreign-role@example.invalid").exists())
