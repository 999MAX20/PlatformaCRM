from django.conf import settings
from django.core.cache import cache
from django.contrib.auth.tokens import default_token_generator
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from django.test import TestCase, override_settings
import pyotp
from rest_framework.test import APIClient

from apps.accounts.models import User


class LoginCsrfTests(TestCase):
    def setUp(self):
        cache.clear()
        self.user = User.objects.create_user(username="csrf-account", email="csrf@example.invalid", password="SyntheticCsrf123!", role="business_operator")
        self.client = APIClient(enforce_csrf_checks=True)

    def test_cross_site_form_cannot_install_attacker_session(self):
        response = self.client.post("/api/auth/token/", {"email": self.user.email, "password": "SyntheticCsrf123!"},
                                    HTTP_ORIGIN="https://attacker.invalid", HTTP_SEC_FETCH_SITE="cross-site")
        self.assertEqual(response.status_code, 403)
        self.assertNotIn(settings.AUTH_REFRESH_COOKIE_NAME, response.cookies)

    def test_originless_form_cannot_install_session(self):
        response = self.client.post("/api/auth/token/", {"email": self.user.email, "password": "SyntheticCsrf123!"})
        self.assertEqual(response.status_code, 403)
        self.assertNotIn(settings.AUTH_REFRESH_COOKIE_NAME, response.cookies)

    def bootstrap(self):
        response = self.client.get("/api/auth/csrf/")
        self.assertEqual(response.status_code, 200)
        self.assertIn("no-store", response["Cache-Control"])
        self.assertIn(settings.CSRF_COOKIE_NAME, response.cookies)
        self.assertNotIn(settings.AUTH_REFRESH_COOKIE_NAME, response.cookies)
        return response.json()["csrf_token"]

    def test_valid_csrf_login_refresh_logout_and_missing_token_rejection(self):
        token = self.bootstrap()
        args = {"HTTP_X_CSRFTOKEN": token, "HTTP_ORIGIN": "http://testserver"}
        login = self.client.post("/api/auth/token/", {"email": self.user.email, "password": "SyntheticCsrf123!"}, format="json", **args)
        self.assertEqual(login.status_code, 200)
        cookie = login.cookies[settings.AUTH_REFRESH_COOKIE_NAME].value
        for path in ["/api/auth/token/refresh/", "/api/auth/logout/"]:
            with self.subTest(path=path):
                denied = self.client.post(path, {}, format="json")
                self.assertEqual(denied.status_code, 403)
                self.assertNotIn(settings.AUTH_REFRESH_COOKIE_NAME, denied.cookies)
                self.assertEqual(self.client.cookies[settings.AUTH_REFRESH_COOKIE_NAME].value, cookie)
        refreshed = self.client.post("/api/auth/token/refresh/", {}, format="json", **args)
        self.assertEqual(refreshed.status_code, 200)
        self.assertEqual(self.client.post("/api/auth/logout/", {}, format="json", **args).status_code, 200)

    def test_all_public_cookie_issuance_endpoints_reject_untrusted_origin_even_with_token(self):
        token = self.bootstrap()
        paths = ["/api/auth/token/", "/api/auth/social/", "/api/auth/signup/owner/",
                 "/api/auth/mfa/verify/", "/api/auth/mfa/enrollment/confirm/",
                 "/api/auth/password-reset/confirm/",
                 "/api/auth/token/refresh/", "/api/auth/logout/"]
        for path in paths:
            for origin in ["https://attacker.invalid", "null"]:
                with self.subTest(path=path, origin=origin):
                    response = self.client.post(path, {}, format="json", HTTP_X_CSRFTOKEN=token, HTTP_ORIGIN=origin)
                    self.assertEqual(response.status_code, 403)
                    self.assertNotIn(settings.AUTH_REFRESH_COOKIE_NAME, response.cookies)

    @override_settings(CSRF_TRUSTED_ORIGINS=["https://frontend.example.invalid"])
    def test_explicit_trusted_frontend_can_login_with_token(self):
        response = self.client.post("/api/auth/token/", {"email": self.user.email, "password": "SyntheticCsrf123!"},
                                    format="json", HTTP_X_CSRFTOKEN=self.bootstrap(), HTTP_ORIGIN="https://frontend.example.invalid")
        self.assertEqual(response.status_code, 200)

    def test_valid_password_reset_preserves_one_time_token_contract(self):
        payload = {"uid": urlsafe_base64_encode(force_bytes(self.user.pk)), "token": default_token_generator.make_token(self.user), "password": "SyntheticCsrfNew123!"}
        headers = {"HTTP_X_CSRFTOKEN": self.bootstrap(), "HTTP_ORIGIN": "http://testserver"}
        self.assertEqual(self.client.post("/api/auth/password-reset/confirm/", payload, format="json").status_code, 403)
        allowed = self.client.post("/api/auth/password-reset/confirm/", payload, format="json", **headers)
        self.assertEqual(allowed.status_code, 200)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password(payload["password"]))
        self.assertEqual(self.client.post("/api/auth/password-reset/confirm/", payload, format="json", **headers).status_code, 400)

    @override_settings(AUTH_PRIVILEGED_MFA_REQUIRED=True)
    def test_mfa_enrollment_issues_cookie_only_with_csrf(self):
        self.user.role = User.Roles.BUSINESS_OWNER
        self.user.save()
        args = {"HTTP_X_CSRFTOKEN": self.bootstrap(), "HTTP_ORIGIN": "http://testserver"}
        login = self.client.post("/api/auth/token/", {"email": self.user.email, "password": "SyntheticCsrf123!"}, format="json", **args)
        self.assertEqual(login.status_code, 202)
        challenge = login.data["challenge_token"]
        start = self.client.post("/api/auth/mfa/enrollment/start/", {"challenge_token": challenge}, format="json")
        self.assertEqual(start.status_code, 200)
        payload = {"challenge_token": challenge, "code": pyotp.TOTP(start.data["manual_key"]).now()}
        denied = self.client.post("/api/auth/mfa/enrollment/confirm/", payload, format="json")
        self.assertEqual(denied.status_code, 403)
        allowed = self.client.post("/api/auth/mfa/enrollment/confirm/", payload, format="json", **args)
        self.assertEqual(allowed.status_code, 200)
        self.assertIn(settings.AUTH_REFRESH_COOKIE_NAME, allowed.cookies)
