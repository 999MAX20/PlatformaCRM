from datetime import timedelta
from unittest.mock import patch
import re

from django.core import mail
from django.core.cache import cache
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounts.models import EmailChangeChallenge, User
from apps.accounts.mfa import issue_session
from apps.accounts.session_security import revoke_user_refresh_sessions
from apps.businesses.models import Business
from apps.core.models import AuditLog


@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
class EmailChangeTests(TestCase):
    request_url = "/api/auth/change-email/request/"
    confirm_url = "/api/auth/change-email/confirm/"

    def setUp(self):
        cache.clear()
        self.user = User.objects.create_user(username="mail", email="old@example.com", password="StrongPass123!")
        self.other = User.objects.create_user(username="othermail", email="other@example.com", password="StrongPass123!")
        self.business = Business.objects.create(name="Mail test", slug="mail-test", owner=self.user)
        self.api = APIClient()
        self.api.force_authenticate(self.user)

    def request_code(self, **overrides):
        payload = {"new_email": "new@example.com", "current_password": "StrongPass123!", **overrides}
        response = self.api.post(self.request_url, payload)
        self.assertEqual(response.status_code, 200, response.data)
        return re.search(r"\b[0-9]{6}\b", mail.outbox[-1].body).group()

    def test_verified_change_keeps_identity_and_links_revokes_old_tokens(self):
        old = issue_session(self.user, mfa_verified=False)
        code = self.request_code(new_email="NEW@example.com")
        self.user.refresh_from_db()
        self.assertEqual(self.user.email, "old@example.com")
        self.assertNotEqual(EmailChangeChallenge.objects.get(user=self.user).code_hash, code)
        response = self.api.post(self.confirm_url, {"code": code})
        self.assertEqual(response.status_code, 200, response.data)
        self.user.refresh_from_db(); self.business.refresh_from_db()
        self.assertEqual(self.user.email, "new@example.com")
        self.assertEqual(self.business.owner_id, self.user.pk)
        self.assertFalse(EmailChangeChallenge.objects.filter(user=self.user).exists())
        self.assertEqual(User.objects.count(), 2)
        self.assertTrue(AuditLog.objects.filter(metadata__event="email_changed").exists())
        self.assertNotIn(code, str(list(AuditLog.objects.values_list("metadata", flat=True))))
        api = APIClient(); api.credentials(HTTP_AUTHORIZATION=f"Bearer {old.access_token}")
        self.assertEqual(api.get("/api/auth/me/").status_code, 401)
        api.credentials(HTTP_AUTHORIZATION=f"Bearer {response.data['access']}")
        self.assertEqual(api.get("/api/auth/me/").status_code, 200)
        self.assertEqual(self.api.post(self.confirm_url, {"code": code}).status_code, 400)

    def test_password_duplicate_and_unauthenticated_denial(self):
        for data in ({"current_password": "wrong"}, {"new_email": "OTHER@example.com"}, {"new_email": "old@example.com"}):
            response = self.api.post(self.request_url, {"new_email": "new@example.com", "current_password": "StrongPass123!", **data})
            self.assertEqual(response.status_code, 400)
        self.api.force_authenticate(None)
        self.assertEqual(self.api.post(self.request_url, {}).status_code, 401)
        self.assertEqual(self.api.post(self.confirm_url, {}).status_code, 401)

    def test_other_user_cannot_confirm_and_no_user_id_override(self):
        code = self.request_code()
        self.api.force_authenticate(self.other)
        self.assertEqual(self.api.post(self.confirm_url, {"code": code, "user": self.user.pk}).status_code, 400)
        self.user.refresh_from_db(); self.assertEqual(self.user.email, "old@example.com")

    def test_attempt_limit_expiry_and_session_change(self):
        code = self.request_code()
        wrong = "000000" if code != "000000" else "000001"
        for _ in range(5):
            self.assertEqual(self.api.post(self.confirm_url, {"code": wrong}).status_code, 400)
        self.assertEqual(EmailChangeChallenge.objects.get(user=self.user).failed_attempts, 5)
        self.assertEqual(self.api.post(self.confirm_url, {"code": code}).status_code, 400)
        code = self.request_code()
        EmailChangeChallenge.objects.filter(user=self.user).update(expires_at=timezone.now()-timedelta(seconds=1))
        self.assertEqual(self.api.post(self.confirm_url, {"code": code}).status_code, 400)
        code = self.request_code()
        revoke_user_refresh_sessions(self.user)
        self.assertEqual(self.api.post(self.confirm_url, {"code": code}).status_code, 400)

    def test_resend_invalidates_code_and_rechecks_address(self):
        with patch("apps.accounts.email_changes.secrets.randbelow", return_value=123456):
            old = self.request_code()
        with patch("apps.accounts.email_changes.secrets.randbelow", return_value=654321):
            new = self.request_code()
        self.assertEqual(self.api.post(self.confirm_url, {"code": old}).status_code, 400)
        self.other.email = "new@example.com"; self.other.save(update_fields=["email"])
        self.assertEqual(self.api.post(self.confirm_url, {"code": new}).status_code, 400)
        self.user.refresh_from_db(); self.assertEqual(self.user.email, "old@example.com")

    @patch("apps.accounts.email_changes.send_mail", side_effect=OSError("smtp down"))
    def test_delivery_failure_does_not_change_login_or_claim_success(self, _send):
        response = self.api.post(self.request_url, {"new_email": "new@example.com", "current_password": "StrongPass123!"})
        self.assertEqual(response.status_code, 503, response.data)
        self.assertFalse(EmailChangeChallenge.objects.exists())
        self.user.refresh_from_db(); self.assertEqual(self.user.email, "old@example.com")

    @patch("apps.accounts.email_changes.has_confirmed_mfa", return_value=True)
    @patch("apps.accounts.email_changes.verify_user_factor", return_value=False)
    def test_mfa_is_enforced(self, verify, _has):
        response = self.api.post(self.request_url, {"new_email": "new@example.com", "current_password": "StrongPass123!"})
        self.assertEqual(response.status_code, 400)
        self.assertFalse(EmailChangeChallenge.objects.exists())
        verify.return_value = True
        self.request_code(mfa_code="123456")

    def test_direct_profile_patch_cannot_change_email(self):
        self.api.patch("/api/auth/me/", {"email": "bypass@example.com"}, format="json")
        self.user.refresh_from_db(); self.assertEqual(self.user.email, "old@example.com")

    @override_settings(EMAIL_BACKEND="django.core.mail.backends.console.EmailBackend")
    def test_console_backend_does_not_report_mail_delivered(self):
        response = self.api.post(self.request_url, {"new_email": "new@example.com", "current_password": "StrongPass123!"})
        self.assertEqual(response.status_code, 503)
        self.assertFalse(EmailChangeChallenge.objects.exists())
