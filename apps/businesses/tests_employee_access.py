import uuid
from datetime import timedelta
from unittest.mock import patch

import pyotp
from django.core.cache import cache
from django.db import DatabaseError
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounts.mfa import issue_step_up_token
from apps.accounts.models import MfaDevice, User
from apps.businesses.models import Business, BusinessMember, BusinessInvitation, BusinessRole, EmployeeAccessRepair, RolePermission
from apps.core.models import AuditLog
from apps.integrations.credential_encryption import encrypt_credential_value
from apps.scheduling.models import Resource
from apps.support.models import SupportCase
from apps.clients.models import Client
from apps.tasks.models import Task
from apps.activities.models import ActivityEvent
from rest_framework_simplejwt.tokens import AccessToken


class EmployeeAccessFixture:
    def setUp(self):
        cache.clear()
        self.owner = User.objects.create_user(username="owner", email="owner@example.com", role="business_owner")
        self.staff = User.objects.create_user(username="staff", email="staff@example.com", role="staff")
        self.operator = User.objects.create_user(username="support", email="support@example.com", role="platform_manager")
        self.business = Business.objects.create(owner=self.owner, name="Business", slug="access")
        self.other = Business.objects.create(owner=self.owner, name="Other", slug="other")
        self.owner_member = BusinessMember.objects.create(business=self.business, user=self.owner, role="owner")
        self.role = BusinessRole.objects.create(business=self.business, name="Specialist", preset_key="specialist")
        self.member = BusinessMember.objects.create(business=self.business, user=self.staff, role="specialist", business_role=self.role)
        self.other_member = BusinessMember.objects.create(business=self.other, user=self.staff, role="manager")
        self.resource = Resource.objects.create(business=self.business, linked_user=self.staff, name="Specialist")
        Resource.objects.create(business=self.other, linked_user=self.staff, name="PRIVATE other specialist")
        self.invitation = BusinessInvitation.objects.create(business=self.business, email="invite@example.com", business_role=self.role,
            expires_at=timezone.now() + timedelta(days=7))
        self.case = SupportCase.objects.create(business=self.business, created_by=self.operator, requester=self.owner, source="platform", subject="Employee access")
        secret = pyotp.random_base32()
        MfaDevice.objects.create(user=self.operator, encrypted_secret=encrypt_credential_value(secret), confirmed_at=timezone.now())
        self.step = issue_step_up_token(self.operator, pyotp.TOTP(secret).now())
        self.api = APIClient(); self.api.force_authenticate(self.operator)
        self.owner_api = APIClient(); self.owner_api.force_authenticate(self.owner)
        self.root = f"/api/platform/merchants/{self.business.pk}/employee-access/"

    def data(self, action="disable", target=None, **overrides):
        target = target or (self.invitation if action in {"reissue", "revoke"} else self.member)
        snapshot = self.api.get(self.root)
        self.assertEqual(snapshot.status_code, 200, snapshot.data)
        key = "members" if isinstance(target, BusinessMember) else "invitations"
        revision = next(row["revision"] for row in snapshot.data[key] if row["id"] == target.pk)
        return {"request_id": str(uuid.uuid4()), "action": action, "target_id": target.pk,
            "expected_revision": revision, "support_case_id": self.case.pk, "reason": "Verified support request", **overrides}

    def prepare(self, action="disable", target=None, **overrides):
        return self.api.post(self.root, self.data(action, target, **overrides), format="json", HTTP_X_ZANI_MFA_STEP_UP=self.step)

    def execute(self, id, action="execute"):
        return self.api.post(f"{self.root}{id}/", {"action": action}, format="json", HTTP_X_ZANI_MFA_STEP_UP=self.step)

    def confirm(self, id, decision="confirm", api=None):
        return (api or self.owner_api).post(f"/api/auth/employee-access-confirmations/{id}/", {"decision": decision}, format="json")

class EmployeeAccessTests(EmployeeAccessFixture, TestCase):
    def test_existing_session_loses_only_selected_business_and_history_stays(self):
        self.member.role = "manager"; self.member.business_role = None; self.member.save()
        customer = Client.objects.create(business=self.business, full_name="Retained client")
        other_customer = Client.objects.create(business=self.other, full_name="Other client")
        task = Task.objects.create(business=self.business, title="Retained work", assignee=self.staff)
        event = ActivityEvent.objects.create(business=self.business, client=customer, actor=self.staff,
            event_type="client_updated", text="Retained history")
        token = AccessToken.for_user(self.staff); token["auth_epoch"] = self.staff.auth_epoch
        staff_api = APIClient(); staff_api.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
        self.assertEqual(staff_api.get(f"/api/clients/{customer.pk}/").status_code, 200)
        self.assertEqual(staff_api.get(f"/api/clients/{other_customer.pk}/").status_code, 200)
        id = self.prepare().data["id"]; self.assertEqual(self.execute(id).status_code, 200)
        self.assertEqual(staff_api.get(f"/api/clients/{customer.pk}/").status_code, 404)
        self.assertEqual(staff_api.get(f"/api/clients/{other_customer.pk}/").status_code, 200)
        task.refresh_from_db(); event.refresh_from_db()
        self.assertEqual(task.assignee_id, self.staff.pk); self.assertEqual(event.actor_id, self.staff.pk)

    def test_invitation_cannot_overwrite_owner_or_use_unavailable_role(self):
        self.invitation.email = self.owner.email; self.invitation.save()
        response = self.owner_api.post("/api/team/invitations/accept/", {"token": str(self.invitation.token)})
        self.assertEqual(response.status_code, 400)
        self.owner_member.refresh_from_db(); self.assertEqual(self.owner_member.role, "owner")
        self.invitation.email = "new@example.com"; self.invitation.save()
        self.role.is_active = False; self.role.save()
        self.assertEqual(APIClient().post("/api/team/invitations/accept/", {"token": str(self.invitation.token), "password": "SafePassword123!"}).status_code, 400)
        self.assertFalse(User.objects.filter(email="new@example.com").exists())

    def test_deleted_target_keeps_request_history_without_enabling_execution(self):
        id = self.prepare().data["id"]
        self.member.delete()
        response = self.api.get(self.root)
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data["requests"][0]["target_email"], self.staff.email)
        self.assertEqual(self.execute(id).status_code, 404)

    def test_repair_id_is_bound_to_business_and_confirmation_owner(self):
        id = self.prepare("reissue").data["id"]
        response = self.api.post(f"/api/platform/merchants/{self.other.pk}/employee-access/{id}/", {"action": "execute"}, HTTP_X_ZANI_MFA_STEP_UP=self.step)
        self.assertEqual(response.status_code, 404)
        Business.objects.filter(pk=self.business.pk).update(owner=self.staff)
        self.assertEqual(self.owner_api.get("/api/auth/employee-access-confirmations/").data["results"], [])
        self.assertEqual(self.confirm(id).status_code, 409)

    def test_audit_failure_rolls_back_invitation_rotation(self):
        old = self.invitation.token
        id = self.prepare("reissue").data["id"]
        self.assertEqual(self.confirm(id).status_code, 200)
        with patch("apps.businesses.employee_access.write_audit_log", side_effect=DatabaseError("unavailable")):
            self.assertEqual(self.execute(id).status_code, 503)
        self.invitation.refresh_from_db(); self.assertEqual(self.invitation.token, old)
        self.assertEqual(EmployeeAccessRepair.objects.get(pk=id).status, "pending")

    def test_disable_preserves_account_specialist_history_other_business(self):
        original = (self.staff.password, self.staff.auth_epoch, self.other_member.role)
        response = self.prepare()
        self.assertEqual(response.status_code, 200, response.data)
        id = response.data["id"]
        self.assertEqual(self.execute(id).status_code, 200)
        self.member.refresh_from_db(); self.staff.refresh_from_db(); self.resource.refresh_from_db(); self.other_member.refresh_from_db()
        self.assertFalse(self.member.is_active)
        self.assertTrue(self.staff.is_active and self.resource.is_active and self.other_member.is_active)
        self.assertEqual((self.staff.password, self.staff.auth_epoch, self.other_member.role), original)
        self.assertEqual(self.execute(id).status_code, 200)
        self.assertEqual(AuditLog.objects.filter(metadata__kind="employee_access_repair", metadata__event="completed").count(), 1)

    def test_restore_requires_personal_owner_consent_and_preserves_role(self):
        self.member.is_active = False; self.member.save()
        response = self.prepare("restore"); self.assertEqual(response.status_code, 200, response.data)
        id = response.data["id"]
        self.assertEqual(self.execute(id).status_code, 400)
        self.assertEqual(self.confirm(id, api=self.api).status_code, 404)
        self.assertEqual(len(self.owner_api.get("/api/auth/employee-access-confirmations/").data["results"]), 1)
        self.assertEqual(self.confirm(id).status_code, 200)
        self.assertEqual(self.execute(id).status_code, 200)
        self.member.refresh_from_db(); self.assertTrue(self.member.is_active)
        self.assertEqual(self.member.business_role_id, self.role.pk)

    def test_role_change_requires_owner_and_updates_both_role_fields(self):
        role = BusinessRole.objects.create(business=self.business, name="Manager", preset_key="manager")
        response = self.prepare("role", target_role_id=role.pk)
        self.assertEqual(response.status_code, 200, response.data)
        id = response.data["id"]
        self.assertEqual(self.confirm(id).status_code, 200)
        self.assertEqual(self.execute(id).status_code, 200)
        self.member.refresh_from_db(); self.assertEqual(self.member.role, "manager")
        self.assertEqual(self.member.business_role_id, role.pk)

    def test_reissue_rotates_old_token_only_after_consent_and_is_idempotent(self):
        old = self.invitation.token
        data = self.data("reissue")
        response = self.api.post(self.root, data, format="json", HTTP_X_ZANI_MFA_STEP_UP=self.step)
        self.assertEqual(response.status_code, 200, response.data)
        repeated = self.api.post(self.root, data, format="json", HTTP_X_ZANI_MFA_STEP_UP=self.step)
        self.assertEqual(repeated.data["id"], response.data["id"])
        id = response.data["id"]
        self.assertEqual(self.execute(id).status_code, 400)
        self.assertEqual(self.confirm(id).status_code, 200)
        self.assertEqual(self.execute(id).status_code, 200)
        self.invitation.refresh_from_db(); new = self.invitation.token
        self.assertNotEqual(old, new)
        self.assertEqual(self.execute(id).status_code, 200)
        self.invitation.refresh_from_db(); self.assertEqual(self.invitation.token, new)
        client = APIClient()
        self.assertEqual(client.post("/api/team/invitations/accept/", {"token": str(old), "password": "SafePassword123!"}).status_code, 400)
        accepted = client.post("/api/team/invitations/accept/", {"token": str(new), "password": "SafePassword123!"})
        self.assertEqual(accepted.status_code, 200, getattr(accepted, "data", None))
        self.assertNotIn(str(new), str(self.api.get(self.root).data))
        self.assertNotIn(str(new), str(list(AuditLog.objects.values_list("metadata", flat=True))))

    def test_revoke_does_not_require_owner(self):
        response = self.prepare("revoke"); self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(self.execute(response.data["id"]).status_code, 200)
        self.invitation.refresh_from_db(); self.assertEqual(self.invitation.status, "revoked")

    def test_global_disabled_cannot_be_restored(self):
        self.staff.is_active = False; self.staff.save()
        self.member.is_active = False; self.member.save()
        self.assertEqual(self.prepare("restore").status_code, 400)
        self.staff.refresh_from_db(); self.assertFalse(self.staff.is_active)

    def test_owner_protection_and_wrong_business_entities(self):
        self.assertEqual(self.prepare(target=self.owner_member).status_code, 403)
        data = self.data(); data["target_id"] = self.other_member.pk
        self.assertEqual(self.api.post(self.root, data, format="json", HTTP_X_ZANI_MFA_STEP_UP=self.step).status_code, 404)
        foreign = BusinessRole.objects.create(business=self.other, name="Foreign", preset_key="manager")
        self.assertEqual(self.prepare("role", target_role_id=foreign.pk).status_code, 404)
        owner_role = BusinessRole.objects.create(business=self.business, name="Owner", preset_key="owner")
        self.assertEqual(self.prepare("role", target_role_id=owner_role.pk).status_code, 400)
        foreign_case = SupportCase.objects.create(business=self.other, created_by=self.operator, requester=self.owner, source="platform", subject="Other")
        self.assertEqual(self.prepare(support_case_id=foreign_case.pk).status_code, 404)

    def test_both_platform_roles_mfa_and_stale_actor_denial(self):
        data = self.data()
        denied = self.api.post(self.root, data, format="json")
        self.assertEqual(denied.status_code, 401)
        self.assertEqual(denied.data["code"], "mfa_step_up_required")
        self.assertEqual(self.owner_api.get(self.root).status_code, 403)
        User.objects.filter(pk=self.operator.pk).update(role="platform_admin")
        self.operator.refresh_from_db(); self.api.force_authenticate(self.operator)
        self.assertEqual(self.prepare().status_code, 200)
        User.objects.filter(pk=self.operator.pk).update(role="staff")
        self.assertEqual(self.api.get(self.root).status_code, 403)
        self.assertEqual(self.api.post(self.root, data, format="json", HTTP_X_ZANI_MFA_STEP_UP=self.step).status_code, 403)

    def test_stale_target_owner_epoch_and_expiry_reject(self):
        self.member.is_active = False; self.member.save()
        id = self.prepare("restore").data["id"]
        self.assertEqual(self.confirm(id).status_code, 200)
        User.objects.filter(pk=self.owner.pk).update(auth_epoch=1)
        self.assertEqual(self.execute(id).status_code, 409)
        User.objects.filter(pk=self.owner.pk).update(auth_epoch=0)
        EmployeeAccessRepair.objects.filter(pk=id).update(expires_at=timezone.now() - timedelta(seconds=1))
        self.assertEqual(self.execute(id).status_code, 409)
        self.assertEqual(self.api.get(self.root).data["requests"][0]["status"], "expired")
        second = self.prepare("restore").data["id"]
        BusinessMember.objects.filter(pk=self.member.pk).update(role="manager")
        self.assertEqual(self.confirm(second).status_code, 409)

    def test_role_permission_change_invalidates_consent(self):
        role = BusinessRole.objects.create(business=self.business, name="Custom")
        id = self.prepare("role", target_role_id=role.pk).data["id"]
        self.assertEqual(self.confirm(id).status_code, 200)
        RolePermission.objects.create(business_role=role, resource="tasks", action="manage", scope="business")
        self.assertEqual(self.execute(id).status_code, 409)

    def test_cancel_decline_and_closed_case(self):
        id = self.prepare().data["id"]
        self.assertEqual(self.execute(id, "cancel").status_code, 200)
        self.assertEqual(self.execute(id, "cancel").status_code, 200)
        self.assertEqual(self.execute(id).status_code, 409)
        id = self.prepare("reissue").data["id"]
        self.assertEqual(self.confirm(id, "decline").status_code, 200)
        self.assertEqual(self.execute(id).status_code, 409)
        id = self.prepare().data["id"]
        self.case.status = "resolved"; self.case.resolved_at = timezone.now(); self.case.save()
        self.assertEqual(self.execute(id).status_code, 400)
        self.assertEqual(self.prepare().status_code, 400)

    def test_audit_failure_rolls_back_and_read_fails_closed(self):
        id = self.prepare().data["id"]
        with patch("apps.businesses.employee_access.write_audit_log", side_effect=DatabaseError("unavailable")):
            self.assertEqual(self.execute(id).status_code, 503)
        self.member.refresh_from_db(); self.assertTrue(self.member.is_active)
        self.assertEqual(EmployeeAccessRepair.objects.get(pk=id).status, "pending")
        with patch("apps.core.platform_crm_views.write_audit_log", side_effect=DatabaseError("unavailable")):
            response = self.api.get(self.root)
            self.assertEqual(response.status_code, 503)
            self.assertNotIn("members", response.data)

    def test_diagnostics_are_scoped_paginated_and_token_free(self):
        response = self.api.get(self.root)
        self.assertEqual(response.status_code, 200, response.data)
        self.assertNotIn("PRIVATE", str(response.data))
        self.assertNotIn(str(self.invitation.token), str(response.data))
        self.assertIn("no-store", response["Cache-Control"])
        snapshot = self.api.get(self.root, {"search": "staff@", "page_size": 1}).data
        self.assertEqual(snapshot["members_count"], 1)
        self.assertEqual(snapshot["members"][0]["specialists"][0]["name"], "Specialist")
        self.assertEqual(snapshot["invitations_count"], 0)
        self.assertEqual(self.api.get(self.root, {"page": 2, "page_size": 1}).data["members"][0]["id"], self.member.pk)
        self.assertEqual(self.api.get(self.root, {"page_size": 51}).status_code, 400)

    def test_invalid_input_conflicting_id_and_changed_revision(self):
        data = self.data()
        self.assertEqual(self.api.post(self.root, {**data, "reason": "  "}, format="json", HTTP_X_ZANI_MFA_STEP_UP=self.step).status_code, 400)
        self.assertEqual(self.api.post(self.root, {**data, "global_unlock": True}, format="json", HTTP_X_ZANI_MFA_STEP_UP=self.step).status_code, 400)
        self.assertEqual(self.api.post(self.root, {**data, "expected_revision": "0" * 64}, format="json", HTTP_X_ZANI_MFA_STEP_UP=self.step).status_code, 409)
        self.assertEqual(self.api.post(self.root, data, format="json", HTTP_X_ZANI_MFA_STEP_UP=self.step).status_code, 200)
        self.assertEqual(self.api.post(self.root, {**data, "reason": "Changed"}, format="json", HTTP_X_ZANI_MFA_STEP_UP=self.step).status_code, 409)
