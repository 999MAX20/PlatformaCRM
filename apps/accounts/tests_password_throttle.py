from unittest.mock import patch

import pyotp
from django.core.cache import cache
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounts.mfa import issue_session, _replace_recovery_codes
from apps.accounts.models import MfaDevice, MfaRecoveryCode, User
from apps.integrations.credential_encryption import encrypt_credential_value


class PasswordChangeThrottleTests(TestCase):
    password = "Current-Synthetic-Password-2026!"
    replacement = "Replacement-Synthetic-Password-2026!"

    def setUp(self):
        cache.clear()
        self.user = User.objects.create_user(username="throttle", email="throttle@example.invalid", password=self.password)
        self.api = APIClient()
        self.authenticate()

    def authenticate(self):
        refresh = issue_session(self.user, mfa_verified=True)
        self.api.credentials(HTTP_AUTHORIZATION="Bearer " + str(refresh.access_token))

    def change(self, password=None, factor="invalid"):
        return self.api.post("/api/auth/change-password/", {
            "current_password": password or self.password,
            "new_password": self.replacement, "mfa_code": factor,
        }, format="json")

    def enroll(self):
        secret = pyotp.random_base32()
        MfaDevice.objects.create(user=self.user, encrypted_secret=encrypt_credential_value(secret), confirmed_at=timezone.now())
        return secret

    def test_wrong_password_quota_survives_new_access_token(self):
        for _ in range(5):
            self.assertEqual(self.change("incorrect").status_code, 400)
        self.authenticate()
        rejected = self.change()
        self.assertEqual(rejected.status_code, 429)
        self.assertGreater(int(rejected["Retry-After"]), 0)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password(self.password))
        self.assertEqual(self.user.auth_epoch, 0)

    def test_factor_quota_does_not_consume_valid_recovery_code(self):
        self.enroll()
        recovery = _replace_recovery_codes(self.user)[0]
        for _ in range(5):
            self.assertEqual(self.change().status_code, 401)
        self.assertEqual(self.change(factor=recovery).status_code, 429)
        self.assertEqual(MfaRecoveryCode.objects.filter(user=self.user, used_at__isnull=True).count(), 10)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password(self.password))

    def test_quota_expiry_allows_legitimate_password_change(self):
        from rest_framework.throttling import SimpleRateThrottle
        now = SimpleRateThrottle.timer()
        with patch.object(SimpleRateThrottle, "timer", staticmethod(lambda: now)):
            for _ in range(5):
                self.change("incorrect")
            self.assertEqual(self.change().status_code, 429)
        with patch.object(SimpleRateThrottle, "timer", staticmethod(lambda: now + 61)):
            self.assertEqual(self.change().status_code, 200)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password(self.replacement))

    def test_valid_totp_changes_password_and_revokes_old_access(self):
        secret = self.enroll()
        self.assertEqual(self.change(factor=pyotp.TOTP(secret).now()).status_code, 200)
        self.assertEqual(self.api.get("/api/auth/me/").status_code, 401)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password(self.replacement))

    def test_valid_recovery_code_changes_password_once(self):
        self.enroll()
        recovery = _replace_recovery_codes(self.user)[0]
        self.assertEqual(self.change(factor=recovery).status_code, 200)
        self.assertEqual(MfaRecoveryCode.objects.filter(user=self.user, used_at__isnull=False).count(), 1)
