from datetime import timedelta
from types import SimpleNamespace
from unittest.mock import patch
from unittest import skipUnless
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
import secrets

import jwt
import pyotp
from cryptography.hazmat.primitives.asymmetric import rsa
from django.conf import settings
from django.core.cache import cache
from django.db import IntegrityError, connection, connections, close_old_connections
from django.test import TestCase, TransactionTestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounts.google_auth import BROWSER_COOKIE, COOKIE, _hash
from apps.accounts.models import GoogleAuthFlow, MfaDevice, SocialIdentity, User
from apps.accounts.mfa import issue_session
from apps.businesses.models import Business, BusinessMember
from apps.core.models import AuditLog
from apps.integrations.credential_encryption import encrypt_credential_value


@override_settings(GOOGLE_OAUTH_CLIENT_IDS=["synthetic-client"], AUTH_PRIVILEGED_MFA_REQUIRED=False)
class GoogleAuthTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.key = rsa.generate_private_key(public_exponent=65537, key_size=2048)

    def setUp(self):
        cache.clear()
        self.client = APIClient(enforce_csrf_checks=True)
        self.headers = self.bootstrap(self.client)
        self.jwks = patch("apps.accounts.social_auth.PyJWKClient")
        self.jwks.start().return_value.get_signing_key_from_jwt.return_value = SimpleNamespace(key=self.key.public_key())
        self.addCleanup(self.jwks.stop)

    def bootstrap(self, client):
        response = client.get("/api/auth/csrf/")
        return {"HTTP_X_CSRFTOKEN": response.json()["csrf_token"], "HTTP_ORIGIN": "http://testserver"}

    def post(self, action, data=None, client=None, headers=None):
        return (client or self.client).post(f"/api/auth/google/{action}/", data or {}, format="json", **(headers or self.headers))

    def start(self):
        response = self.post("start")
        self.assertEqual(response.status_code, 200, response.data)
        self.assertTrue(response.cookies[COOKIE]["httponly"])
        self.assertEqual(response.cookies[COOKIE]["samesite"], "Lax")
        self.assertEqual(response["Cache-Control"], "no-store")
        return response.data["nonce"]

    def token(self, expected_nonce, **overrides):
        now = int(timezone.now().timestamp())
        claims = {"iss": "https://accounts.google.com", "aud": "synthetic-client", "sub": "google-subject",
                  "iat": now, "exp": now + 300, "nonce": expected_nonce, "email": "google@example.test", "email_verified": True, "name": "Synthetic Google"}
        claims.update(overrides)
        return jwt.encode(claims, self.key, algorithm="RS256")

    def verify(self, **claims):
        return self.post("verify", {"id_token": self.token(self.start(), **claims)})

    def signup_data(self):
        return {"business_name": "Synthetic workspace", "business_type": "beauty", "city": "Almaty",
                "accepted_documents": ["terms", "privacy", "personal-data", "company-data"]}

    def user(self, email="google@example.test", **kwargs):
        return User.objects.create_user(username=email, email=email, password="ExistingSynthetic123", role="business_operator", **kwargs)

    def authenticate(self, user, *, mfa=False, stale=False):
        refresh = issue_session(user, mfa_verified=mfa)
        if stale:
            refresh["auth_time"] = int((timezone.now() - timedelta(minutes=20)).timestamp())
        self.client.credentials(HTTP_AUTHORIZATION="Bearer " + str(refresh.access_token))

    def tab_start(self, client=None, **extra):
        response = self.post("start", {"flow_scope": "tab", **extra}, client=client)
        self.assertEqual(response.status_code, 200, response.data)
        self.assertTrue(response.cookies[BROWSER_COOKIE]["httponly"])
        self.assertNotIn(COOKIE, response.cookies)
        return response.data

    def tab_verify(self, flow, client=None):
        return self.post("verify", {"flow_id": flow["flow_id"], "id_token": self.token(flow["nonce"])}, client=client)

    def test_two_tabs_keep_independent_callbacks_and_shared_binding_after_finish(self):
        first = self.tab_start()
        binding = self.client.cookies[BROWSER_COOKIE].value
        second_tab = APIClient(enforce_csrf_checks=True)
        second_tab.cookies = self.client.cookies
        second = self.tab_start(second_tab)
        self.assertEqual(second_tab.cookies[BROWSER_COOKIE].value, binding)
        self.assertNotEqual(first["flow_id"], second["flow_id"])
        self.assertEqual(self.tab_verify(first).status_code, 200)
        self.assertEqual(self.tab_verify(second, second_tab).status_code, 200)
        response = self.post("signup", {**self.signup_data(), "flow_id": first["flow_id"]})
        self.assertEqual(response.status_code, 201, response.data)
        self.assertNotIn(BROWSER_COOKIE, response.cookies)
        self.assertEqual(second_tab.get("/api/auth/google/flow/", {"flow_id": second["flow_id"]}).status_code, 200)
        self.assertEqual(self.post("signup", {**self.signup_data(), "flow_id": second["flow_id"]}, client=second_tab).status_code, 409)
        self.assertEqual((User.objects.count(), Business.objects.count(), SocialIdentity.objects.count()), (1, 1, 1))

    def test_verified_tab_survives_cloned_selector_restart_and_legacy_tab(self):
        first = self.tab_start()
        self.assertEqual(self.tab_verify(first).status_code, 200)
        self.tab_start(flow_id=first["flow_id"])
        self.start()
        response = self.client.get("/api/auth/google/flow/", {"flow_id": first["flow_id"]})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["code"], "google_signup_required")
        self.assertEqual(self.post("signup", {**self.signup_data(), "flow_id": first["flow_id"]}).status_code, 201)

    def test_tab_selector_requires_its_browser_and_does_not_fallback_to_legacy(self):
        first = self.tab_start()
        other = APIClient(enforce_csrf_checks=True)
        headers = self.bootstrap(other)
        self.assertEqual(self.post("verify", {"flow_id": first["flow_id"], "id_token": self.token(first["nonce"])}, other, headers).status_code, 400)
        self.assertEqual(self.post("start", {"flow_scope": "tab"}, other, headers).status_code, 200)
        self.assertEqual(self.post("verify", {"flow_id": first["flow_id"], "id_token": self.token(first["nonce"])}, other, headers).status_code, 400)
        nonce = self.start()
        self.assertEqual(self.post("verify", {"id_token": self.token(nonce), "flow_id": "malformed"}).status_code, 400)
        self.assertEqual(self.post("verify", {"id_token": self.token(nonce)}).status_code, 200)
        self.assertEqual(self.tab_verify(first).status_code, 200)

    def test_tab_expiry_replay_and_failure_limit_remain_enforced(self):
        first = self.tab_start()
        self.assertEqual(self.tab_verify(first).status_code, 200)
        self.assertEqual(self.tab_verify(first).status_code, 400)
        cookie = self.client.cookies[BROWSER_COOKIE].value
        GoogleAuthFlow.objects.filter(browser_hash=_hash(cookie + ":" + first["flow_id"])).update(expires_at=timezone.now() - timedelta(seconds=1))
        self.assertEqual(self.client.get("/api/auth/google/flow/", {"flow_id": first["flow_id"]}).status_code, 400)
        second = self.tab_start()
        for _ in range(5):
            cache.clear()
            self.assertEqual(self.post("verify", {"flow_id": second["flow_id"], "id_token": self.token("wrong-nonce")}).status_code, 400)
        cache.clear()
        self.assertEqual(self.tab_verify(second).status_code, 400)
        self.assertFalse(User.objects.exists())

    def test_unknown_identity_waits_for_business_and_documents_then_initializes_once(self):
        response = self.verify()
        self.assertEqual(response.data["code"], "google_signup_required")
        self.assertEqual((User.objects.count(), Business.objects.count(), SocialIdentity.objects.count()), (0, 0, 0))
        self.assertEqual(self.client.get("/api/auth/google/flow/").data["code"], "google_signup_required")
        missing = self.signup_data(); missing["accepted_documents"] = []
        self.assertEqual(self.post("signup", missing).status_code, 400)
        self.assertFalse(User.objects.exists())
        data = {**self.signup_data(), "email": "attacker@example.test", "password": "IgnoredSynthetic123"}
        response = self.post("signup", data)
        self.assertEqual(response.status_code, 201, response.data)
        user = User.objects.get(email="google@example.test")
        self.assertFalse(user.has_usable_password())
        self.assertTrue(BusinessMember.objects.filter(user=user, role="owner", is_active=True).exists())
        self.assertTrue(Business.objects.get(owner=user).pipelines.exists())
        self.assertIn("access", response.data)
        self.assertNotIn("refresh", response.data)
        self.assertIn(settings.AUTH_REFRESH_COOKIE_NAME, response.cookies)
        self.assertEqual(self.post("signup", data).status_code, 400)
        self.assertEqual((User.objects.count(), Business.objects.count(), SocialIdentity.objects.count()), (1, 1, 1))
        self.assertNotIn("id_token", str(list(AuditLog.objects.values_list("metadata", flat=True))))
        flow = GoogleAuthFlow.objects.get()
        self.assertEqual((flow.subject, flow.email, flow.full_name), ("", "", ""))

    def test_invalid_signature_audience_issuer_expiry_nonce_and_unverified_email(self):
        for changed in [{"aud": "other"}, {"iss": "https://attacker.invalid"}, {"exp": 1}, {"nonce": "other"},
                        {"email_verified": False}, {"email_verified": "true"}, {"sub": ""}]:
            with self.subTest(changed=changed):
                cache.clear()
                response = self.verify(**changed)
                self.assertEqual(response.status_code, 400)
                self.assertEqual(response.data["code"], "google_flow_invalid")
        cache.clear()
        nonce = self.start()
        token = self.token(nonce)
        parts = token.split("."); parts[2] = ("A" if parts[2][0] != "A" else "B") + parts[2][1:]
        self.assertEqual(self.post("verify", {"id_token": ".".join(parts)}).status_code, 400)
        self.assertFalse(User.objects.exists())

    def test_cross_browser_expired_and_replayed_exchange_are_denied(self):
        nonce = self.start(); token = self.token(nonce)
        other = APIClient(enforce_csrf_checks=True)
        self.assertEqual(self.post("verify", {"id_token": token}, other, self.bootstrap(other)).status_code, 400)
        self.assertEqual(self.post("verify", {"id_token": token}).status_code, 200)
        self.assertEqual(self.post("verify", {"id_token": token}).status_code, 400)
        GoogleAuthFlow.objects.update(expires_at=timezone.now() - timedelta(seconds=1))
        self.assertEqual(self.client.get("/api/auth/google/flow/").status_code, 400)
        self.assertEqual(self.post("signup", self.signup_data()).status_code, 400)

    def test_csrf_required_on_all_mutations_and_foreign_origin_denied(self):
        for action in ["start", "verify", "signup", "link"]:
            with self.subTest(action=action):
                self.assertEqual(self.client.post(f"/api/auth/google/{action}/", {}, format="json").status_code, 403)
                self.assertEqual(self.post(action, headers={**self.headers, "HTTP_ORIGIN": "https://attacker.invalid"}).status_code, 403)

    def test_subject_login_preserves_account_despite_provider_email_change(self):
        user = self.user()
        SocialIdentity.objects.create(user=user, provider="google", subject="google-subject", email=user.email)
        response = self.verify(email="changed@example.test")
        self.assertEqual(response.status_code, 200, response.data)
        self.assertFalse(response.data["created"])
        self.assertEqual(User.objects.count(), 1)
        user.refresh_from_db(); self.assertEqual(user.email, "google@example.test")
        self.assertFalse(Business.objects.exists())

    def test_disabled_identity_cannot_login(self):
        user = self.user(is_active=False)
        SocialIdentity.objects.create(user=user, provider="google", subject="google-subject", email=user.email)
        response = self.verify()
        self.assertEqual(response.status_code, 400)
        self.assertNotIn(settings.AUTH_REFRESH_COOKIE_NAME, response.cookies)

    @override_settings(AUTH_PRIVILEGED_MFA_REQUIRED=True)
    def test_new_owner_requires_enrollment_before_session(self):
        self.verify()
        response = self.post("signup", self.signup_data())
        self.assertEqual(response.status_code, 202, response.data)
        self.assertEqual(response.data["code"], "mfa_enrollment_required")
        self.assertNotIn("access", response.data)
        self.assertNotIn(settings.AUTH_REFRESH_COOKIE_NAME, response.cookies)

    def test_existing_identity_requires_mfa(self):
        user = self.user()
        MfaDevice.objects.create(user=user, confirmed_at=timezone.now(), encrypted_secret=encrypt_credential_value(pyotp.random_base32()))
        SocialIdentity.objects.create(user=user, provider="google", subject="google-subject", email=user.email)
        response = self.verify()
        self.assertEqual(response.status_code, 202, response.data)
        self.assertEqual(response.data["code"], "mfa_required")
        self.assertNotIn("access", response.data)

    def test_link_requires_same_user_recent_session_password_and_is_single_use(self):
        user = self.user()
        response = self.verify()
        self.assertEqual(response.data["code"], "google_link_required")
        self.assertFalse(SocialIdentity.objects.exists())
        self.assertEqual(self.post("signup", self.signup_data()).status_code, 409)
        self.assertEqual(self.post("link", {"password": "ExistingSynthetic123"}).status_code, 401)
        self.authenticate(user, stale=True)
        self.assertEqual(self.post("link", {"password": "ExistingSynthetic123"}).status_code, 403)
        self.authenticate(user)
        self.assertEqual(self.post("link", {"password": "wrong"}).status_code, 403)
        self.assertEqual(self.post("link", {"password": "ExistingSynthetic123"}).status_code, 200)
        self.assertEqual(self.post("link", {"password": "ExistingSynthetic123"}).status_code, 400)
        self.assertEqual(SocialIdentity.objects.get().user, user)
        self.assertEqual(User.objects.count(), 1)
        self.assertFalse(Business.objects.exists())

    def test_link_other_user_cannot_claim_flow(self):
        self.user(); other = self.user("other@example.test")
        self.verify(); self.authenticate(other)
        self.assertEqual(self.post("link", {"password": "ExistingSynthetic123"}).status_code, 409)
        self.assertFalse(SocialIdentity.objects.exists())

    def test_link_rechecks_epoch_after_authentication_before_binding(self):
        from apps.accounts.google_auth import _flow
        user = self.user(); self.verify(); self.authenticate(user)
        def revoke_then_lock(request, **kwargs):
            if kwargs.get("lock"):
                User.objects.filter(pk=user.pk).update(auth_epoch=1)
            return _flow(request, **kwargs)
        with patch("apps.accounts.google_auth._flow", side_effect=revoke_then_lock):
            response = self.post("link", {"password": "ExistingSynthetic123"})
        self.assertEqual(response.status_code, 403)
        self.assertFalse(SocialIdentity.objects.exists())

    def test_link_checks_fresh_factor_and_never_duplicates_provider(self):
        user = self.user(); secret = pyotp.random_base32()
        MfaDevice.objects.create(user=user, confirmed_at=timezone.now(), encrypted_secret=encrypt_credential_value(secret))
        self.verify(); self.authenticate(user, mfa=True)
        self.assertEqual(self.post("link", {"password": "ExistingSynthetic123", "mfa_code": "wrong"}).status_code, 403)
        self.assertFalse(SocialIdentity.objects.exists())
        self.assertEqual(self.post("link", {"password": "ExistingSynthetic123", "mfa_code": pyotp.TOTP(secret).now()}).status_code, 200)

    def test_signup_integrity_race_rolls_back_every_new_entity(self):
        self.verify()
        with patch("apps.accounts.google_auth.SocialIdentity.objects.create", side_effect=IntegrityError("synthetic race")):
            response = self.post("signup", self.signup_data())
        self.assertEqual(response.status_code, 409)
        self.assertFalse(User.objects.exists()); self.assertFalse(Business.objects.exists())
        self.assertIsNone(GoogleAuthFlow.objects.get(consumed_at=None).consumed_at)
        self.assertEqual(self.post("signup", self.signup_data()).status_code, 201)

    def test_failed_exchange_attempts_are_bounded_and_new_start_recovers(self):
        self.start()
        for _ in range(5):
            self.assertEqual(self.post("verify", {"id_token": "invalid"}).status_code, 400)
        flow = GoogleAuthFlow.objects.get(); self.assertEqual(flow.failed_attempts, 5)
        cache.clear()
        self.assertEqual(self.verify().status_code, 200)

    def test_nonce_and_browser_secret_are_hashed_not_persisted(self):
        nonce = self.start(); flow = GoogleAuthFlow.objects.get()
        self.assertEqual(flow.nonce_hash, _hash(nonce))
        self.assertEqual(flow.browser_hash, _hash(self.client.cookies[COOKIE].value))
        self.assertNotIn(nonce, str(flow.__dict__))

    def test_expired_flow_cleanup_is_bounded_and_preserves_active_flow(self):
        from apps.accounts.google_auth import prune_google_flows
        self.verify()
        active = GoogleAuthFlow.objects.get()
        for index in range(3):
            GoogleAuthFlow.objects.create(browser_hash=_hash(str(index)), nonce_hash=_hash("unused"),
                                         expires_at=timezone.now() - timedelta(seconds=1), email="expired@example.test")
        self.assertEqual(prune_google_flows(limit=2), 2)
        self.assertTrue(GoogleAuthFlow.objects.filter(pk=active.pk).exists())
        from apps.accounts.tasks import flush_expired_tokens
        with patch("apps.accounts.tasks.call_command") as flush:
            flush_expired_tokens()
        flush.assert_called_once_with("flushexpiredtokens")
        self.assertEqual(GoogleAuthFlow.objects.count(), 1)
        self.start()
        active.refresh_from_db()
        self.assertEqual((active.subject, active.email, active.full_name), ("", "", ""))


@skipUnless(connection.vendor == "postgresql", "Requires independent PostgreSQL transactions")
@override_settings(GOOGLE_OAUTH_CLIENT_IDS=["synthetic-client"], AUTH_PRIVILEGED_MFA_REQUIRED=False)
class GoogleAuthConcurrencyTests(TransactionTestCase):
    def setUp(self):
        cache.clear()

    def flow(self, subject="same-subject"):
        cookie = secrets.token_urlsafe(32)
        GoogleAuthFlow.objects.create(browser_hash=_hash(cookie), nonce_hash=_hash("unused"),
                                     expires_at=timezone.now() + timedelta(minutes=10), verified_at=timezone.now(),
                                     subject=subject, email="race@example.test", full_name="Synthetic race")
        return cookie

    def race(self, cookies, action, payload, access=None):
        ready = Barrier(2)
        def request(cookie):
            close_old_connections()
            try:
                client = APIClient(enforce_csrf_checks=True)
                csrf = client.get("/api/auth/csrf/").json()["csrf_token"]
                client.cookies[COOKIE] = cookie
                if access:
                    client.credentials(HTTP_AUTHORIZATION="Bearer " + access)
                ready.wait(timeout=10)
                response = client.post(f"/api/auth/google/{action}/", payload, format="json",
                                       HTTP_X_CSRFTOKEN=csrf, HTTP_ORIGIN="http://testserver")
                return response.status_code
            finally:
                connections.close_all()
        with ThreadPoolExecutor(max_workers=2) as pool:
            futures = [pool.submit(request, cookie) for cookie in cookies]
            return sorted(future.result(timeout=30) for future in futures)

    def test_concurrent_signup_different_flows_cannot_duplicate_identity_or_business(self):
        cookies = [self.flow(), self.flow()]
        payload = {"business_name": "Synthetic race", "city": "Almaty",
                   "accepted_documents": ["terms", "privacy", "personal-data", "company-data"]}
        self.assertEqual(self.race(cookies, "signup", payload), [201, 409])
        self.assertEqual((User.objects.count(), Business.objects.count(), SocialIdentity.objects.count()), (1, 1, 1))
        self.assertEqual(GoogleAuthFlow.objects.filter(consumed_at__isnull=False).count(), 1)

    def test_concurrent_links_cannot_attach_two_subjects_to_same_user(self):
        user = User.objects.create_user(username="race", email="race@example.test", password="SyntheticRace123", role="business_operator")
        access = str(issue_session(user).access_token)
        self.assertEqual(self.race([self.flow("subject-1"), self.flow("subject-2")], "link",
                                   {"password": "SyntheticRace123"}, access), [200, 409])
        self.assertEqual(SocialIdentity.objects.filter(user=user, provider="google").count(), 1)
        self.assertFalse(Business.objects.exists())
