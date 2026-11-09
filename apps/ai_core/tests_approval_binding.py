"""OFFICIAL-22: a prior decision cannot authorize a substituted command."""
from datetime import timedelta

from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.ai_core.models import AIRequestLog, ApprovalRequest
from apps.ai_core.serializers import ApprovalRequestSerializer
from apps.ai_core.tool_registry import suggest_tool_calls, tool_call_fingerprint
from apps.businesses.models import Business, BusinessMember, BusinessRole, RolePermission
from apps.clients.models import Client
from apps.core.models import AuditLog


class ApprovalBindingTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(username="approval-owner", email="approval-owner@example.test")
        self.actor = User.objects.create_user(username="approval-requester", email="approval-requester@example.test")
        self.business = Business.objects.create(owner=self.owner, name="Approval", slug="approval-binding")
        BusinessMember.objects.create(business=self.business, user=self.owner, role="owner")
        self.role = BusinessRole.objects.create(business=self.business, name="Requester without approval")
        BusinessMember.objects.create(business=self.business, user=self.actor, role="staff", business_role=self.role)
        for resource, actions in (("ai_automation", ("view", "manage")), ("ai_pipeline", ("view", "suggest", "execute")),
                                  ("clients", ("view", "update"))):
            for action in actions:
                RolePermission.objects.create(business_role=self.role, resource=resource, action=action, scope="business")
        RolePermission.objects.create(business_role=self.role, resource="ai_pipeline", action="approve", is_allowed=False, scope="none")
        self.person = Client.objects.create(business=self.business, full_name="Original")
        self.first = self.proposal("Reviewed")
        self.second = self.proposal("Unreviewed")
        self.api = APIClient()
        self.api.force_authenticate(self.actor)

    def proposal(self, name):
        return suggest_tool_calls(business=self.business, user=self.actor, tool_name="crm_update",
            arguments={"entity": "clients", "entity_id": self.person.pk, "values": {"full_name": name}})[0]

    def approval(self, status="approved"):
        return ApprovalRequest.objects.create(business=self.business, requested_by=self.actor,
            approved_by=self.owner if status in {"approved", "executed"} else None,
            approved_at=timezone.now() if status in {"approved", "executed"} else None,
            action_type="ai_pipeline", ai_tool_call_log=self.first, status=status,
            expires_at=timezone.now() + timedelta(minutes=10),
            payload={"tool_call_id": self.first.pk, "tool_fingerprint": tool_call_fingerprint(self.first)})

    def url(self, approval):
        return f"/api/ai/approval-requests/{approval.pk}/"

    def execute(self, log, approval):
        return self.api.post(f"/api/ai/tools/{log.pk}/execute/", {"approval_id": approval.pk}, format="json")

    def test_repointed_approval_cannot_execute_second_unreviewed_command(self):
        approval = self.approval()
        changed = self.api.patch(self.url(approval), {"ai_tool_call_log": self.second.pk,
            "payload": {"tool_call_id": self.second.pk, "tool_fingerprint": tool_call_fingerprint(self.second)}}, format="json")
        response = self.execute(self.second, approval)
        self.person.refresh_from_db()
        self.assertEqual(self.person.full_name, "Original", response.data)
        self.assertEqual(changed.status_code, 400, changed.data)
        self.assertEqual(response.status_code, 403, response.data)

    def test_material_fields_are_immutable_in_every_state(self):
        changes = ({"ai_tool_call_log": self.second.pk}, {"ai_tool_call_log": None}, {"payload": {}},
            {"expires_at": None}, {"expires_at": (timezone.now() + timedelta(days=10)).isoformat()},
            {"action_type": "ai_outreach"}, {"source_object_type": "Client"}, {"source_object_id": "999"},
            {"required_role": "owner"})
        for status in ApprovalRequest.Statuses.values:
            for change in changes:
                with self.subTest(status=status, change=change):
                    approval = self.approval(status)
                    response = self.api.patch(self.url(approval), change, format="json")
                    self.assertEqual(response.status_code, 400, response.data)
                    approval.refresh_from_db()
                    self.assertEqual(approval.status, status)
                    self.assertEqual(approval.ai_tool_call_log_id, self.first.pk)
                    self.assertEqual(approval.payload["tool_fingerprint"], tool_call_fingerprint(self.first))

    def test_put_cannot_replace_approval_identity(self):
        approval = self.approval()
        response = self.api.put(self.url(approval), {"business": self.business.pk, "action_type": "ai_pipeline",
            "ai_tool_call_log": self.second.pk, "payload": {"tool_fingerprint": tool_call_fingerprint(self.second)}}, format="json")
        self.assertEqual(response.status_code, 400, response.data)

    def test_reason_only_update_preserves_decision_and_command(self):
        approval = self.approval()
        approved_at = approval.approved_at
        response = self.api.patch(self.url(approval), {"reason": "Additional context"}, format="json")
        self.assertEqual(response.status_code, 200, response.data)
        approval.refresh_from_db()
        self.assertEqual(approval.reason, "Additional context")
        self.assertEqual(approval.status, "approved")
        self.assertEqual(approval.approved_at, approved_at)
        self.assertEqual(approval.approved_by_id, self.owner.pk)
        self.assertEqual(approval.ai_tool_call_log_id, self.first.pk)

    def test_identical_material_fields_are_noop(self):
        approval = self.approval()
        response = self.api.patch(self.url(approval), {"ai_tool_call_log": str(self.first.pk), "payload": approval.payload,
            "expires_at": approval.expires_at.isoformat(), "action_type": "ai_pipeline"}, format="json")
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(self.execute(self.first, approval).status_code, 200)

    def test_stale_reason_save_does_not_overwrite_concurrent_decision(self):
        for current in ("approved", "rejected", "executed", "expired"):
            with self.subTest(current=current):
                stale = self.approval("pending")
                serializer = ApprovalRequestSerializer(stale, data={"reason": "Context"}, partial=True)
                self.assertTrue(serializer.is_valid(), serializer.errors)
                ApprovalRequest.objects.filter(pk=stale.pk).update(status=current, approved_by=self.owner)
                result = serializer.save()
                stale.refresh_from_db()
                self.assertEqual(stale.status, current)
                self.assertEqual(stale.approved_by_id, self.owner.pk)
                self.assertEqual(result.status, current)

    def test_stale_noop_cannot_overwrite_execution(self):
        stale = self.approval()
        serializer = ApprovalRequestSerializer(stale, data={"payload": stale.payload}, partial=True)
        self.assertTrue(serializer.is_valid(), serializer.errors)
        self.assertEqual(self.execute(self.first, stale).status_code, 200)
        serializer.save()
        stale.refresh_from_db()
        self.assertEqual(stale.status, "executed")

    def test_original_approved_command_executes_once(self):
        approval = self.approval()
        for _ in range(2):
            response = self.execute(self.first, approval)
            self.assertEqual(response.status_code, 200, response.data)
        self.person.refresh_from_db()
        self.assertEqual(self.person.full_name, "Reviewed")
        self.assertEqual(AuditLog.objects.filter(metadata__kind="ai_crm_command", metadata__tool_call_id=self.first.pk).count(), 1)

    def test_requester_cannot_approve_fresh_request(self):
        approval = self.approval("pending")
        self.assertEqual(self.api.post(self.url(approval) + "approve/", {}).status_code, 403)
        self.assertEqual(self.execute(self.first, approval).status_code, 403)

    def test_new_request_is_pending_and_fingerprint_is_server_owned(self):
        response = self.api.post("/api/ai/approval-requests/", {"business": self.business.pk,
            "action_type": "ai_pipeline", "ai_tool_call_log": self.second.pk,
            "payload": {"tool_fingerprint": "forged"}, "status": "approved", "approved_by": self.owner.pk}, format="json")
        self.assertEqual(response.status_code, 201, response.data)
        approval = ApprovalRequest.objects.get(pk=response.data["id"])
        self.assertEqual(approval.status, "pending")
        self.assertIsNone(approval.approved_by_id)
        self.assertEqual(approval.payload["tool_fingerprint"], tool_call_fingerprint(self.second))

    def test_current_underlying_permission_still_required(self):
        approval = self.approval()
        RolePermission.objects.filter(business_role=self.role, resource="clients", action="update").update(is_allowed=False)
        response = self.execute(self.first, approval)
        self.assertIn(response.status_code, (400, 403))
        self.person.refresh_from_db()
        self.assertEqual(self.person.full_name, "Original")

    def test_foreign_tenant_cannot_edit_approval(self):
        approval = self.approval()
        other = User.objects.create_user(username="approval-foreign", email="approval-foreign@example.test")
        Business.objects.create(owner=other, name="Foreign", slug="approval-foreign")
        self.api.force_authenticate(other)
        self.assertEqual(self.api.patch(self.url(approval), {"reason": "Foreign"}, format="json").status_code, 404)
        approval.refresh_from_db()
        self.assertEqual(approval.reason, "")

    def test_executed_approval_cannot_be_recycled_for_fresh_command(self):
        approval = self.approval()
        self.assertEqual(self.execute(self.first, approval).status_code, 200)
        fresh = self.proposal("Second write")
        response = self.api.patch(self.url(approval), {"ai_tool_call_log": fresh.pk,
            "payload": {"tool_fingerprint": tool_call_fingerprint(fresh)}}, format="json")
        self.assertEqual(response.status_code, 400, response.data)
        self.assertEqual(self.execute(fresh, approval).status_code, 403)
        self.person.refresh_from_db()
        self.assertEqual(self.person.full_name, "Reviewed")

    def test_expired_approval_cannot_be_extended_or_cleared(self):
        approval = self.approval()
        ApprovalRequest.objects.filter(pk=approval.pk).update(expires_at=timezone.now() - timedelta(seconds=1))
        for expires in (None, (timezone.now() + timedelta(days=1)).isoformat()):
            self.assertEqual(self.api.patch(self.url(approval), {"expires_at": expires}, format="json").status_code, 400)
        self.assertEqual(self.execute(self.first, approval).status_code, 403)
        self.person.refresh_from_db()
        self.assertEqual(self.person.full_name, "Original")

    def test_request_log_cannot_replace_decision_evidence(self):
        approval = self.approval()
        request_log = AIRequestLog.objects.create(business=self.business, user=self.actor, source="crm", prompt_type="test")
        self.assertEqual(self.api.patch(self.url(approval), {"ai_request_log": request_log.pk}, format="json").status_code, 400)
        approval.refresh_from_db()
        self.assertIsNone(approval.ai_request_log_id)

    def test_current_approver_permission_is_still_required(self):
        approver = User.objects.create_user(username="approval-reviewer", email="approval-reviewer@example.test")
        role = BusinessRole.objects.create(business=self.business, name="Reviewer")
        BusinessMember.objects.create(business=self.business, user=approver, role="staff", business_role=role)
        permission = RolePermission.objects.create(business_role=role, resource="ai_pipeline", action="approve", scope="business")
        approval = self.approval()
        ApprovalRequest.objects.filter(pk=approval.pk).update(approved_by=approver)
        permission.is_allowed = False
        permission.save()
        response = self.execute(self.first, approval)
        self.assertEqual(response.status_code, 403, response.data)
        self.person.refresh_from_db()
        self.assertEqual(self.person.full_name, "Original")

    def test_normal_owner_decisions_keep_reason_and_audit(self):
        self.api.force_authenticate(self.owner)
        for action, expected in (("approve", "approved"), ("reject", "rejected")):
            approval = self.approval("pending")
            response = self.api.post(self.url(approval) + action + "/", {"reason": "Reviewed by owner"}, format="json")
            self.assertEqual(response.status_code, 200, response.data)
            approval.refresh_from_db()
            self.assertEqual(approval.status, expected)
            self.assertEqual(approval.reason, "Reviewed by owner")
            self.assertTrue(AuditLog.objects.filter(entity_id=str(approval.pk), metadata__kind="ai_approval_decision",
                metadata__decision=expected).exists())
