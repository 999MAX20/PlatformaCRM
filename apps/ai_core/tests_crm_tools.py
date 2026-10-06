from unittest.mock import patch

from django.test import TestCase
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied, ValidationError

from apps.ai_core import tests as fixtures
from apps.ai_core.crm_tools import prepare_command, read_entities
from apps.ai_core.models import AIToolCallLog, ApprovalRequest, AgentProfile
from apps.ai_core.tool_registry import execute_tool_call_once, suggest_tool_calls, tool_call_fingerprint
from apps.clients.models import Client
from apps.tasks.models import Task
from apps.core.models import AuditLog


class CRMCommandTests(TestCase):
    def setUp(self):
        fixtures.AICoreFoundationTests.setUp(self)
        self.api.force_authenticate(self.owner)
        self.person = Client.objects.create(business=self.business, full_name="Original")

    def proposal(self, tool, entity="clients", **arguments):
        return suggest_tool_calls(business=self.business, user=self.owner, tool_name=tool,
            arguments={"entity": entity, **arguments})[0]

    def approval(self, log):
        return ApprovalRequest.objects.create(business=self.business, requested_by=self.owner,
            approved_by=self.owner, approved_at=timezone.now(), action_type="ai_pipeline",
            ai_tool_call_log=log, status="approved", expires_at=timezone.now() + timezone.timedelta(minutes=10),
            payload={"tool_fingerprint": tool_call_fingerprint(log)})

    def execute(self, log):
        approval = self.approval(log)
        return self.api.post(f"/api/ai/tools/{log.pk}/execute/", {"approval_id": approval.pk})

    def test_update_preview_does_not_write_then_exact_approval_updates_once(self):
        log = self.proposal("crm_update", entity_id=self.person.pk, values={"full_name": "Reviewed"})
        self.person.refresh_from_db()
        self.assertEqual(self.person.full_name, "Original")
        self.assertEqual(log.input_json["before"]["full_name"], "Original")
        approval = self.approval(log)
        for _ in range(2):
            response = self.api.post(f"/api/ai/tools/{log.pk}/execute/", {"approval_id": approval.pk})
            self.assertEqual(response.status_code, 200, response.data)
        self.person.refresh_from_db()
        self.assertEqual(self.person.full_name, "Reviewed")
        self.assertEqual(AuditLog.objects.filter(metadata__kind="ai_crm_command", metadata__tool_call_id=log.pk).count(), 1)

    def test_missing_approval_cannot_write(self):
        log = self.proposal("crm_update", entity_id=self.person.pk, values={"full_name": "Denied"})
        response = self.api.post(f"/api/ai/tools/{log.pk}/execute/", {})
        self.assertEqual(response.status_code, 403)
        self.person.refresh_from_db()
        self.assertEqual(self.person.full_name, "Original")

    def test_other_requester_cannot_disclose_a_command_through_execution_errors(self):
        from apps.accounts.models import User
        from apps.businesses.models import BusinessMember
        log = self.proposal("crm_update", entity_id=self.person.pk, values={"notes": "Private reviewed note"})
        actor = User.objects.create_user(username="different-requester", password="pass")
        BusinessMember.objects.create(business=self.business, user=actor, role="admin")
        self.api.force_authenticate(actor)
        response = self.api.post(f"/api/ai/tools/{log.pk}/execute/", {})
        self.assertEqual(response.status_code, 403)
        self.assertNotIn("Private reviewed note", str(response.data))
        log.refresh_from_db()
        self.assertEqual(log.status, "suggested")

    def test_stale_target_is_not_overwritten(self):
        log = self.proposal("crm_update", entity_id=self.person.pk, values={"full_name": "Old proposal"})
        Client.objects.filter(pk=self.person.pk).update(full_name="Other staff change")
        response = self.execute(log)
        self.assertEqual(response.status_code, 400, response.data)
        self.person.refresh_from_db()
        self.assertEqual(self.person.full_name, "Other staff change")

    def test_provider_cannot_supply_foreign_entity_or_business_or_lifecycle(self):
        foreign = Client.objects.create(business=self.other_business, full_name="Foreign")
        with self.assertRaises(PermissionDenied):
            self.proposal("crm_update", entity_id=foreign.pk, values={"full_name": "Denied"})
        for values in ({"business": self.other_business.pk}, {"is_archived": True}, {"status": "closed"}):
            with self.assertRaises(ValidationError):
                self.proposal("crm_update", entity_id=self.person.pk, values=values)
        with self.assertRaises(ValidationError):
            self.proposal("crm_create", entity="tasks", values={"title": "Bad link", "client": foreign.pk})

    def test_create_task_and_replay_preserve_one_record(self):
        log = self.proposal("crm_create", entity="tasks", values={"title": "Call", "client": self.person.pk})
        approval = self.approval(log)
        for _ in range(2):
            response = self.api.post(f"/api/ai/tools/{log.pk}/execute/", {"approval_id": approval.pk})
            self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(Task.objects.filter(business=self.business, title="Call").count(), 1)

    def test_archive_preserves_data_and_restore_is_confirmed(self):
        log = self.proposal("crm_archive", entity_id=self.person.pk, reason="Duplicate")
        approval = self.approval(log)
        response = self.api.post(f"/api/ai/tools/{log.pk}/execute/", {"approval_id": approval.pk})
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(self.api.post(f"/api/ai/tools/{log.pk}/execute/", {"approval_id": approval.pk}).status_code, 200)
        self.person.refresh_from_db()
        self.assertTrue(self.person.is_archived)
        restore = self.proposal("crm_restore", entity_id=self.person.pk)
        self.assertEqual(self.execute(restore).status_code, 200)
        self.person.refresh_from_db()
        self.assertFalse(self.person.is_archived)

    def test_client_archive_respects_unfinished_work(self):
        Task.objects.create(business=self.business, client=self.person, title="Unfinished")
        log = self.proposal("crm_archive", entity_id=self.person.pk)
        self.assertEqual(self.execute(log).status_code, 400)
        self.person.refresh_from_db()
        self.assertFalse(self.person.is_archived)

    def test_mutated_or_expired_approval_is_rejected(self):
        log = self.proposal("crm_update", entity_id=self.person.pk, values={"phone": "+77000000000"})
        approval = self.approval(log)
        log.input_json["values"]["phone"] = "+77000000001"
        log.save()
        response = self.api.post(f"/api/ai/tools/{log.pk}/execute/", {"approval_id": approval.pk})
        self.assertEqual(response.status_code, 403)
        approval.payload = {"tool_fingerprint": tool_call_fingerprint(log)}
        approval.expires_at = timezone.now() - timezone.timedelta(seconds=1)
        approval.save()
        self.assertEqual(self.api.post(f"/api/ai/tools/{log.pk}/execute/", {"approval_id": approval.pk}).status_code, 403)

    def test_disabled_capability_is_rechecked(self):
        from apps.bots.models import Bot
        agent = Bot.objects.create(business=self.business, name="CRM", status="active", settings_json={"scenario": "crm"})
        profile = AgentProfile.objects.create(business=self.business, bot=agent, name="CRM",
            allowed_tools_json={"tools": ["crm_update"]})
        log = self.proposal("crm_update", entity_id=self.person.pk, values={"phone": "123"})
        profile.allowed_tools_json = {"tools": []}
        profile.save()
        self.assertEqual(self.execute(log).status_code, 403)

    def test_search_paginates_full_scope_and_hides_foreign_records(self):
        Client.objects.bulk_create([Client(business=self.business, full_name=f"Person {i}") for i in range(24)])
        Client.objects.create(business=self.other_business, full_name="Person foreign")
        result = read_entities(business=self.business, user=self.owner, entity="clients", query="Person", offset=20)
        self.assertEqual(result["count"], 24)
        self.assertEqual(len(result["results"]), 4)
        self.assertFalse(result["has_more"])

    def test_domain_write_and_audit_failure_roll_back_together(self):
        log = self.proposal("crm_create", entity="tasks", values={"title": "Rollback"})
        approval = self.approval(log)
        with patch("apps.ai_core.crm_tools.write_audit_log", side_effect=RuntimeError("Audit unavailable")):
            result, _ = execute_tool_call_once(log.pk, self.owner, approval_id=approval.pk)
        self.assertEqual(result.status, "failed")
        self.assertFalse(Task.objects.filter(title="Rollback").exists())

    def test_lifecycle_uses_domain_invariants(self):
        task = Task.objects.create(business=self.business, title="Complete", assignee=self.owner)
        log = self.proposal("crm_transition", entity="tasks", entity_id=task.pk, action="complete")
        self.assertEqual(self.execute(log).status_code, 200)
        task.refresh_from_db()
        self.assertEqual(task.status, "done")
        self.assertIsNotNone(task.completed_at)

    def test_lead_and_deal_creation_update_and_terminal_reason(self):
        from apps.crm.services import ensure_default_pipeline
        from apps.crm.models import Deal
        from apps.leads.models import Lead
        lead_log = self.proposal("crm_create", entity="leads", values={"client": self.person.pk, "message": "Consultation"})
        response = self.execute(lead_log)
        self.assertEqual(response.status_code, 200, response.data)
        lead = Lead.objects.get(pk=response.data["output_json"]["entity_id"])
        self.assertEqual(lead.responsible_user, self.owner)
        pipeline = ensure_default_pipeline(self.business)
        stage = pipeline.stages.filter(is_won=False, is_lost=False).first()
        deal_log = self.proposal("crm_create", entity="deals", values={"client": self.person.pk, "lead": lead.pk,
            "pipeline": pipeline.pk, "stage": stage.pk, "title": "Consultation deal", "amount": "100.25", "currency": "KZT"})
        response = self.execute(deal_log)
        self.assertEqual(response.status_code, 200, response.data)
        deal = Deal.objects.get(pk=response.data["output_json"]["entity_id"])
        update = self.proposal("crm_update", entity="deals", entity_id=deal.pk, values={"title": "Reviewed deal", "amount": "110.50"})
        self.assertEqual(self.execute(update).status_code, 200)
        deal.refresh_from_db()
        self.assertEqual(str(deal.amount), "110.50")
        with self.assertRaises(ValidationError):
            self.proposal("crm_transition", entity="deals", entity_id=deal.pk, action="lose")
        lose = self.proposal("crm_transition", entity="deals", entity_id=deal.pk, action="lose", reason="Customer declined")
        self.assertEqual(self.execute(lose).status_code, 200)
        deal.refresh_from_db()
        self.assertEqual(deal.status, "lost")
        self.assertIsNotNone(deal.lost_at)

    def test_appointment_create_reschedule_cancel_and_busy_slot_recheck(self):
        from datetime import datetime, time
        from apps.services.models import Service
        from apps.scheduling.models import Resource, WorkingHours, Appointment
        service = Service.objects.create(business=self.business, name="Consultation", duration_minutes=30)
        resource = Resource.objects.create(business=self.business, name="Specialist")
        WorkingHours.objects.create(business=self.business, weekday=0, start_time=time(9), end_time=time(18))
        values = {"client": self.person.pk, "service": service.pk, "resource": resource.pk, "start_at": "2026-10-05T10:00:00Z"}
        first = self.proposal("crm_create", entity="appointments", values=values)
        second = self.proposal("crm_create", entity="appointments", values=values)
        response = self.execute(first)
        self.assertEqual(response.status_code, 200, response.data)
        appointment = Appointment.objects.get(pk=response.data["output_json"]["entity_id"])
        self.assertEqual(self.execute(second).status_code, 400)
        self.assertEqual(Appointment.objects.count(), 1)
        move = self.proposal("crm_transition", entity="appointments", entity_id=appointment.pk, action="reschedule", values={"start_at": "2026-10-05T11:00:00Z", "resource": resource.pk, "reason": "Customer requested"})
        self.assertEqual(self.execute(move).status_code, 200)
        appointment.refresh_from_db()
        self.assertEqual(appointment.start_at.hour, 11)
        cancel = self.proposal("crm_transition", entity="appointments", entity_id=appointment.pk, action="cancel", reason="Customer requested")
        self.assertEqual(self.execute(cancel).status_code, 200)
        appointment.refresh_from_db()
        self.assertEqual(appointment.status, "cancelled")

    def test_direct_execution_cannot_bypass_exact_approval(self):
        log = self.proposal("crm_update", entity_id=self.person.pk, values={"phone": "123"})
        with self.assertRaises(PermissionDenied):
            execute_tool_call_once(log.pk, self.owner)
        log.refresh_from_db()
        self.assertEqual(log.status, "suggested")
        self.person.refresh_from_db()
        self.assertEqual(self.person.phone, "")

    def test_role_denial_and_revoked_membership_prevent_new_commands(self):
        from apps.accounts.models import User
        from apps.businesses.models import BusinessMember, BusinessRole, RolePermission
        actor = User.objects.create_user(username="limited-command", password="pass")
        role = BusinessRole.objects.create(business=self.business, name="AI reader")
        for resource, action in (("ai_pipeline", "suggest"), ("clients", "view")):
            RolePermission.objects.create(business_role=role, resource=resource, action=action, scope="business", is_allowed=True)
        RolePermission.objects.create(business_role=role, resource="clients", action="update", scope="none", is_allowed=False)
        membership = BusinessMember.objects.create(business=self.business, user=actor, role="manager", business_role=role)
        self.api.force_authenticate(actor)
        response = self.api.post("/api/ai/tools/suggest/", {"business": self.business.pk, "tool_name": "crm_update", "arguments": {"entity": "clients", "entity_id": self.person.pk, "values": {"full_name": "Denied"}}}, format="json")
        self.assertEqual(response.status_code, 403, response.data)
        membership.is_active = False; membership.save()
        self.assertEqual(self.api.get("/api/ai/crm/read/", {"business": self.business.pk, "entity": "clients"}).status_code, 403)

    def test_own_scope_hides_other_tasks_and_rechecks_target_after_reassignment(self):
        from apps.accounts.models import User
        from apps.businesses.models import BusinessMember, BusinessRole, RolePermission
        actor = User.objects.create_user(username="own-command", password="pass")
        role = BusinessRole.objects.create(business=self.business, name="Own tasks")
        for action in ("view", "update"):
            RolePermission.objects.create(business_role=role, resource="tasks", action=action, scope="own", is_allowed=True)
        BusinessMember.objects.create(business=self.business, user=actor, role="manager", business_role=role)
        own = Task.objects.create(business=self.business, assignee=actor, title="Own")
        other = Task.objects.create(business=self.business, assignee=self.owner, title="Other")
        result = read_entities(business=self.business, user=actor, entity="tasks")
        self.assertEqual([row["id"] for row in result["results"]], [own.pk])
        with self.assertRaises(PermissionDenied):
            prepare_command(business=self.business, user=actor, tool="crm_update", payload={"entity": "tasks", "entity_id": other.pk, "values": {"title": "Denied"}})
        prepared = prepare_command(business=self.business, user=actor, tool="crm_update", payload={"entity": "tasks", "entity_id": own.pk, "values": {"title": "Proposed"}})
        Task.objects.filter(pk=own.pk).update(assignee=self.owner)
        from apps.ai_core.crm_tools import assert_command_allowed
        with self.assertRaises(PermissionDenied):
            assert_command_allowed(business=self.business, user=actor, tool="crm_update", payload=prepared, lock=True)

    def test_read_and_preview_do_not_disclose_staff_restricted_notes(self):
        from apps.accounts.models import User
        from apps.businesses.models import BusinessMember, BusinessRole, RolePermission
        actor = User.objects.create_user(username="notes-restricted", password="pass")
        role = BusinessRole.objects.create(business=self.business, name="Client editor")
        for action in ("view", "update"):
            RolePermission.objects.create(business_role=role, resource="clients", action=action, scope="business", is_allowed=True)
        BusinessMember.objects.create(business=self.business, user=actor, role="staff", business_role=role)
        self.person.notes = "Internal sensitive note"
        self.person.save()
        result = read_entities(business=self.business, user=actor, entity="clients")
        self.assertNotIn("notes", result["results"][0])
        prepared = prepare_command(business=self.business, user=actor, tool="crm_update", payload={"entity": "clients", "entity_id": self.person.pk, "values": {"phone": "123"}})
        self.assertNotIn("notes", prepared["before"])
        with self.assertRaises(PermissionDenied):
            prepare_command(business=self.business, user=actor, tool="crm_update", payload={"entity": "clients", "entity_id": self.person.pk, "values": {"notes": "Hidden update"}})
