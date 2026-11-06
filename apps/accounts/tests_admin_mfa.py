import pyotp
from django.contrib import admin
from django.core.cache import cache
from django.test import Client, TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounts.admin_site import ADMIN_MFA_SESSION_KEY, MfaAdminSite
from apps.accounts.mfa import _replace_recovery_codes
from apps.accounts.models import MfaDevice, MfaRecoveryCode, User
from apps.accounts.session_security import revoke_user_refresh_sessions
from apps.integrations.credential_encryption import encrypt_credential_value


@override_settings(AUTH_PRIVILEGED_MFA_REQUIRED=True)
class AdminMfaTests(TestCase):
    password = "Synthetic-Admin-Password-2026!"

    def setUp(self):
        cache.clear()
        self.user = User.objects.create_superuser(username="admin", email="admin@example.invalid", password=self.password)
        self.secret = pyotp.random_base32()
        self.device = MfaDevice.objects.create(user=self.user, encrypted_secret=encrypt_credential_value(self.secret), confirmed_at=timezone.now())
        self.client = Client(enforce_csrf_checks=True)

    def login(self, code="", **extra):
        self.client.get("/admin/login/")
        data = {"username": self.user.email, "password": self.password, "mfa_code": code,
                "csrfmiddlewaretoken": self.client.cookies["csrftoken"].value, "next": "/admin/", **extra}
        return self.client.post("/admin/login/", data, HTTP_ORIGIN="http://testserver")

    def test_default_site_is_protected_and_password_only_is_denied(self):
        self.assertIsInstance(admin.site, MfaAdminSite)
        self.assertEqual(self.login().status_code, 200)
        self.assertNotIn("_auth_user_id", self.client.session)
        for path in ("/admin/", "/admin/accounts/user/", "/admin/password_change/", "/admin/autocomplete/"):
            self.assertEqual(self.client.get(path).status_code, 302)

    def test_valid_totp_preserves_admin_access_and_logout(self):
        self.assertEqual(self.login(pyotp.TOTP(self.secret).now()).status_code, 302)
        self.assertEqual(self.client.get("/admin/accounts/user/").status_code, 200)
        response = self.client.post("/admin/logout/", {"csrfmiddlewaretoken": self.client.cookies["csrftoken"].value})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.client.get("/admin/").status_code, 302)

    def test_recovery_code_is_single_use_and_not_echoed(self):
        code = _replace_recovery_codes(self.user)[0]
        self.assertEqual(self.login(code).status_code, 302)
        self.assertEqual(MfaRecoveryCode.objects.filter(user=self.user, used_at__isnull=False).count(), 1)
        self.client = Client(enforce_csrf_checks=True)
        response = self.login(code)
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, code)
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_totp_replay_cannot_create_second_admin_session(self):
        code = pyotp.TOTP(self.secret).now()
        self.assertEqual(self.login(code).status_code, 302)
        self.client = Client(enforce_csrf_checks=True)
        self.assertEqual(self.login(code).status_code, 200)
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_existing_password_session_cannot_bypass_factor(self):
        self.client.force_login(self.user)
        self.assertEqual(self.client.get("/admin/accounts/user/").status_code, 302)

    def test_epoch_revocation_invalidates_admin_proof(self):
        self.login(pyotp.TOTP(self.secret).now())
        revoke_user_refresh_sessions(self.user)
        self.assertEqual(self.client.get("/admin/accounts/user/").status_code, 302)

    def test_replaced_device_invalidates_admin_proof(self):
        self.login(pyotp.TOTP(self.secret).now())
        self.device.delete()
        MfaDevice.objects.create(user=self.user, encrypted_secret=encrypt_credential_value(pyotp.random_base32()), confirmed_at=timezone.now())
        self.assertEqual(self.client.get("/admin/accounts/user/").status_code, 302)

    def test_missing_device_requires_existing_crm_enrollment(self):
        self.device.delete()
        response = self.login()
        self.assertContains(response, "Set up two-factor authentication")
        self.assertNotIn("_auth_user_id", self.client.session)

    @override_settings(AUTH_PRIVILEGED_MFA_REQUIRED=False)
    def test_enabled_factor_required_even_with_policy_disabled(self):
        self.assertEqual(self.login().status_code, 200)
        self.assertNotIn("_auth_user_id", self.client.session)

    @override_settings(AUTH_PRIVILEGED_MFA_REQUIRED=False)
    def test_staff_without_factor_keeps_development_login(self):
        self.device.delete()
        self.assertEqual(self.login().status_code, 302)
        self.assertEqual(self.client.get("/admin/").status_code, 200)

    def test_csrf_rejection_does_not_consume_totp(self):
        response = self.client.post("/admin/login/", {"username": self.user.email, "password": self.password,
                                                    "mfa_code": pyotp.TOTP(self.secret).now()})
        self.assertEqual(response.status_code, 403)
        self.device.refresh_from_db()
        self.assertEqual(self.device.last_used_counter, -1)

    def test_throttle_precedes_factor_and_password_authentication(self):
        for _ in range(5):
            self.assertEqual(self.login("invalid").status_code, 200)
        response = self.login(pyotp.TOTP(self.secret).now())
        self.assertContains(response, "Too many sign-in attempts")
        self.assertNotIn("_auth_user_id", self.client.session)
        self.device.refresh_from_db()
        self.assertEqual(self.device.last_used_counter, -1)

    def test_nonstaff_user_cannot_enter_or_consume_factor(self):
        self.user.is_staff = False
        self.user.save(update_fields=["is_staff"])
        self.assertEqual(self.login(pyotp.TOTP(self.secret).now()).status_code, 200)
        self.assertNotIn("_auth_user_id", self.client.session)
        self.device.refresh_from_db()
        self.assertEqual(self.device.last_used_counter, -1)

    def test_unicode_login_alias_shares_account_quota_across_ips(self):
        for _ in range(5):
            self.login("invalid")
        self.client = Client(enforce_csrf_checks=True, REMOTE_ADDR="192.0.2.42")
        response = self.login(pyotp.TOTP(self.secret).now(), username=self.user.email.replace("a", "ａ"))
        self.assertContains(response, "Too many sign-in attempts")
        self.assertNotIn("_auth_user_id", self.client.session)
        self.device.refresh_from_db()
        self.assertEqual(self.device.last_used_counter, -1)

    def test_copied_proof_for_other_user_is_rejected(self):
        self.login(pyotp.TOTP(self.secret).now())
        session = self.client.session
        proof = session[ADMIN_MFA_SESSION_KEY]
        proof["user_id"] = "999999"
        session[ADMIN_MFA_SESSION_KEY] = proof
        session.save()
        self.assertEqual(self.client.get("/admin/").status_code, 302)

    def test_rest_login_still_requires_challenge_and_external_next_is_rejected(self):
        api = APIClient()
        response = api.post("/api/auth/token/", {"email": self.user.email, "password": self.password}, format="json")
        self.assertEqual(response.status_code, 202)
        self.assertEqual(response.data["code"], "mfa_required")
        response = self.login(pyotp.TOTP(self.secret).now(), next="https://attacker.invalid/")
        self.assertEqual(response.status_code, 302)
        self.assertNotIn("attacker.invalid", response["Location"])
