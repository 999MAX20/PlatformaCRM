import re
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier, Event
from datetime import timedelta
from unittest.mock import patch
from unittest import skipUnless

import pyotp
from django.core import mail
from django.core.cache import cache
from django.db import DatabaseError, connection, close_old_connections, transaction
from django.test import TestCase, TransactionTestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework.test import APIRequestFactory
from rest_framework.exceptions import ValidationError

from apps.accounts.mfa import issue_session, issue_step_up_token
from apps.accounts.models import AccountRecovery, EmailChangeChallenge, MfaDevice, SocialIdentity, User
from apps.accounts.session_security import revoke_user_refresh_sessions
from apps.businesses.models import Business, BusinessMember
from apps.core.models import AuditLog
from apps.integrations.credential_encryption import encrypt_credential_value
from apps.support.models import SupportCase


@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend", FRONTEND_URL="https://crm.example.test")
class RecoveryTests(TestCase):
    def setUp(self):
        cache.clear()
        self.owner = User.objects.create_user(username="owner", email="owner@example.com", role="business_owner", password="Original123!password")
        self.staff = User.objects.create_user(username="employee", email="employee@example.com", role="staff", password="Original123!password")
        self.operator = User.objects.create_user(username="operator", email="operator@example.com", role="platform_manager")
        self.business = Business.objects.create(owner=self.owner, name="Recovery business", slug="recovery")
        BusinessMember.objects.create(business=self.business, user=self.owner, role="owner")
        BusinessMember.objects.create(business=self.business, user=self.staff, role="specialist")
        self.case = SupportCase.objects.create(business=self.business, created_by=self.operator, requester=self.owner, source="platform", subject="Lost access")
        secret = pyotp.random_base32()
        MfaDevice.objects.create(user=self.operator, encrypted_secret=encrypt_credential_value(secret), confirmed_at=timezone.now())
        self.step = issue_step_up_token(self.operator, pyotp.TOTP(secret).now())
        self.api = APIClient(); self.api.force_authenticate(self.operator)
        self.root = f"/api/platform/merchants/{self.business.pk}/account-recovery/"
        self.public = APIClient()

    def prepare(self, user=None, **overrides):
        user = user or self.owner
        self.case.requester = user; self.case.save(update_fields=["requester"])
        snapshot = self.api.get(self.root)
        self.assertEqual(snapshot.status_code, 200, snapshot.data)
        candidate = next(row for row in snapshot.data["candidates"] if row["id"] == user.pk)
        return self.api.post(self.root, {"user_id": user.pk, "support_case_id": self.case.pk,
            "new_email": "recovered@example.com", "expected_revision": candidate["revision"],
            "reason": "Verified support request", "verified_reference": "Previously verified onboarding record ref 42; authority matched", **overrides},
            format="json", HTTP_X_ZANI_MFA_STEP_UP=self.step)

    def act(self, id, action="send"):
        return self.api.post(f"{self.root}{id}/", {"action": action}, format="json", HTTP_X_ZANI_MFA_STEP_UP=self.step)

    def send(self, **overrides):
        prepared = self.prepare(**overrides)
        self.assertEqual(prepared.status_code, 200, prepared.data)
        sent = self.act(prepared.data["id"])
        self.assertEqual(sent.status_code, 200, sent.data)
        self.assertEqual(sent.data["status"], "sent")
        token = re.search(r"recover-account#([^/]+)/([^\s]+)", mail.outbox[-1].body).group(2)
        return prepared.data["id"], token

    def finish(self, id, token, **overrides):
        return self.public.post("/api/auth/account-recovery/", {"recovery_id": id, "token": token, "password": "NewVerifiedPassword123!", **overrides}, format="json")

    def test_manager_recovers_owner_atomically_without_session_or_identity_change(self):
        session = issue_session(self.owner)
        SocialIdentity.objects.create(user=self.owner, provider="google", subject="old-google", email=self.owner.email)
        MfaDevice.objects.create(user=self.owner, encrypted_secret="unused", confirmed_at=timezone.now())
        old_password = self.owner.password
        id, token = self.send()
        self.owner.refresh_from_db(); self.assertEqual(self.owner.password, old_password)
        response = self.finish(id, token)
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data, {"ok": True})
        self.owner.refresh_from_db(); self.business.refresh_from_db()
        self.assertTrue(self.owner.check_password("NewVerifiedPassword123!"))
        self.assertEqual(self.owner.email, "recovered@example.com")
        self.assertEqual(self.business.owner_id, self.owner.pk)
        self.assertEqual(self.owner.auth_epoch, 1)
        self.assertFalse(SocialIdentity.objects.filter(user=self.owner).exists())
        self.assertFalse(MfaDevice.objects.filter(user=self.owner).exists())
        stale = APIClient(); stale.credentials(HTTP_AUTHORIZATION=f"Bearer {session.access_token}")
        self.assertEqual(stale.get("/api/auth/me/").status_code, 401)
        self.assertEqual(self.finish(id, token).status_code, 400)
        self.assertTrue(AuditLog.objects.filter(metadata__kind="account_recovery", metadata__event="completed", actor=self.owner).exists())
        self.assertNotIn(token, str(list(AuditLog.objects.values_list("metadata", flat=True))))

    @override_settings(AUTH_PRIVILEGED_MFA_REQUIRED=True)
    def test_next_login_requires_mfa_enrollment(self):
        id, token = self.send()
        self.assertEqual(self.finish(id, token).status_code, 200)
        response = self.public.post("/api/auth/token/", {"email": "recovered@example.com", "password": "NewVerifiedPassword123!"})
        self.assertEqual(response.data["code"], "mfa_enrollment_required")
        self.assertNotIn("access", response.data)

    def test_staff_requires_real_owner_confirmation(self):
        response = self.prepare(self.staff, verified_reference="")
        self.assertEqual(response.status_code, 200, response.data)
        id = response.data["id"]
        self.assertEqual(self.act(id).status_code, 400)
        url = f"/api/auth/recovery-confirmations/{id}/"
        self.assertEqual(self.api.post(url, {"decision": "confirm"}).status_code, 404)
        owner = APIClient(); owner.force_authenticate(self.owner)
        self.assertEqual(len(owner.get("/api/auth/recovery-confirmations/").data["results"]), 1)
        self.assertEqual(owner.post(url, {"decision": "confirm"}).status_code, 200)
        self.assertEqual(self.act(id).data["status"], "sent")

    def test_multiple_businesses_require_identity_reference_and_keep_memberships(self):
        other = Business.objects.create(owner=self.owner, name="Other", slug="other")
        member = BusinessMember.objects.create(business=other, user=self.staff, role="manager")
        self.assertEqual(self.prepare(self.staff, verified_reference="").status_code, 400)
        response = self.prepare(self.staff)
        self.assertEqual(response.status_code, 200)
        owner = APIClient(); owner.force_authenticate(self.owner)
        owner.post(f"/api/auth/recovery-confirmations/{response.data['id']}/", {"decision": "confirm"})
        self.act(response.data["id"])
        token = re.search(r"recover-account#[^/]+/([^\s]+)", mail.outbox[-1].body).group(1)
        self.assertEqual(self.finish(response.data["id"], token).status_code, 200)
        member.refresh_from_db(); self.assertTrue(member.is_active); self.assertEqual(member.role, "manager")

    def test_missing_identity_evidence_denied(self):
        self.assertEqual(self.prepare(verified_reference="").status_code, 400)

    def test_delivery_failure_is_persisted_and_retry_rotates_link(self):
        response = self.prepare(); id = response.data["id"]
        with patch("apps.accounts.recovery.send_mail", side_effect=OSError("secret provider payload")):
            failure = self.act(id)
        self.assertEqual(failure.status_code, 200)
        self.assertEqual(failure.data["delivery_status"], "unavailable")
        self.assertNotIn("secret", str(failure.data))
        AccountRecovery.objects.filter(pk=id).update(last_attempt_at=timezone.now() - timedelta(minutes=2))
        self.assertEqual(self.act(id).data["status"], "sent")
        first = re.search(r"recover-account#[^/]+/([^\s]+)", mail.outbox[-1].body).group(1)
        self.assertEqual(self.act(id).status_code, 400)
        AccountRecovery.objects.filter(pk=id).update(last_attempt_at=timezone.now() - timedelta(minutes=2))
        self.assertEqual(self.act(id).data["status"], "sent")
        self.assertEqual(self.finish(id, first).status_code, 400)

    def test_wrong_expired_and_cancelled_links(self):
        id, token = self.send()
        self.assertEqual(self.finish(id, "x" * 43).status_code, 400)
        AccountRecovery.objects.filter(pk=id).update(token_expires_at=timezone.now() - timedelta(seconds=1))
        self.assertEqual(self.finish(id, token).status_code, 400)
        self.assertEqual(self.act(id, "cancel").status_code, 200)
        self.assertEqual(self.finish(id, token).status_code, 400)

    def test_owner_decline(self):
        id = self.prepare(self.staff).data["id"]
        owner = APIClient(); owner.force_authenticate(self.owner)
        self.assertEqual(owner.post(f"/api/auth/recovery-confirmations/{id}/", {"decision": "decline"}).status_code, 200)
        self.assertEqual(self.act(id).status_code, 409)

    def test_changed_auth_and_membership_invalidates_link(self):
        id, token = self.send()
        revoke_user_refresh_sessions(self.owner)
        self.assertEqual(self.finish(id, token).status_code, 409)

    def test_membership_change_invalidates_link(self):
        id, token = self.send()
        BusinessMember.objects.filter(business=self.business, user=self.owner).update(is_active=False)
        self.assertEqual(self.finish(id, token).status_code, 409)

    def test_platform_and_inactive_target_denied(self):
        BusinessMember.objects.create(business=self.business, user=self.operator, role="admin")
        snapshot = self.api.get(self.root).data
        self.assertNotIn(self.operator.pk, [row["id"] for row in snapshot["candidates"]])
        id, token = self.send()
        User.objects.filter(pk=self.owner.pk).update(is_active=False)
        self.assertEqual(self.finish(id, token).status_code, 409)

    def test_duplicate_request_and_duplicate_email_denied(self):
        self.assertEqual(self.prepare(new_email=self.staff.email.upper()).status_code, 400)
        self.assertEqual(self.prepare().status_code, 200)
        self.assertEqual(self.prepare().status_code, 409)

    def test_cross_business_case_and_action_denied(self):
        other = Business.objects.create(owner=self.staff, name="Other", slug="other")
        case = SupportCase.objects.create(business=other, requester=self.owner, created_by=self.operator, source="platform", subject="Other")
        self.assertEqual(self.prepare(support_case_id=case.pk).status_code, 404)
        id = self.prepare().data["id"]
        response = self.api.post(f"/api/platform/merchants/{other.pk}/account-recovery/{id}/", {"action": "send"}, HTTP_X_ZANI_MFA_STEP_UP=self.step)
        self.assertEqual(response.status_code, 404)

    def test_mfa_role_and_stale_operator_denied(self):
        response = self.prepare(); id = response.data["id"]
        self.assertEqual(self.api.post(f"{self.root}{id}/", {"action": "send"}).status_code, 401)
        User.objects.filter(pk=self.operator.pk).update(role="staff")
        self.assertEqual(self.act(id).status_code, 403)

    def test_merchant_cannot_read_or_write(self):
        self.api.force_authenticate(self.owner)
        self.assertEqual(self.api.get(self.root).status_code, 403)
        self.assertEqual(self.api.post(self.root, {}).status_code, 403)

    def test_audit_failure_rolls_back_complete(self):
        id, token = self.send()
        with patch("apps.accounts.recovery.write_actor_audit_log", side_effect=DatabaseError("audit unavailable")):
            self.assertEqual(self.finish(id, token).status_code, 503)
        self.owner.refresh_from_db()
        self.assertEqual(self.owner.email, "owner@example.com")
        self.assertEqual(self.owner.auth_epoch, 0)
        self.assertEqual(AccountRecovery.objects.get(pk=id).status, "sent")
        self.assertEqual(self.finish(id, token).status_code, 200)

    def test_password_policy_and_unknown_fields(self):
        id, token = self.send()
        self.assertEqual(self.finish(id, token, password="12345678").status_code, 400)
        self.assertEqual(self.finish(id, token, user_id=self.staff.pk).status_code, 400)

    @override_settings(ACCOUNT_RECOVERY_SUPPORT_EMAIL="support@example.test")
    def test_public_contact_only_no_secret_projection(self):
        self.assertEqual(self.public.get("/api/auth/account-recovery/").data, {"support_email": "support@example.test"})
        id, token = self.send()
        data = str(self.api.get(self.root).data)
        self.assertNotIn(token, data)
        self.assertNotIn("token_hash", data)
        self.assertNotIn("code_hash", data)

    @override_settings(EMAIL_BACKEND="django.core.mail.backends.console.EmailBackend")
    def test_console_backend_does_not_print_recovery_link(self):
        id = self.prepare().data["id"]
        with patch("apps.accounts.recovery.send_mail") as send:
            self.assertEqual(self.act(id).data["delivery_status"], "unavailable")
            send.assert_not_called()

    def test_admin_role_can_prepare_and_execute(self):
        self.operator.role = "platform_admin"; self.operator.save(update_fields=["role"])
        id, token = self.send()
        self.assertEqual(self.finish(id, token).status_code, 200)

    def test_owner_auth_change_invalidates_employee_consent(self):
        response = self.prepare(self.staff)
        owner = APIClient(); owner.force_authenticate(self.owner)
        owner.post(f"/api/auth/recovery-confirmations/{response.data['id']}/", {"decision": "confirm"})
        revoke_user_refresh_sessions(self.owner)
        self.assertEqual(self.act(response.data["id"]).status_code, 409)

    def test_stale_operator_and_cross_tenant_target(self):
        id = self.prepare().data["id"]
        User.objects.filter(pk=self.operator.pk).update(auth_epoch=1)
        self.assertEqual(self.act(id).status_code, 403)

    def test_support_case_requester_must_match_target(self):
        from apps.accounts.recovery import revision
        data = {"user_id": self.staff.pk, "support_case_id": self.case.pk, "new_email": "new@example.com",
                "expected_revision": revision(self.staff), "reason": "Identity verified"}
        response = self.api.post(self.root, data, format="json", HTTP_X_ZANI_MFA_STEP_UP=self.step)
        self.assertEqual(response.status_code, 404)

    def test_expired_request_is_replaceable_and_resolved_case_blocks_completion(self):
        id = self.prepare().data["id"]
        AccountRecovery.objects.filter(pk=id).update(expires_at=timezone.now() - timedelta(seconds=1))
        id, token = self.send()
        self.case.status = "resolved"; self.case.resolved_at = timezone.now(); self.case.save()
        self.assertEqual(self.finish(id, token).status_code, 409)


@skipUnless(connection.vendor == "postgresql", "Requires PostgreSQL row locks")
@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend", FRONTEND_URL="https://crm.example.test")
class RecoveryConcurrencyTests(TransactionTestCase):
    setUp = RecoveryTests.setUp
    prepare = RecoveryTests.prepare
    act = RecoveryTests.act
    send = RecoveryTests.send

    def test_only_one_completion_wins(self):
        from apps.accounts.recovery import complete
        id, token = self.send()
        barrier = Barrier(2)
        def worker():
            close_old_connections()
            try:
                barrier.wait(timeout=10)
                try:
                    complete(APIRequestFactory().post("/"), id, token=token, password="NewVerifiedPassword123!")
                    return "completed"
                except ValidationError:
                    return "rejected"
            finally:
                close_old_connections()
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(lambda _: worker(), range(2)))
        self.assertCountEqual(results, ["completed", "rejected"])
        self.owner.refresh_from_db(); self.assertEqual(self.owner.auth_epoch, 1)
        self.assertEqual(AuditLog.objects.filter(metadata__kind="account_recovery", metadata__event="completed").count(), 1)

    def test_only_one_global_request_across_businesses(self):
        from apps.accounts.recovery import prepare, revision
        from apps.businesses.ownership import OwnershipConflict
        other = Business.objects.create(owner=self.owner, name="Other", slug="other")
        case = SupportCase.objects.create(business=other, created_by=self.operator, requester=self.owner, source="platform", subject="Recovery")
        barrier = Barrier(2)
        state = revision(self.owner)
        def worker(pair):
            close_old_connections()
            try:
                request = APIRequestFactory().post("/", HTTP_X_ZANI_MFA_STEP_UP=self.step)
                request.user = User.objects.get(pk=self.operator.pk)
                barrier.wait(timeout=10)
                try:
                    prepare(request, pair[0], user_id=self.owner.pk, support_case_id=pair[1], new_email="recovered@example.com",
                            expected_revision=state, reason="Verified identity", verified_reference="Verified record 42")
                    return "prepared"
                except OwnershipConflict:
                    return "rejected"
            finally:
                close_old_connections()
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(worker, [(self.business.pk, self.case.pk), (other.pk, case.pk)]))
        self.assertCountEqual(results, ["prepared", "rejected"])

    def test_owner_revocation_before_completion_invalidates_consent(self):
        from apps.accounts.recovery import complete
        from apps.businesses.ownership import OwnershipConflict
        item = self.prepare(self.staff).data
        owner = APIClient(); owner.force_authenticate(self.owner)
        owner.post(f"/api/auth/recovery-confirmations/{item['id']}/", {"decision": "confirm"})
        self.assertEqual(self.act(item["id"]).data["status"], "sent")
        token = re.search(r"recover-account#[^/]+/([^\s]+)", mail.outbox[-1].body).group(1)
        started = Event()
        def worker():
            close_old_connections()
            try:
                started.set()
                try:
                    complete(APIRequestFactory().post("/"), item["id"], token=token, password="NewVerifiedPassword123!")
                    return "completed"
                except OwnershipConflict:
                    return "rejected"
            finally:
                close_old_connections()
        with ThreadPoolExecutor(max_workers=1) as pool:
            with transaction.atomic():
                owner = User.objects.select_for_update().get(pk=self.owner.pk)
                future = pool.submit(worker)
                self.assertTrue(started.wait(timeout=5))
                revoke_user_refresh_sessions(owner)
            self.assertEqual(future.result(timeout=15), "rejected")
        self.staff.refresh_from_db(); self.assertEqual(self.staff.email, "employee@example.com")
