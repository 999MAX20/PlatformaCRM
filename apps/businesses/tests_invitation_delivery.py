from datetime import timedelta
from unittest.mock import patch

from django.core import mail
from django.db import transaction
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.businesses.models import Business, BusinessInvitation, BusinessMember
from apps.businesses.invitations import deliver_invitation


@override_settings(FRONTEND_URL="https://crm.example.invalid", ENVIRONMENT="test")
class InvitationDeliveryTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(username="mail-owner", email="mail-owner@example.invalid")
        self.business = Business.objects.create(owner=self.owner, name="Pilot business", slug="mail-pilot", language="en")
        self.api = APIClient()
        self.api.force_authenticate(self.owner)
        self.url = "/api/team/invitations/"

    def create(self, **values):
        with self.captureOnCommitCallbacks(execute=True):
            response = self.api.post(self.url, {"business": self.business.pk, "email": "invitee@example.invalid",
                "role": "specialist", "delivery_channel": "email", **values}, format="json")
        self.assertEqual(response.status_code, 201, response.data)
        return BusinessInvitation.objects.get(pk=response.data["id"])

    def resend(self, row, revision=None):
        with self.captureOnCommitCallbacks(execute=True):
            return self.api.post(f"{self.url}{row.pk}/resend/", {"revision": revision or row.updated_at.isoformat()}, format="json")

    def test_email_and_exact_24h_lifetime_no_account_until_acceptance(self):
        now = timezone.now()
        with patch("apps.businesses.invitations.timezone.now", return_value=now):
            row = self.create()
        self.assertEqual(row.expires_at, now + timedelta(hours=24))
        self.assertEqual(row.delivery_status, "accepted")
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, [row.email])
        self.assertIn(f"https://crm.example.invalid/invite/{row.token}", mail.outbox[0].body)
        self.assertIn("24 hours", mail.outbox[0].body)
        self.assertFalse(User.objects.filter(email=row.email).exists())
        with patch("apps.businesses.models.timezone.now", return_value=row.expires_at):
            result = APIClient().post(f"{self.url}accept/", {"token": str(row.token), "password": "PilotRecipient123!"}, format="json")
        self.assertEqual(result.status_code, 400)
        self.assertFalse(User.objects.filter(email=row.email).exists())

    def test_resend_rotates_and_stale_retry_cannot_rotate_twice(self):
        row = self.create()
        old_token = row.token
        row.delivery_attempted_at -= timedelta(seconds=61)
        row.save(update_fields=["delivery_attempted_at"])
        revision = row.updated_at.isoformat()
        response = self.resend(row)
        self.assertEqual(response.status_code, 200, response.data)
        row.refresh_from_db()
        self.assertNotEqual(row.token, old_token)
        self.assertEqual(len(mail.outbox), 2)
        self.assertEqual(self.resend(row, revision).status_code, 409)
        self.assertEqual(self.resend(row).status_code, 429)
        self.assertEqual(len(mail.outbox), 2)
        rejected = APIClient().post(f"{self.url}accept/", {"token": str(old_token), "password": "PilotRecipient123!"}, format="json")
        self.assertEqual(rejected.status_code, 400)

    def test_failure_is_persisted_without_provider_secrets_and_can_be_retried(self):
        with patch("apps.businesses.invitations.send_mail", side_effect=OSError("secret-password-and-token")):
            row = self.create()
        self.assertEqual((row.delivery_status, row.delivery_error), ("failed", "unavailable"))
        response = self.api.get(f"{self.url}{row.pk}/")
        self.assertNotIn("secret-password", str(response.data))
        row.delivery_attempted_at -= timedelta(seconds=61)
        row.save(update_fields=["delivery_attempted_at"])
        self.assertEqual(self.resend(row).status_code, 200)
        row.refresh_from_db()
        self.assertEqual(row.delivery_status, "accepted")

    @override_settings(FRONTEND_URL="")
    def test_missing_configuration_is_not_reported_as_sent(self):
        row = self.create()
        self.assertEqual((row.delivery_status, row.delivery_error), ("failed", "not_configured"))
        self.assertEqual(len(mail.outbox), 0)

    def test_revoked_and_accepted_cannot_be_resent(self):
        row = self.create()
        self.assertEqual(self.api.post(f"{self.url}{row.pk}/revoke/").status_code, 200)
        row.refresh_from_db()
        self.assertEqual(self.resend(row).status_code, 409)
        row2 = self.create(email="second@example.invalid")
        result = APIClient().post(f"{self.url}accept/", {"token": str(row2.token), "password": "PilotRecipient123!"}, format="json")
        self.assertEqual(result.status_code, 200, result.data)
        row2.refresh_from_db()
        self.assertEqual(self.resend(row2).status_code, 409)

    def test_expired_can_be_resent(self):
        row = self.create()
        row.expires_at -= timedelta(days=2)
        row.delivery_attempted_at -= timedelta(days=2)
        row.save()
        self.assertEqual(self.resend(row).status_code, 200)
        row.refresh_from_db()
        self.assertEqual(row.status, "pending")

    def test_foreign_actor_and_readonly_member_cannot_resend(self):
        row = self.create()
        outsider = User.objects.create_user(username="mail-outsider")
        self.api.force_authenticate(outsider)
        self.assertEqual(self.resend(row).status_code, 404)
        BusinessMember.objects.create(business=self.business, user=outsider, role="specialist")
        self.assertIn(self.resend(row).status_code, [403, 404])

    def test_rollbacks_and_revoked_queued_links_do_not_send(self):
        with patch("apps.businesses.invitations.write_audit_log", side_effect=RuntimeError("audit failed")):
            with self.captureOnCommitCallbacks(execute=True):
                response = self.api.post(self.url, {"business": self.business.pk, "email": "rollback@example.invalid",
                    "role": "specialist", "delivery_channel": "email"}, format="json")
                self.assertEqual(response.status_code, 500)
        self.assertFalse(BusinessInvitation.objects.exists())
        row = self.create(delivery_channel="manual")
        row.delivery_status = "pending"
        row.revoked_at = timezone.now()
        row.save()
        deliver_invitation(row.pk, row.token, None)
        self.assertEqual(len(mail.outbox), 0)

    def test_invalid_uuid_and_generic_mutations_are_rejected(self):
        row = self.create()
        self.assertEqual(APIClient().get(f"{self.url}preview/not-a-uuid/").status_code, 400)
        self.assertEqual(self.api.patch(f"{self.url}{row.pk}/", {"email": "other@example.invalid"}).status_code, 405)
        self.assertEqual(self.api.delete(f"{self.url}{row.pk}/").status_code, 405)
