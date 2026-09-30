from datetime import timedelta
from unittest.mock import patch
from uuid import uuid4

from django.core.cache import cache
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from apps.accounts.models import AccountSession, User
from apps.core.models import AuditLog


@override_settings(AUTH_DEVICE_SESSIONS_ENABLED=True, AUTH_PRIVILEGED_MFA_REQUIRED=False)
class DeviceSessionTests(TestCase):
    password = "StrongPass123!"

    def setUp(self):
        cache.clear()
        self.user = User.objects.create_user(username="devices", email="devices@example.com", password=self.password)
        self.other = User.objects.create_user(username="foreign-device", email="foreign@example.com", password=self.password)

    def login(self, user=None, agent="Mozilla/5.0 Windows Chrome/130.0"):
        client = APIClient()
        response = client.post("/api/auth/token/", {"email": (user or self.user).email, "password": self.password}, HTTP_USER_AGENT=agent, REMOTE_ADDR="192.0.2.10")
        self.assertEqual(response.status_code, 200, response.data)
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {response.data['access']}")
        raw = response.cookies["zani_refresh"].value
        return client, raw, RefreshToken(raw)["sid"]

    def revoke(self, client, sid, **data):
        return client.post(f"/api/auth/sessions/{sid}/revoke/", data)

    def test_list_is_private_current_and_contains_no_credentials(self):
        client, raw, sid = self.login()
        self.login(agent="Mozilla/5.0 iPhone Safari/604.1")
        self.login(self.other)
        response = client.get("/api/auth/sessions/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data["sessions"]), 2)
        current = [item for item in response.data["sessions"] if item["is_current"]]
        self.assertEqual([item["id"] for item in current], [sid])
        self.assertEqual(current[0]["ip_address"], "192.0.2.10")
        self.assertEqual(response.data["legacy_count"], 0)
        self.assertNotIn(raw, str(response.data))
        self.assertNotIn("refresh_jti", str(response.data))
        self.assertIn("no-store", response["Cache-Control"])
        self.assertEqual(APIClient().get("/api/auth/sessions/").status_code, 401)

    def test_remote_revoke_blocks_access_and_refresh_only_for_target(self):
        first, _, _ = self.login()
        second, raw, sid = self.login()
        third, _, _ = self.login()
        response = self.revoke(first, sid)
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(second.get("/api/auth/me/").status_code, 401)
        second.credentials()
        self.assertEqual(second.post("/api/auth/token/refresh/", {"refresh": raw}).status_code, 401)
        self.assertEqual(first.get("/api/auth/me/").status_code, 200)
        self.assertEqual(third.get("/api/auth/me/").status_code, 200)
        self.assertEqual(self.revoke(first, sid).status_code, 200)
        self.assertEqual(AuditLog.objects.filter(metadata__event="device_session_revoked").count(), 1)

    def test_foreign_and_unknown_ids_have_same_denial_current_is_protected(self):
        client, _, current = self.login()
        _, _, foreign = self.login(self.other)
        self.assertEqual(self.revoke(client, foreign).status_code, 404)
        self.assertEqual(self.revoke(client, uuid4()).status_code, 404)
        self.assertEqual(self.revoke(client, current).status_code, 400)
        self.assertEqual(client.get("/api/auth/me/").status_code, 200)

    def test_rotation_keeps_session_id_and_revocation_closes_rotated_token(self):
        first, _, _ = self.login()
        second, old_raw, sid = self.login()
        second.credentials()
        response = second.post("/api/auth/token/refresh/", {})
        self.assertEqual(response.status_code, 200)
        raw = response.cookies["zani_refresh"].value
        self.assertEqual(RefreshToken(raw)["sid"], sid)
        self.assertNotEqual(raw, old_raw)
        self.assertEqual(AccountSession.objects.count(), 2)
        second.credentials(HTTP_AUTHORIZATION=f"Bearer {response.data['access']}")
        self.assertEqual(second.get("/api/auth/me/").status_code, 200)
        self.assertEqual(self.revoke(first, sid).status_code, 200)
        self.assertEqual(second.get("/api/auth/me/").status_code, 401)
        second.credentials()
        self.assertEqual(second.post("/api/auth/token/refresh/", {"refresh": raw}).status_code, 401)

    def test_legacy_refresh_is_adopted_without_inventing_old_device_details(self):
        token = RefreshToken.for_user(self.user)
        token["auth_epoch"] = self.user.auth_epoch
        token["mfa_verified"] = False
        client = APIClient(); client.credentials(HTTP_AUTHORIZATION=f"Bearer {token.access_token}")
        before = client.get("/api/auth/sessions/").data
        self.assertEqual(before["legacy_count"], 1)
        self.assertEqual(before["sessions"], [])
        client.credentials()
        response = client.post("/api/auth/token/refresh/", {"refresh": str(token)}, HTTP_USER_AGENT="Firefox/130.0 Linux")
        self.assertEqual(response.status_code, 200, response.data)
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {response.data['access']}")
        after = client.get("/api/auth/sessions/").data
        self.assertEqual(after["legacy_count"], 0)
        self.assertTrue(after["sessions"][0]["is_current"])
        self.assertEqual(after["sessions"][0]["user_agent"], "Firefox/130.0 Linux")

    def test_global_revoke_keeps_replacement_and_rejects_other_devices(self):
        first, _, _ = self.login()
        second, _, _ = self.login()
        response = first.post("/api/auth/mfa/sessions/revoke/", {})
        self.assertEqual(response.status_code, 200)
        first.credentials(HTTP_AUTHORIZATION=f"Bearer {response.data['access']}")
        self.assertEqual(first.get("/api/auth/me/").status_code, 200)
        self.assertEqual(second.get("/api/auth/me/").status_code, 401)
        self.assertEqual(len(first.get("/api/auth/sessions/").data["sessions"]), 1)

    def test_expired_session_rejected_and_missing_or_foreign_sid_rejected(self):
        client, raw, sid = self.login()
        AccountSession.objects.filter(pk=sid).update(expires_at=timezone.now()-timedelta(seconds=1))
        self.assertEqual(client.get("/api/auth/me/").status_code, 401)
        client.credentials()
        self.assertEqual(client.post("/api/auth/token/refresh/", {"refresh": raw}).status_code, 401)
        _, valid, _ = self.login()
        token = RefreshToken(valid)
        for invalid in (str(uuid4()), "not-a-uuid"):
            token["sid"] = invalid
            client.credentials(HTTP_AUTHORIZATION=f"Bearer {token.access_token}")
            self.assertEqual(client.get("/api/auth/me/").status_code, 401)

    def test_mfa_factor_required_for_selective_revocation(self):
        first, _, _ = self.login()
        _, _, sid = self.login()
        with patch("apps.accounts.mfa.has_confirmed_mfa", return_value=True), patch("apps.accounts.mfa.verify_user_factor", return_value=False) as factor:
            self.assertEqual(self.revoke(first, sid).status_code, 400)
            self.assertIsNone(AccountSession.objects.get(pk=sid).revoked_at)
            factor.return_value = True
            self.assertEqual(self.revoke(first, sid, code="123456").status_code, 200)

    def test_disabling_rollout_does_not_bypass_existing_sid_revocation(self):
        first, _, _ = self.login()
        second, _, sid = self.login()
        self.assertEqual(self.revoke(first, sid).status_code, 200)
        with override_settings(AUTH_DEVICE_SESSIONS_ENABLED=False):
            self.assertEqual(second.get("/api/auth/me/").status_code, 401)
            self.assertFalse(first.get("/api/auth/sessions/").data["available"])
