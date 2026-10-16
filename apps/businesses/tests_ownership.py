from concurrent.futures import ThreadPoolExecutor
from threading import Barrier, Event
from unittest import skipUnless
from unittest.mock import patch

import pyotp
from django.db import DatabaseError, close_old_connections, connection, transaction
from django.test import TestCase, TransactionTestCase
from django.utils import timezone
from rest_framework.test import APIClient, APIRequestFactory

from apps.accounts.mfa import issue_session, issue_step_up_token
from apps.accounts.models import MfaDevice, User
from apps.businesses.access import ensure_owner_memberships_for_user
from apps.businesses.models import Business, BusinessMember, BusinessOwnershipTransfer, BusinessRole
from apps.businesses.ownership import finish_transfer
from apps.core.models import AuditLog
from apps.integrations.credential_encryption import encrypt_credential_value
from apps.support.models import SupportCase


class OwnershipFixture:
    def setUp(self):
        self.owner = User.objects.create_user(username="owner", email="owner@example.com", role="business_owner")
        self.recipient = User.objects.create_user(username="recipient", email="recipient@example.com", role="staff")
        self.admin = User.objects.create_user(username="platform", email="platform@example.com", role="platform_admin")
        self.manager = User.objects.create_user(username="platform-manager", email="platform-manager@example.com", role="platform_manager")
        self.stranger = User.objects.create_user(username="stranger", email="stranger@example.com", role="staff")
        self.business = Business.objects.create(owner=self.owner, name="Ownership business", slug="ownership")
        self.owner_role = BusinessRole.objects.create(business=self.business, name="Owner", preset_key="owner")
        self.employee_role = BusinessRole.objects.create(business=self.business, name="Specialist", preset_key="specialist")
        self.old_member = BusinessMember.objects.create(business=self.business, user=self.owner, role="owner", business_role=self.owner_role)
        self.new_member = BusinessMember.objects.create(business=self.business, user=self.recipient, role="specialist", business_role=self.employee_role)
        self.case = SupportCase.objects.create(business=self.business, requester=self.owner, created_by=self.owner, source="clinic", subject="Transfer")
        secret = pyotp.random_base32()
        MfaDevice.objects.create(user=self.admin, encrypted_secret=encrypt_credential_value(secret), confirmed_at=timezone.now())
        self.token = issue_step_up_token(self.admin, pyotp.TOTP(secret).now())
        self.api = APIClient()
        self.api.force_authenticate(self.admin)
        self.url = f"/api/platform/merchants/{self.business.pk}/ownership/"
        self.payload = {"new_owner_id": self.recipient.pk, "expected_owner_id": self.owner.pk,
            "previous_owner_business_role_id": self.employee_role.pk, "support_case_id": self.case.pk,
            "reason": "Confirmed transfer of business ownership"}

    def prepare(self, **changes):
        return self.api.post(self.url, {**self.payload, **changes}, format="json", HTTP_X_ZANI_MFA_STEP_UP=self.token)

    def confirm(self, transfer_id, actor, decision="confirm"):
        api = APIClient()
        api.force_authenticate(actor)
        return api.post(f"/api/auth/ownership-transfers/{transfer_id}/decision/", {"decision": decision}, format="json")

    def ready(self, **changes):
        response = self.prepare(**changes)
        self.assertEqual(response.status_code, 200, response.data)
        transfer_id = response.data["id"]
        for actor in (self.owner, self.recipient):
            response = self.confirm(transfer_id, actor)
            self.assertEqual(response.status_code, 200, response.data)
        return transfer_id

    def execute(self, transfer_id, action="execute"):
        return self.api.post(f"{self.url}{transfer_id}/", {"action": action}, format="json", HTTP_X_ZANI_MFA_STEP_UP=self.token)


class OwnershipTests(OwnershipFixture, TestCase):
    def test_complete_preserves_identity_history_and_other_business_membership(self):
        other = Business.objects.create(owner=self.owner, name="Other", slug="other")
        other_member = BusinessMember.objects.create(business=other, user=self.recipient, role="manager")
        transfer_id = self.ready()
        result = self.execute(transfer_id)
        self.assertEqual(result.status_code, 200, result.data)
        self.assertEqual(result.data["status"], "completed")
        self.assertIn("no-store", result["Cache-Control"])
        self.business.refresh_from_db(); self.old_member.refresh_from_db(); self.new_member.refresh_from_db()
        self.assertEqual(self.business.owner_id, self.recipient.pk)
        self.assertEqual((self.old_member.role, self.old_member.business_role_id, self.old_member.is_active), ("specialist", self.employee_role.pk, True))
        self.assertEqual((self.new_member.role, self.new_member.business_role_id), ("owner", self.owner_role.pk))
        self.owner.refresh_from_db(); self.recipient.refresh_from_db(); other.refresh_from_db(); other_member.refresh_from_db()
        self.assertEqual((self.owner.role, self.recipient.role), ("business_owner", "staff"))
        self.assertEqual(other.owner_id, self.owner.pk)
        self.assertEqual(other_member.role, "manager")
        self.case.refresh_from_db()
        self.assertEqual(self.case.created_by_id, self.owner.pk)
        audit = AuditLog.objects.get(metadata__event="completed", metadata__kind="business_ownership_transfer")
        self.assertEqual(audit.actor_id, self.admin.pk)
        self.assertEqual(audit.metadata["support_case_id"], self.case.pk)
        self.assertNotIn("@", str(audit.metadata))
        self.assertEqual((self.owner.auth_epoch, self.recipient.auth_epoch), (1, 1))
        self.assertEqual(self.execute(transfer_id).status_code, 409)

    def test_disable_is_business_local_and_profile_cannot_restore_old_owner(self):
        from apps.scheduling.models import Resource
        specialist = Resource.objects.create(business=self.business, name="Previous owner specialist", linked_user=self.owner)
        transfer_id = self.ready(previous_owner_business_role_id=None)
        self.assertEqual(self.execute(transfer_id).status_code, 200)
        self.owner.refresh_from_db()
        ensure_owner_memberships_for_user(self.owner)
        self.old_member.refresh_from_db()
        self.assertFalse(self.old_member.is_active)
        self.assertNotEqual(self.old_member.role, "owner")
        self.assertTrue(self.owner.is_active)
        from apps.core.permissions import user_can_access_business
        self.business.refresh_from_db()
        self.assertFalse(user_can_access_business(self.owner, self.business))
        specialist.refresh_from_db()
        self.assertTrue(specialist.is_active)
        self.assertEqual(specialist.linked_user_id, self.owner.pk)

    def test_revoke_actual_access_credentials_for_both_participants(self):
        old_access = str(issue_session(self.owner).access_token)
        new_access = str(issue_session(self.recipient).access_token)
        for token in (old_access, new_access):
            client = APIClient(); client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
            self.assertEqual(client.get("/api/auth/me/").status_code, 200)
        transfer_id = self.ready()
        self.assertEqual(self.execute(transfer_id).status_code, 200)
        for token in (old_access, new_access):
            client = APIClient()
            client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
            self.assertEqual(client.get("/api/auth/me/").status_code, 401)

    def test_new_owner_requires_privileged_mfa_and_old_role_does_not_grant_owner_permissions(self):
        from apps.accounts.mfa import requires_mfa
        from apps.businesses.access import Actions, Resources, can
        transfer_id = self.ready()
        self.assertEqual(self.execute(transfer_id).status_code, 200)
        self.business.refresh_from_db(); self.owner.refresh_from_db(); self.recipient.refresh_from_db()
        with self.settings(AUTH_PRIVILEGED_MFA_REQUIRED=True):
            self.assertTrue(requires_mfa(self.recipient))
        self.assertFalse(can(self.owner, self.business, Resources.TEAM, Actions.MANAGE).allowed)
        self.assertTrue(can(self.recipient, self.business, Resources.TEAM, Actions.MANAGE).allowed)

    def test_member_crud_cannot_delete_or_deactivate_new_owner(self):
        transfer_id = self.ready()
        self.assertEqual(self.execute(transfer_id).status_code, 200)
        self.recipient.refresh_from_db()
        client = APIClient(); client.force_authenticate(self.recipient)
        for root in ("business-members", "team/members"):
            url = f"/api/{root}/{self.new_member.pk}/"
            self.assertEqual(client.patch(url, {"is_active": False}, format="json").status_code, 400)
            self.assertEqual(client.delete(url).status_code, 400)

    def test_serializer_validated_before_transfer_cannot_overwrite_new_owner(self):
        from apps.businesses.views import BusinessMemberViewSet, TeamMemberManagementViewSet
        from rest_framework.exceptions import ValidationError
        from rest_framework.request import Request
        views = []
        for cls in (BusinessMemberViewSet, TeamMemberManagementViewSet):
            view = cls(); view.action = "partial_update"; view.format_kwarg = None
            view.kwargs = {"pk": self.new_member.pk}
            request = Request(APIRequestFactory().patch("/", {"is_active": False}, format="json"))
            request.user = self.owner; view.request = request
            serializer = view.get_serializer(BusinessMember.objects.get(pk=self.new_member.pk), data={"is_active": False}, partial=True)
            serializer.is_valid(raise_exception=True)
            views.append((view, serializer))
        transfer_id = self.ready()
        self.assertEqual(self.execute(transfer_id).status_code, 200)
        self.recipient.refresh_from_db()
        for view, serializer in views:
            view.request.user = self.recipient
            with self.assertRaises(ValidationError):
                view.perform_update(serializer)
        self.new_member.refresh_from_db()
        self.assertEqual((self.new_member.role, self.new_member.is_active), ("owner", True))

    def test_read_permissions_and_manager_cannot_prepare_or_execute(self):
        for actor in (self.admin, self.manager):
            self.api.force_authenticate(actor)
            response = self.api.get(self.url)
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.data["can_prepare"], actor == self.admin)
        self.assertEqual(self.prepare().status_code, 403)
        self.api.force_authenticate(self.admin)
        transfer_id = self.ready()
        self.api.force_authenticate(self.manager)
        self.assertEqual(self.execute(transfer_id).status_code, 403)
        self.api.force_authenticate(self.owner)
        self.assertEqual(self.api.get(self.url).status_code, 403)

    def test_mfa_and_fresh_database_role_required(self):
        self.assertEqual(self.api.post(self.url, self.payload, format="json").status_code, 401)
        User.objects.filter(pk=self.admin.pk).update(role="platform_manager")
        self.assertEqual(self.prepare().status_code, 403)

    def test_strict_input_foreign_case_role_and_inactive_recipient(self):
        foreign = Business.objects.create(owner=self.stranger, name="Foreign", slug="foreign")
        case = SupportCase.objects.create(business=foreign, created_by=self.stranger, requester=self.stranger, subject="Foreign", source="clinic")
        role = BusinessRole.objects.create(business=foreign, name="Foreign", preset_key="admin")
        for changes, status in [({"support_case_id": case.pk}, 404), ({"previous_owner_business_role_id": role.pk}, 404),
                                ({"previous_owner_business_role_id": self.owner_role.pk}, 400),
                                ({"new_owner_id": self.stranger.pk}, 400), ({"new_owner_id": self.owner.pk}, 400),
                                ({"expected_owner_id": self.stranger.pk}, 409), ({"reason": " "}, 400), ({"owner": self.stranger.pk}, 400)]:
            response = self.prepare(**changes)
            self.assertEqual(response.status_code, status, response.data)
        self.new_member.is_active = False; self.new_member.save()
        self.assertEqual(self.prepare().status_code, 400)
        self.assertFalse(BusinessOwnershipTransfer.objects.exists())

    def test_both_consents_required_and_unrelated_user_cannot_read_or_confirm(self):
        transfer_id = self.prepare().data["id"]
        self.assertEqual(self.execute(transfer_id).status_code, 400)
        self.assertEqual(self.confirm(transfer_id, self.owner).status_code, 200)
        self.assertEqual(self.execute(transfer_id).status_code, 400)
        self.assertEqual(self.confirm(transfer_id, self.stranger).status_code, 404)
        client = APIClient(); client.force_authenticate(self.stranger)
        self.assertEqual(client.get("/api/auth/ownership-transfers/").data["results"], [])
        self.assertEqual(self.confirm(transfer_id, self.recipient).status_code, 200)
        self.assertEqual(self.execute(transfer_id).status_code, 200)

    def test_confirmation_is_idempotent_but_mutable_terms_are_rejected(self):
        transfer_id = self.prepare().data["id"]
        for _ in range(2):
            self.assertEqual(self.confirm(transfer_id, self.owner).status_code, 200)
        self.assertEqual(AuditLog.objects.filter(metadata__event="previous_owner_confirmed").count(), 1)
        self.employee_role.name = "Different profile"; self.employee_role.save()
        self.assertEqual(self.confirm(transfer_id, self.recipient).status_code, 409)

    def test_changed_membership_and_epoch_invalidate_completion(self):
        transfer_id = self.ready()
        self.recipient.auth_epoch += 1; self.recipient.save()
        self.assertEqual(self.execute(transfer_id).status_code, 409)
        self.recipient.auth_epoch = 0; self.recipient.save()
        self.new_member.role = "operator"; self.new_member.save()
        self.assertEqual(self.execute(transfer_id).status_code, 409)
        self.business.refresh_from_db()
        self.assertEqual(self.business.owner_id, self.owner.pk)

    def test_disabled_account_after_consent_is_rejected(self):
        transfer_id = self.ready()
        self.recipient.is_active = False; self.recipient.save()
        self.assertEqual(self.execute(transfer_id).status_code, 400)

    def test_decline_and_expiry_prevent_transfer_and_allow_new_request(self):
        transfer_id = self.prepare().data["id"]
        self.assertEqual(self.prepare().status_code, 409)
        self.assertEqual(self.confirm(transfer_id, self.recipient, "decline").status_code, 200)
        self.assertEqual(self.execute(transfer_id).status_code, 409)
        transfer_id = self.ready()
        BusinessOwnershipTransfer.objects.filter(pk=transfer_id).update(expires_at=timezone.now())
        self.assertEqual(self.execute(transfer_id).status_code, 409)
        self.assertEqual(self.prepare().status_code, 200)

    def test_audit_failure_rolls_back_transfer_memberships_and_revocation_then_retry(self):
        transfer_id = self.ready()
        with patch("apps.businesses.ownership.write_audit_log", side_effect=DatabaseError("audit unavailable")):
            self.assertEqual(self.execute(transfer_id).status_code, 503)
        self.business.refresh_from_db(); self.old_member.refresh_from_db(); self.new_member.refresh_from_db()
        self.owner.refresh_from_db(); self.recipient.refresh_from_db()
        self.assertEqual(self.business.owner_id, self.owner.pk)
        self.assertEqual((self.old_member.role, self.new_member.role), ("owner", "specialist"))
        self.assertEqual((self.owner.auth_epoch, self.recipient.auth_epoch), (0, 0))
        self.assertEqual(BusinessOwnershipTransfer.objects.get(pk=transfer_id).status, "pending")
        self.assertEqual(self.execute(transfer_id).status_code, 200)

    def test_foreign_business_action_and_unknown_action_rejected(self):
        transfer_id = self.ready()
        other = Business.objects.create(owner=self.owner, name="Other", slug="other")
        result = self.api.post(f"/api/platform/merchants/{other.pk}/ownership/{transfer_id}/", {"action": "execute"}, format="json", HTTP_X_ZANI_MFA_STEP_UP=self.token)
        self.assertEqual(result.status_code, 404)
        self.assertEqual(self.execute(transfer_id, "recovery_override").status_code, 400)


@skipUnless(connection.vendor == "postgresql", "Real row-lock concurrency requires PostgreSQL")
class OwnershipConcurrencyTests(OwnershipFixture, TransactionTestCase):
    def test_role_change_committing_during_transfer_invalidates_consent(self):
        transfer_id = self.ready()
        started = Event()
        def execute():
            close_old_connections()
            try:
                client = APIClient(); client.force_authenticate(User.objects.get(pk=self.admin.pk))
                started.set()
                return client.post(f"{self.url}{transfer_id}/", {"action": "execute"}, format="json", HTTP_X_ZANI_MFA_STEP_UP=self.token).status_code
            finally:
                close_old_connections()
        with ThreadPoolExecutor(max_workers=1) as pool:
            with transaction.atomic():
                role = BusinessRole.objects.select_for_update().get(pk=self.employee_role.pk)
                future = pool.submit(execute)
                self.assertTrue(started.wait(timeout=10))
                role.name = "Changed during transfer"
                role.save(update_fields=["name", "updated_at"])
            self.assertEqual(future.result(timeout=10), 409)
        self.business.refresh_from_db()
        self.assertEqual(self.business.owner_id, self.owner.pk)

    def test_two_executions_have_one_winner(self):
        transfer_id = self.ready()
        barrier = Barrier(2)
        def execute():
            close_old_connections()
            try:
                client = APIClient(); client.force_authenticate(User.objects.get(pk=self.admin.pk))
                barrier.wait(timeout=10)
                return client.post(f"{self.url}{transfer_id}/", {"action": "execute"}, format="json", HTTP_X_ZANI_MFA_STEP_UP=self.token).status_code
            finally:
                close_old_connections()
        with ThreadPoolExecutor(max_workers=2) as pool:
            outcomes = list(pool.map(lambda _: execute(), range(2)))
        self.assertEqual(sorted(outcomes), [200, 409])
        self.assertEqual(AuditLog.objects.filter(metadata__event="completed").count(), 1)
        self.assertEqual(BusinessMember.objects.filter(business=self.business, role="owner").count(), 1)

    def test_concurrent_profile_repair_cannot_restore_previous_owner(self):
        transfer_id = self.ready(previous_owner_business_role_id=None)
        started = Event()
        def profile():
            close_old_connections()
            try:
                started.set()
                ensure_owner_memberships_for_user(User.objects.get(pk=self.owner.pk))
            finally:
                close_old_connections()
        with ThreadPoolExecutor(max_workers=1) as pool:
            with transaction.atomic():
                Business.objects.select_for_update().get(pk=self.business.pk)
                future = pool.submit(profile)
                self.assertTrue(started.wait(timeout=10))
                request = APIRequestFactory().post("/", HTTP_X_ZANI_MFA_STEP_UP=self.token)
                from rest_framework.request import Request
                request = Request(request); request.user = self.admin
                finish_transfer(request, self.business.pk, transfer_id, action="execute")
            future.result(timeout=10)
        self.old_member.refresh_from_db()
        self.assertFalse(self.old_member.is_active)
        self.assertNotEqual(self.old_member.role, "owner")
