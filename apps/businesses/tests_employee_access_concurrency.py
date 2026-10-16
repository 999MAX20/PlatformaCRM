from concurrent.futures import ThreadPoolExecutor
from threading import Barrier, Event
from unittest import skipUnless
from unittest.mock import patch
import uuid
import pyotp

from django.db import connection, close_old_connections, transaction
from django.test import TransactionTestCase
from rest_framework.test import APIClient
from django.utils import timezone

from apps.accounts.models import User, MfaDevice
from apps.accounts.mfa import issue_step_up_token
from apps.integrations.credential_encryption import encrypt_credential_value
from apps.support.models import SupportCase
from apps.businesses.models import Business, BusinessMember
from apps.businesses.tests_employee_access import EmployeeAccessFixture
from apps.core.audit import write_audit_log
from apps.core.models import AuditLog


@skipUnless(connection.vendor == "postgresql", "Real row locks require PostgreSQL")
class EmployeeAccessConcurrencyTests(EmployeeAccessFixture, TransactionTestCase):
    def test_cross_business_people_are_locked_in_stable_order(self):
        other_operator = User.objects.create_user(username="second-support", email="second-support@example.com", role="platform_admin")
        secret = pyotp.random_base32()
        MfaDevice.objects.create(user=other_operator, encrypted_secret=encrypt_credential_value(secret), confirmed_at=timezone.now())
        step = issue_step_up_token(other_operator, pyotp.TOTP(secret).now())
        other = Business.objects.create(owner=self.staff, name="Reverse participants", slug="reverse")
        member = BusinessMember.objects.create(business=other, user=self.owner, role="manager")
        case = SupportCase.objects.create(business=other, created_by=other_operator, requester=self.staff, source="platform", subject="Disable")
        client = APIClient(); client.force_authenticate(other_operator)
        root = f"/api/platform/merchants/{other.pk}/employee-access/"
        row = client.get(root).data["members"][0]
        response = client.post(root, {"request_id": str(uuid.uuid4()), "target_id": member.pk, "action": "disable",
            "expected_revision": row["revision"], "support_case_id": case.pk, "reason": "Verified request"}, format="json", HTTP_X_ZANI_MFA_STEP_UP=step)
        self.assertEqual(response.status_code, 200, response.data)
        id = self.prepare().data["id"]
        barrier = Barrier(2)
        def second():
            close_old_connections()
            try:
                barrier.wait(timeout=10)
                return client.post(f"{root}{response.data['id']}/", {"action": "execute"}, HTTP_X_ZANI_MFA_STEP_UP=step).status_code
            finally:
                close_old_connections()
        def first():
            barrier.wait(timeout=10)
            return self.worker_execute(id)
        with ThreadPoolExecutor(max_workers=2) as executor:
            futures = [executor.submit(first), executor.submit(second)]
            self.assertEqual([future.result(timeout=20) for future in futures], [200, 200])
        self.member.refresh_from_db(); member.refresh_from_db()
        self.assertFalse(self.member.is_active or member.is_active)

    def worker_execute(self, id):
        close_old_connections()
        try:
            client = APIClient(); client.force_authenticate(self.operator)
            response = client.post(f"{self.root}{id}/", {"action": "execute"}, format="json", HTTP_X_ZANI_MFA_STEP_UP=self.step)
            return response.status_code
        finally:
            close_old_connections()

    def test_concurrent_execute_has_one_effect_and_one_audit(self):
        id = self.prepare().data["id"]
        barrier = Barrier(2)
        def execute():
            barrier.wait(timeout=10)
            return self.worker_execute(id)
        with ThreadPoolExecutor(max_workers=2) as executor:
            futures = [executor.submit(execute) for _ in range(2)]
            self.assertEqual([future.result(timeout=20) for future in futures], [200, 200])
        self.member.refresh_from_db(); self.assertFalse(self.member.is_active)
        self.assertEqual(AuditLog.objects.filter(metadata__kind="employee_access_repair", metadata__event="completed").count(), 1)

    def test_accept_waits_for_reissue_and_rejects_old_token(self):
        old = str(self.invitation.token)
        id = self.prepare("reissue").data["id"]
        self.assertEqual(self.confirm(id).status_code, 200)
        written, release, accepting = Event(), Event(), Event()
        def audit(*args, **kwargs):
            if kwargs.get("metadata", {}).get("event") == "completed":
                written.set()
                if not release.wait(timeout=10):
                    raise RuntimeError("test release timeout")
            return write_audit_log(*args, **kwargs)
        def accept():
            close_old_connections()
            try:
                accepting.set()
                return APIClient().post("/api/team/invitations/accept/", {"token": old, "password": "SafePassword123!"}).status_code
            finally:
                close_old_connections()
        with patch("apps.businesses.employee_access.write_audit_log", side_effect=audit), ThreadPoolExecutor(max_workers=2) as executor:
            repair = executor.submit(self.worker_execute, id)
            try:
                self.assertTrue(written.wait(timeout=10))
                consumer = executor.submit(accept)
                self.assertTrue(accepting.wait(timeout=10))
                self.assertFalse(consumer.done())
            finally:
                release.set()
            self.assertEqual(repair.result(timeout=20), 200)
            self.assertEqual(consumer.result(timeout=20), 400)
        self.invitation.refresh_from_db()
        self.assertNotEqual(str(self.invitation.token), old)
        self.assertIsNone(self.invitation.accepted_at)

    def test_concurrent_member_change_invalidates_owner_consent(self):
        self.member.is_active = False; self.member.save()
        id = self.prepare("restore").data["id"]
        self.assertEqual(self.confirm(id).status_code, 200)
        changed, release = Event(), Event()
        def edit():
            close_old_connections()
            try:
                with transaction.atomic():
                    Business.objects.select_for_update().get(pk=self.business.pk)
                    BusinessMember.objects.filter(pk=self.member.pk).update(role="manager")
                    changed.set()
                    if not release.wait(timeout=10):
                        raise RuntimeError("test release timeout")
            finally:
                close_old_connections()
        with ThreadPoolExecutor(max_workers=2) as executor:
            edit_future = executor.submit(edit)
            try:
                self.assertTrue(changed.wait(timeout=10))
                repair = executor.submit(self.worker_execute, id)
            finally:
                release.set()
            edit_future.result(timeout=20)
            self.assertEqual(repair.result(timeout=20), 409)
        self.member.refresh_from_db(); self.assertFalse(self.member.is_active)
