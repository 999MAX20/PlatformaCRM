"""Synthetic Inbox create/replay read-boundary regressions."""
import copy
import json
from datetime import timedelta
from unittest.mock import Mock, patch

from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.bots.models import Bot, BotConversation
from apps.businesses.models import Business, BusinessCapability, BusinessMember, BusinessRole, RolePermission, Team, TeamMember
from apps.clients.models import Client
from apps.conversations.inbox_serializers import InboxConversationSerializer
from apps.core.models import CRMCommandIdempotency
from apps.core.idempotency import CRMCommandResult, run_idempotent_crm_command
from apps.crm.models import Deal
from apps.crm.services import ensure_default_pipeline
from apps.leads.models import Lead
from apps.notifications.models import Notification
from apps.scheduling.models import Appointment
from apps.services.models import Service
from apps.tasks.models import Task


class InboxCreateReadVisibilityTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(username="inbox-read-owner", email="inbox-read-owner@example.invalid")
        self.actor = User.objects.create_user(username="inbox-read-actor", email="inbox-read-actor@example.invalid", role="business_operator")
        self.peer = User.objects.create_user(username="inbox-read-peer", email="inbox-read-peer@example.invalid", role="business_operator")
        self.business = Business.objects.create(owner=self.owner, name="Inbox read A", slug="inbox-read-a")
        self.other = Business.objects.create(owner=self.owner, name="Inbox read B", slug="inbox-read-b")
        self.role = BusinessRole.objects.create(business=self.business, name="Create without read")
        self.member = BusinessMember.objects.create(business=self.business, user=self.actor, role="operator", business_role=self.role)
        self.peer_member = BusinessMember.objects.create(business=self.business, user=self.peer, role="operator")
        for resource in ["clients", "leads", "deals", "tasks", "appointments"]:
            RolePermission.objects.create(business_role=self.role, resource=resource, action="create", scope="business")
            RolePermission.objects.create(business_role=self.role, resource=resource, action="view", is_allowed=resource=="clients", scope="business" if resource=="clients" else "none")
        for action in ["view", "update"]:
            RolePermission.objects.create(business_role=self.role, resource="conversations", action=action, scope="business")
        RolePermission.objects.create(business_role=self.role, resource="ai_pipeline", action="execute", scope="business")
        self.client = Client.objects.create(business=self.business, full_name="PRIVATE_CLIENT_910", phone="+77015550910")
        pipeline = ensure_default_pipeline(self.business)
        self.lead = Lead.objects.create(business=self.business, client=self.client, responsible_user=self.peer, message="PRIVATE_LEAD_MESSAGE_910")
        self.deal = Deal.objects.create(business=self.business, client=self.client, lead=self.lead, pipeline=pipeline,
            stage=pipeline.stages.order_by("order").first(), owner=self.peer, title="PRIVATE_DEAL_TITLE_910", amount=910)
        self.bot = Bot.objects.create(business=self.business, name="Synthetic inbox")
        self.conversation = BotConversation.objects.create(business=self.business, bot=self.bot, channel="website", external_user_id="visitor-910",
            client=self.client, lead=self.lead, deal=self.deal, assigned_to=self.actor)
        self.task = Task.objects.create(business=self.business, client=self.client, conversation=self.conversation,
            title="PRIVATE_TASK_TITLE_910", description="PRIVATE_TASK_DESCRIPTION_910", assignee=self.peer, created_by=self.owner)
        self.conversation.metadata_json = {"conversation_pipeline": {"client_id": self.client.pk, "lead_id": self.lead.pk,
            "deal_id": self.deal.pk, "task_id": self.task.pk}, "safe": "keep"}
        self.conversation.save(update_fields=["metadata_json"])
        self.api = APIClient()
        self.api.force_authenticate(self.actor)

    def grant(self, resource, scope="business", allowed=True):
        self.role.permissions.filter(resource=resource, action="view").update(scope=scope, is_allowed=allowed)

    def post(self, action, data=None, key=None):
        extra = {"HTTP_IDEMPOTENCY_KEY": key} if key else {}
        return self.api.post(f"/api/inbox/conversations/{self.conversation.pk}/{action}/", data or {}, format="json", **extra)

    def restricted(self, response, expected=200):
        self.assertEqual(response.status_code, expected, response.data)
        self.assertTrue(response.data.get("read_restricted"), response.data)
        self.assertNotIn("id", response.data)
        self.assertNotIn("PRIVATE_", json.dumps(response.data))

    def test_existing_lead_create_only_is_safe_ack_without_duplicate(self):
        before = Lead.objects.count()
        self.restricted(self.post("create-lead"))
        self.assertEqual(Lead.objects.count(), before)

    def test_existing_deal_create_only_is_safe_ack_without_duplicate(self):
        before = Deal.objects.count()
        self.restricted(self.post("create-deal"))
        self.assertEqual(Deal.objects.count(), before)

    def test_existing_children_business_view_preserves_normal_dto(self):
        self.grant("leads"); self.grant("deals")
        lead = self.post("create-lead")
        deal = self.post("create-deal")
        self.assertEqual(lead.data["id"], self.lead.pk)
        self.assertEqual(lead.data["message"], self.lead.message)
        self.assertEqual(deal.data["id"], self.deal.pk)
        self.assertEqual(deal.data["title"], self.deal.title)

    def test_own_scope_does_not_read_peer_link(self):
        self.grant("leads", "own"); self.grant("deals", "own")
        self.restricted(self.post("create-lead")); self.restricted(self.post("create-deal"))
        self.lead.responsible_user = self.actor; self.lead.save(update_fields=["responsible_user"])
        self.assertEqual(self.post("create-lead").data["id"], self.lead.pk)

    def test_team_scope_uses_current_membership(self):
        self.grant("leads", "team")
        self.restricted(self.post("create-lead"))
        team = Team.objects.create(business=self.business, name="Synthetic inbox team")
        TeamMember.objects.create(team=team, member=self.member, is_lead=True)
        TeamMember.objects.create(team=team, member=self.peer_member)
        self.assertEqual(self.post("create-lead").data["id"], self.lead.pk)
        TeamMember.objects.filter(team=team, member=self.peer_member).delete()
        self.restricted(self.post("create-lead"))

    def test_fresh_create_without_view_keeps_write_and_status_but_not_dto(self):
        self.conversation.lead = None; self.conversation.deal = None; self.conversation.metadata_json = {}
        self.conversation.save(update_fields=["lead", "deal", "metadata_json"])
        before = Lead.objects.count()
        self.restricted(self.post("create-lead", {"message": "Entered new lead"}), 201)
        self.assertEqual(Lead.objects.count(), before+1)
        self.conversation.refresh_from_db()
        self.assertEqual(self.conversation.lead.message, "Entered new lead")

    def test_pipeline_reuse_hides_each_child_and_preserves_created_flags(self):
        counts = (Client.objects.count(), Lead.objects.count(), Deal.objects.count(), Task.objects.count())
        response = self.post("run-pipeline", {"create_lead": True, "create_deal": True, "create_task": True,
            "use_ai_qualification": False, "apply_ai_decisions": False, "confirmed_actions": ["create_lead", "create_deal", "create_task"]})
        self.assertEqual(response.status_code, 200, response.data)
        for key in ["lead", "deal", "task"]:self.assertIsNone(response.data[key])
        self.assertFalse(any(response.data["created"].values()))
        self.assertNotIn("PRIVATE_LEAD_MESSAGE_910", json.dumps(response.data))
        self.assertEqual((Client.objects.count(), Lead.objects.count(), Deal.objects.count(), Task.objects.count()), counts)

    def test_pipeline_metadata_copy_respects_view_and_keeps_stored_state(self):
        original = copy.deepcopy(self.conversation.metadata_json)
        data = InboxConversationSerializer(self.conversation, context={"actor": self.actor}).data
        meta = data["metadata_json"]["conversation_pipeline"]
        for key in ["lead_id", "deal_id", "task_id"]:self.assertIsNone(meta[key])
        self.assertEqual(data["metadata_json"]["safe"], "keep")
        self.assertEqual(self.conversation.metadata_json, original)

    def test_metadata_no_actor_is_fail_closed_and_owner_control_keeps_refs(self):
        hidden = InboxConversationSerializer(self.conversation).data["metadata_json"]["conversation_pipeline"]
        self.assertTrue(all(hidden[key] is None for key in ["client_id", "lead_id", "deal_id", "task_id"]))
        allowed = InboxConversationSerializer(self.conversation, context={"actor": self.owner}).data["metadata_json"]["conversation_pipeline"]
        self.assertEqual(allowed["task_id"], self.task.pk)

    def test_task_replay_rechecks_view_and_does_not_repeat_writes(self):
        self.grant("tasks")
        first = self.post("create-task", {"title": "Replay task"}, "synthetic-task-910")
        self.assertEqual(first.status_code, 201, first.data)
        counts = (Task.objects.count(), Notification.objects.count())
        receipt = CRMCommandIdempotency.objects.get(action="conversation.create_task")
        saved = copy.deepcopy(receipt.response_json)
        self.grant("tasks", "none", False)
        self.restricted(self.post("create-task", {"title": "Replay task"}, "synthetic-task-910"), 201)
        self.assertEqual((Task.objects.count(), Notification.objects.count()), counts)
        receipt.refresh_from_db(); self.assertEqual(receipt.response_json, saved)

    def test_task_create_only_then_view_gain_can_replay_authorized_record(self):
        self.restricted(self.post("create-task", {"title": "New private task"}, "synthetic-task-gain-910"), 201)
        self.grant("tasks")
        response = self.post("create-task", {"title": "New private task"}, "synthetic-task-gain-910")
        self.assertEqual(response.data["title"], "New private task")

    def test_replay_uses_current_actor_field_policy_and_current_record(self):
        self.grant("tasks")
        first = self.post("create-task", {"title": "Original title"}, "synthetic-task-fields-910")
        Task.objects.filter(pk=first.data["id"]).update(title="Updated visible title")
        self.grant("clients", "none", False)
        response = self.post("create-task", {"title": "Original title"}, "synthetic-task-fields-910")
        self.assertEqual(response.data["title"], "Updated visible title")
        self.assertIsNone(response.data["client"])
        self.assertNotIn(self.client.full_name, json.dumps(response.data))

    def test_deleted_and_foreign_replay_targets_never_fall_back_to_cached_json(self):
        self.grant("tasks")
        payload = {"title": "Receipt task"}
        self.post("create-task", payload, "synthetic-task-ref-910")
        receipt = CRMCommandIdempotency.objects.get(action="conversation.create_task")
        foreign = Task.objects.create(business=self.other, title="FOREIGN_PRIVATE_TASK", created_by=self.owner)
        for reference in [str(foreign.pk), "999999999", "invalid"]:
            CRMCommandIdempotency.objects.filter(pk=receipt.pk).update(resource_id=reference)
            self.restricted(self.post("create-task", payload, "synthetic-task-ref-910"), 201)

    def test_appointment_replay_rechecks_view_without_duplicate_booking(self):
        service = Service.objects.create(business=self.business, name="Synthetic service", duration_minutes=30)
        start = timezone.now()+timedelta(days=1)
        appointment = Appointment.objects.create(business=self.business, client=self.client, service=service,
            start_at=start, end_at=start+timedelta(minutes=30), notes="PRIVATE_APPOINTMENT_NOTES_910")
        payload = {"service_id": service.pk, "start_at": start.isoformat()}
        self.grant("appointments")
        with patch("apps.conversations.inbox_views.create_appointment_from_conversation", return_value=appointment) as create:
            first = self.post("create-appointment", payload, "synthetic-booking-910")
            self.assertEqual(first.status_code, 201, first.data)
            self.grant("appointments", "none", False)
            self.restricted(self.post("create-appointment", payload, "synthetic-booking-910"), 201)
            self.assertEqual(create.call_count, 1)

    def test_foreign_existing_child_is_hidden_even_owner_of_both(self):
        client = Client.objects.create(business=self.other, full_name="Foreign client")
        foreign = Lead.objects.create(business=self.other, client=client, message="FOREIGN_PRIVATE_LEAD")
        self.conversation.lead = foreign; self.conversation.save(update_fields=["lead"])
        self.api.force_authenticate(self.owner)
        self.restricted(self.post("create-lead"))

    def test_create_denial_and_payload_mismatch_still_deny(self):
        self.role.permissions.filter(resource="leads", action="create").update(is_allowed=False)
        self.assertEqual(self.post("create-lead").status_code, 403)
        self.grant("tasks")
        self.post("create-task", {"title": "one"}, "synthetic-conflict-910")
        self.assertEqual(self.post("create-task", {"title": "two"}, "synthetic-conflict-910").status_code, 409)

    def test_narrowing_between_unkeyed_existing_reads_is_applied(self):
        self.grant("leads")
        self.assertEqual(self.post("create-lead").data["message"], self.lead.message)
        self.grant("leads", "none", False)
        self.restricted(self.post("create-lead"))

    def test_booking_metadata_existing_target_hides_copied_slot(self):
        service = Service.objects.create(business=self.business, name="Booking metadata service", duration_minutes=30)
        start = timezone.now()+timedelta(days=1)
        appointment = Appointment.objects.create(business=self.business, client=self.client, service=service,
            start_at=start, end_at=start+timedelta(minutes=30))
        self.conversation.metadata_json = {"auto_booking": {"appointment_id": appointment.pk, "status": "booked",
            "selected_slot": {"start_at": start.isoformat()}, "reason": "PRIVATE_BOOKING_REASON"}}
        before = copy.deepcopy(self.conversation.metadata_json)
        data = InboxConversationSerializer(self.conversation, context={"actor": self.actor}).data
        self.assertIsNone(data["metadata_json"]["auto_booking"]["appointment_id"])
        self.assertIsNone(data["metadata_json"]["auto_booking"]["selected_slot"])
        self.assertEqual(data["metadata_json"]["auto_booking"]["reason"], "")
        self.assertEqual(self.conversation.metadata_json, before)

    def test_pending_booking_without_saved_appointment_keeps_offered_slot(self):
        self.conversation.metadata_json = {"auto_booking": {"appointment_id": None, "status": "awaiting_confirmation",
            "selected_slot": {"start_at": "2026-10-29T10:00:00Z"}, "reason": "Choose an offered slot"}}
        data = InboxConversationSerializer(self.conversation, context={"actor": self.actor}).data
        self.assertEqual(data["metadata_json"], self.conversation.metadata_json)

    def test_generic_command_default_contract_is_unchanged(self):
        operation = Mock(return_value=CRMCommandResult(data={"receipt": "synthetic"}, status_code=202, resource=self.task))
        kwargs = {"business": self.business, "actor": self.actor, "action": "synthetic.generic.contract",
                  "idempotency_key": "synthetic-generic-910", "payload": {"same": "data"}, "operation": operation}
        first = run_idempotent_crm_command(**kwargs)
        second = run_idempotent_crm_command(**kwargs)
        self.assertEqual(second.data, first.data)
        self.assertEqual(second.status_code, 202)
        self.assertTrue(second.replayed)
        self.assertEqual(operation.call_count, 1)
        self.assertEqual((second.resource_type, second.resource_id), ("tasks.task", str(self.task.pk)))
