from types import SimpleNamespace
from uuid import uuid4

from django.core import mail
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.businesses.models import Business, BusinessInvitation, BusinessMember, BusinessRole, RolePermission
from apps.businesses.serializers import BusinessInvitationSerializer


class InvitationTokenBoundaryTests(TestCase):
    def setUp(self):
        self.api = APIClient()
        self.owner = User.objects.create_user(username="token-owner", email="token-owner@example.invalid")
        self.viewer = User.objects.create_user(username="token-viewer", email="token-viewer@example.invalid")
        self.business = Business.objects.create(owner=self.owner, name="Invitation boundary", slug="invitation-boundary")
        self.role = BusinessRole.objects.create(business=self.business, name="Team read only")
        RolePermission.objects.create(business_role=self.role, resource="team", action="view", scope="business")
        RolePermission.objects.create(business_role=self.role, resource="team", action="manage", scope="none", is_allowed=False)
        self.member = BusinessMember.objects.create(
            business=self.business, user=self.viewer, role=BusinessMember.Roles.OPERATOR, business_role=self.role,
        )
        self.invitation = self.make_invitation("new-admin@example.invalid")
        self.url = f"/api/team/invitations/{self.invitation.pk}/"

    def make_invitation(self, email, **kwargs):
        values = {"business": self.business, "email": email, "role": BusinessMember.Roles.ADMIN,
                  "expires_at": timezone.now() + timezone.timedelta(days=1)}
        values.update(kwargs)
        return BusinessInvitation.objects.create(**values)

    def assert_masked(self, data):
        self.assertEqual((data["token"], data["invite_path"]), ("", ""))

    def test_team_view_list_and_detail_do_not_disclose_bearer(self):
        self.api.force_authenticate(self.viewer)
        listing = self.api.get("/api/team/invitations/")
        detail = self.api.get(self.url)
        self.assertEqual(listing.status_code, 200)
        self.assertEqual(detail.status_code, 200)
        self.assert_masked(listing.data["results"][0])
        self.assert_masked(detail.data)
        self.assertEqual(detail.data["email"], self.invitation.email)

    def test_viewer_cannot_claim_new_admin_account_from_listed_credentials(self):
        self.api.force_authenticate(self.viewer)
        row = self.api.get(self.url).data
        leaked = row.get("token") or row.get("invite_path", "").removeprefix("/invite/")
        accepted = False
        if leaked:
            response = APIClient().post(
                "/api/team/invitations/accept/",
                {"token": leaked, "password": "SyntheticInvitePassword123!"}, format="json",
            )
            accepted = response.status_code == 200
        account = User.objects.filter(email=self.invitation.email).first()
        self.assertEqual(
            (accepted, account is not None,
             bool(account and account.check_password("SyntheticInvitePassword123!")),
             BusinessMember.objects.filter(business=self.business, user=account, role="admin").exists()),
            (False, False, False, False),
        )

    def test_missing_or_anonymous_context_fails_closed(self):
        for context in ({}, {"request": SimpleNamespace(user=None)}):
            with self.subTest(context_present=bool(context)):
                self.assert_masked(BusinessInvitationSerializer(self.invitation, context=context).data)

    def test_read_only_projection_masks_all_invitation_states(self):
        self.api.force_authenticate(self.viewer)
        for field, value in ((None, None), ("accepted_at", timezone.now()),
                             ("revoked_at", timezone.now()), ("expires_at", timezone.now() - timezone.timedelta(days=1))):
            values = {field: value} if field else {}
            invitation = self.make_invitation(f"state-{field or 'pending'}@example.invalid", **values)
            with self.subTest(state=invitation.status):
                response = self.api.get(f"/api/team/invitations/{invitation.pk}/")
                self.assertEqual(response.status_code, 200)
                self.assert_masked(response.data)

    def test_secret_authorization_is_per_business_in_mixed_list(self):
        managed = Business.objects.create(owner=self.viewer, name="Managed", slug="token-managed")
        other = self.make_invitation("other@example.invalid", business=managed)
        self.api.force_authenticate(self.viewer)
        rows = {item["id"]: item for item in self.api.get("/api/team/invitations/").data["results"]}
        self.assert_masked(rows[self.invitation.pk])
        self.assertEqual(rows[other.pk]["token"], str(other.token))
        self.assertEqual(rows[other.pk]["invite_path"], f"/invite/{other.token}")

    def test_team_manage_can_read_share_create_and_revoke(self):
        permission = self.role.permissions.get(resource="team", action="manage")
        permission.is_allowed = True
        permission.scope = "business"
        permission.save()
        self.api.force_authenticate(self.viewer)
        detail = self.api.get(self.url)
        self.assertEqual(detail.status_code, 200)
        self.assertEqual(detail.data["token"], str(self.invitation.token))
        self.assertEqual(detail.data["invite_path"], f"/invite/{self.invitation.token}")
        created = self.api.post("/api/team/invitations/", {
            "business": self.business.pk, "email": "managed-new@example.invalid", "role": "specialist",
            "delivery_channel": "manual",
        }, format="json")
        self.assertEqual(created.status_code, 201)
        self.assertTrue(created.data["token"])
        revoked = self.api.post(f"/api/team/invitations/{created.data['id']}/revoke/")
        self.assertEqual(revoked.status_code, 200)
        self.assertEqual(revoked.data["status"], "revoked")
        self.assertEqual(revoked.data["token"], created.data["token"])
        self.assertEqual(len(mail.outbox), 0)

    def test_demoted_manager_gets_no_secret_on_next_request(self):
        permission = self.role.permissions.get(resource="team", action="manage")
        permission.is_allowed = True
        permission.scope = "business"
        permission.save()
        self.api.force_authenticate(self.viewer)
        self.assertEqual(self.api.get(self.url).data["token"], str(self.invitation.token))
        permission.is_allowed = False
        permission.save()
        self.assert_masked(self.api.get(self.url).data)

    def test_owner_can_create_each_delivery_channel_and_recipient_can_accept(self):
        self.api.force_authenticate(self.owner)
        for channel in ("manual", "email", "whatsapp", "telegram"):
            with self.subTest(channel=channel):
                response = self.api.post("/api/team/invitations/", {
                    "business": self.business.pk, "email": f"recipient-{channel}@example.invalid",
                    "role": "specialist", "delivery_channel": channel,
                    "phone": "+77015550000", "telegram": "synthetic-recipient",
                }, format="json")
                self.assertEqual(response.status_code, 201)
                token = response.data["token"]
                self.assertEqual(response.data["invite_path"], f"/invite/{token}")
                preview = APIClient().get(f"/api/team/invitations/preview/{token}/")
                self.assertEqual(preview.status_code, 200)
                self.assertNotIn("token", preview.data)
                accepted = APIClient().post("/api/team/invitations/accept/", {
                    "token": token, "password": "RecipientPassword123!",
                }, format="json")
                self.assertEqual(accepted.status_code, 200)
        self.assertEqual(len(mail.outbox), 0)

    def test_read_only_actor_cannot_create_or_revoke(self):
        self.api.force_authenticate(self.viewer)
        self.assertEqual(self.api.post("/api/team/invitations/", {
            "business": self.business.pk, "email": "denied@example.invalid", "role": "admin",
        }, format="json").status_code, 403)
        self.assertEqual(self.api.post(f"{self.url}revoke/").status_code, 403)
        self.invitation.refresh_from_db()
        self.assertIsNone(self.invitation.revoked_at)

    def test_rotated_and_inactive_tokens_remain_unusable(self):
        old = self.invitation.token
        self.invitation.token = uuid4()
        self.invitation.save(update_fields=["token"])
        self.assertEqual(APIClient().post("/api/team/invitations/accept/", {
            "token": str(old), "password": "RecipientPassword123!",
        }, format="json").status_code, 400)
        for field, value in (("accepted_at", timezone.now()), ("revoked_at", timezone.now()),
                             ("expires_at", timezone.now() - timezone.timedelta(days=1))):
            invitation = self.make_invitation(f"inactive-{field}@example.invalid", **{field: value})
            self.assertEqual(APIClient().post("/api/team/invitations/accept/", {
                "token": str(invitation.token), "password": "RecipientPassword123!",
            }, format="json").status_code, 400)

    def test_foreign_or_inactive_member_does_not_gain_access(self):
        outsider = User.objects.create_user(username="token-outsider", email="token-outsider@example.invalid")
        self.api.force_authenticate(outsider)
        self.assertEqual(self.api.get(self.url).status_code, 404)
        self.member.is_active = False
        self.member.save(update_fields=["is_active"])
        self.api.force_authenticate(self.viewer)
        self.assertEqual(self.api.get(self.url).status_code, 404)
