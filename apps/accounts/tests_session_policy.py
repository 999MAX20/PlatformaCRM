from datetime import timedelta

from django.core.cache import cache
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from apps.accounts.models import AccountSession, User


@override_settings(AUTH_DEVICE_SESSIONS_ENABLED=True, AUTH_PRIVILEGED_MFA_REQUIRED=False,
                   AUTH_SESSION_IDLE_DAYS=7, AUTH_SESSION_ABSOLUTE_DAYS=30)
class PersistentSessionTests(TestCase):
    def setUp(self):
        cache.clear()
        self.user = User.objects.create_user(username="persistent", email="persistent@example.invalid", password="StrongPass123!")

    def login(self):
        client = APIClient()
        response = client.post("/api/auth/token/", {"email": self.user.email, "password": "StrongPass123!"})
        self.assertEqual(response.status_code, 200, response.data)
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {response.data['access']}")
        raw = response.cookies["zani_refresh"].value
        session = AccountSession.objects.get(pk=RefreshToken(raw)["sid"])
        return client, raw, session

    def test_background_reads_and_refresh_do_not_extend_idle_deadline(self):
        client, _, session = self.login()
        last_seen = timezone.now() - timedelta(days=6)
        deadline = last_seen + timedelta(days=7)
        AccountSession.objects.filter(pk=session.pk).update(last_seen_at=last_seen, expires_at=deadline)
        self.assertEqual(client.get("/api/auth/me/").status_code, 200)
        client.credentials()
        response = client.post("/api/auth/token/refresh/", {})
        self.assertEqual(response.status_code, 200, response.data)
        session.refresh_from_db()
        self.assertEqual(session.last_seen_at, last_seen)
        self.assertEqual(int(session.expires_at.timestamp()), int(deadline.timestamp()))
        self.assertEqual(RefreshToken(response.cookies["zani_refresh"].value)["exp"], int(deadline.timestamp()))
        self.assertLessEqual(response.cookies["zani_refresh"]["max-age"], 24 * 3600)

    def test_foreground_activity_renews_idle_but_not_absolute_deadline(self):
        client, _, session = self.login()
        created = timezone.now() - timedelta(days=29)
        old_seen = timezone.now() - timedelta(days=6)
        AccountSession.objects.filter(pk=session.pk).update(created_at=created, last_seen_at=old_seen)
        client.credentials()
        response = client.post("/api/auth/token/refresh/", {"activity": True}, format="json")
        self.assertEqual(response.status_code, 200, response.data)
        session.refresh_from_db()
        self.assertGreater(session.last_seen_at, old_seen)
        self.assertEqual(int(session.expires_at.timestamp()), int((created + timedelta(days=30)).timestamp()))
        self.assertEqual(APIClient().post("/api/auth/token/refresh/", {"activity": True}, format="json").status_code, 400)

    def test_idle_and_absolute_limits_block_access_refresh_and_activity(self):
        for boundary in ("idle", "absolute"):
            with self.subTest(boundary=boundary):
                client, _, session = self.login()
                now = timezone.now()
                AccountSession.objects.filter(pk=session.pk).update(
                    created_at=now-timedelta(days=30) if boundary == "absolute" else now-timedelta(days=8),
                    last_seen_at=now if boundary == "absolute" else now-timedelta(days=7),
                    expires_at=now+timedelta(days=7),
                )
                self.assertEqual(client.get("/api/auth/me/").status_code, 401)
                self.assertEqual(client.post("/api/auth/token/refresh/", {"activity": True}, format="json").status_code, 401)
                client.credentials()
                self.assertEqual(client.post("/api/auth/token/refresh/", {}).status_code, 401)

    def test_a_workday_break_and_browser_restore_keep_the_session(self):
        client, _, session = self.login()
        AccountSession.objects.filter(pk=session.pk).update(last_seen_at=timezone.now()-timedelta(hours=8))
        client.credentials()
        response = client.post("/api/auth/token/refresh/", {})
        self.assertEqual(response.status_code, 200)
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {response.data['access']}")
        client.credentials()
        self.assertEqual(client.post("/api/auth/token/refresh/", {"activity": True}, format="json").status_code, 200)

    def test_logout_revokes_only_current_device_and_is_immediate(self):
        first, _, first_session = self.login()
        second, _, _ = self.login()
        self.assertEqual(first.post("/api/auth/logout/", {}).status_code, 200)
        first_session.refresh_from_db()
        self.assertIsNotNone(first_session.revoked_at)
        self.assertEqual(first.get("/api/auth/me/").status_code, 401)
        self.assertEqual(second.get("/api/auth/me/").status_code, 200)
        second.credentials()
        self.assertEqual(second.post("/api/auth/token/refresh/", {}).status_code, 200)

    def test_rejected_old_refresh_cannot_erase_a_new_cookie(self):
        client, old, _ = self.login()
        client.credentials()
        first = client.post("/api/auth/token/refresh/", {})
        self.assertEqual(first.status_code, 200)
        second = client.post("/api/auth/token/refresh/", {"refresh": old})
        self.assertEqual(second.status_code, 401)
        self.assertNotIn("zani_refresh", second.cookies)
        self.assertEqual(client.post("/api/auth/token/refresh/", {}).status_code, 200)

    def test_legacy_adoption_preserves_original_absolute_login_time(self):
        refresh = RefreshToken.for_user(self.user)
        refresh["auth_epoch"] = self.user.auth_epoch
        refresh["auth_time"] = int((timezone.now() - timedelta(days=29)).timestamp())
        client = APIClient()
        response = client.post("/api/auth/token/refresh/", {"refresh": str(refresh), "activity": True}, format="json")
        self.assertEqual(response.status_code, 200, response.data)
        adopted = RefreshToken(response.cookies["zani_refresh"].value)
        self.assertEqual(adopted["exp"], refresh["auth_time"] + 30 * 86400)
        session = AccountSession.objects.get(pk=adopted["sid"])
        self.assertEqual(int(session.created_at.timestamp()), refresh["auth_time"])

    def test_legacy_adoption_cannot_revive_an_expired_absolute_session(self):
        refresh = RefreshToken.for_user(self.user)
        refresh["auth_epoch"] = self.user.auth_epoch
        refresh["auth_time"] = int((timezone.now() - timedelta(days=31)).timestamp())
        response = APIClient().post("/api/auth/token/refresh/", {"refresh": str(refresh), "activity": True}, format="json")
        self.assertEqual(response.status_code, 401)
        self.assertNotIn("zani_refresh", response.cookies)

    def test_deactivated_account_cannot_renew_foreground_activity(self):
        client, _, session = self.login()
        User.objects.filter(pk=self.user.pk).update(is_active=False)
        client.credentials()
        response = client.post("/api/auth/token/refresh/", {"activity": True}, format="json")
        self.assertEqual(response.status_code, 401)
        session.refresh_from_db()
        self.assertIsNone(session.revoked_at)
