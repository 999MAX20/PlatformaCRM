import csv
from datetime import timedelta
import io
import json

from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.activities.models import ActivityEvent, Note
from apps.activities.serializers import ActivityTimelineSerializer, NoteSerializer
from apps.ai_core.assistant import build_crm_context
from apps.ai_core.recommendations import build_owner_daily_brief
from apps.bots.models import Bot, BotConversation
from apps.businesses.models import Business, BusinessCapability, BusinessMember, BusinessRole, RolePermission, Team, TeamMember
from apps.clients.models import Client
from apps.core.crm_cards import deal_crm_card
from apps.core.crm_read_scope import readable_link
from apps.core.export_access import assert_export_download_access
from apps.core.export_jobs import process_export_job, request_entity_export
from apps.core.import_export import export_deals, export_leads
from apps.core.work_queues import build_work_queues
from apps.crm.models import Deal, Pipeline, PipelineStage
from apps.crm.serializers import DealListSerializer, DealSerializer
from apps.leads.models import Lead
from apps.leads.serializers import LeadListSerializer, LeadSerializer
from apps.notifications.models import Notification
from apps.notifications.serializers import NotificationSerializer
from apps.outreach.models import OutreachCampaign, OutreachConsent, OutreachRecipient
from apps.outreach.serializers import OutreachConsentSerializer, OutreachRecipientSerializer
from apps.outreach.services import appointment_automation_status, preview_campaign_audience
from apps.scheduling.models import Appointment, Resource
from apps.scheduling.serializers import AppointmentSerializer
from apps.scheduling.services import APPOINTMENT_REMINDER_LABEL
from apps.services.models import Service
from apps.tasks.models import Task
from apps.tasks.serializers import TaskSerializer


class LinkedClientProjectionTests(TestCase):
    name = "PRIVATE_CLIENT_903"
    phone = "+77011234567"
    email = "private.client903@example.test"
    telegram = "tg-private903"
    whatsapp = "wa-private903"

    def setUp(self):
        self.now = timezone.now()
        self.owner = User.objects.create_user(username="projection-owner", email="projection-owner@example.test")
        self.actor = User.objects.create_user(username="projection-reader", email="projection-reader@example.test")
        self.peer = User.objects.create_user(username="projection-peer", email="projection-peer@example.test")
        self.business = Business.objects.create(owner=self.owner, name="Linked client", slug="linked-client-pii")
        self.role = BusinessRole.objects.create(business=self.business, name="Readable parents, hidden client")
        self.member = BusinessMember.objects.create(business=self.business, user=self.actor, role="operator", business_role=self.role)
        self.peer_member = BusinessMember.objects.create(business=self.business, user=self.peer, role="operator")
        for resource in ("leads", "deals", "appointments", "tasks", "conversations", "analytics", "notifications", "ai_assistant", "ai_analyst"):
            RolePermission.objects.create(business_role=self.role, resource=resource, action="view", scope="business")
        RolePermission.objects.create(business_role=self.role, resource="clients", action="view", scope="none", is_allowed=False)
        RolePermission.objects.create(business_role=self.role, resource="clients", action="create", scope="business")
        RolePermission.objects.create(business_role=self.role, resource="conversations", action="update", scope="business")
        self.customer = Client.objects.create(business=self.business, full_name=self.name, phone=self.phone, email=self.email,
            telegram_id=self.telegram, whatsapp_id=self.whatsapp)
        self.lead = Lead.objects.create(business=self.business, client=self.customer, message="Public parent message", responsible_user=self.actor)
        Lead.objects.filter(pk=self.lead.pk).update(updated_at=self.now-timedelta(days=7))
        pipeline = Pipeline.objects.create(business=self.business, name="Parent pipeline", slug="parent")
        stage = PipelineStage.objects.create(business=self.business, pipeline=pipeline, name="Parent stage", sla_minutes=30)
        self.deal = Deal.objects.create(business=self.business, client=self.customer, lead=self.lead, pipeline=pipeline, stage=stage,
            title="Public parent deal", owner=self.actor, stage_entered_at=self.now-timedelta(days=2))
        self.service = Service.objects.create(business=self.business, name="Public service", price_from=1)
        resource = Resource.objects.create(business=self.business, name="Public specialist", linked_user=self.actor)
        self.appointment = Appointment.objects.create(business=self.business, client=self.customer, lead=self.lead, service=self.service,
            resource=resource, start_at=self.now+timedelta(hours=1), end_at=self.now+timedelta(hours=2))
        bot = Bot.objects.create(business=self.business, name="Public parent bot")
        self.conversation = BotConversation.objects.create(business=self.business, bot=bot, client=self.customer, channel="website",
            assigned_to=self.actor, external_user_id=self.phone, unread_count=1, last_inbound_at=self.now-timedelta(hours=1))
        self.task = Task.objects.create(business=self.business, client=self.customer, lead=self.lead, conversation=self.conversation,
            title="Public task", description="Public parent description", assignee=self.actor, created_by=self.actor, due_at=self.now-timedelta(hours=1))
        self.event = ActivityEvent.objects.create(business=self.business, client=self.customer, entity_type="Deal", entity_id=str(self.deal.pk),
            event_type="legacy_parent_event", text=f"Legacy parent event: {self.name}", metadata={"client": {"full_name": self.name, "phone": self.phone}, "safe_status": "open"})
        self.campaign = OutreachCampaign.objects.create(business=self.business, name="Public campaign", created_by=self.owner,
            channel="whatsapp", audience_type="all_clients", require_opt_in=False, message_text="Hello {client_name}")
        self.consent = OutreachConsent.objects.create(business=self.business, client=self.customer, channel="whatsapp", status="opted_in",
            source="paper", note=self.name, evidence_json={"import_row": {"phone": self.phone, "email": self.email}})
        self.notification = Notification.objects.create(business=self.business, recipient=self.actor, client=self.customer,
            appointment=self.appointment, channel="system", category=Notification.Categories.SALES, status="failed",
            send_at=self.now,
            text=f"Reminder for {self.name} {self.phone}", action_label=APPOINTMENT_REMINDER_LABEL,
            action_url=f"/app/clients?client={self.customer.pk}", last_error=self.email, provider_reference=self.phone)
        self.recipient = OutreachRecipient.objects.create(business=self.business, campaign=self.campaign, client=self.customer,
            notification=self.notification, recipient_id=self.phone, personalized_text=f"Hello {self.name} {self.email}",
            error=f"Delivery to {self.phone}", provider_result={"recipient": self.email})
        self.api = APIClient()
        self.api.force_authenticate(self.actor)

    def permission(self, allowed, scope="business"):
        RolePermission.objects.filter(business_role=self.role, resource="clients", action="view").update(is_allowed=allowed, scope=scope)

    def assert_private_absent(self, data):
        text = json.dumps(data, default=str)
        for value in (self.name, self.phone, self.email, self.telegram, self.whatsapp):
            self.assertNotIn(value, text)

    def cases(self):
        return [(DealSerializer, self.deal), (DealListSerializer, self.deal), (LeadSerializer, self.lead),
                (LeadListSerializer, self.lead), (AppointmentSerializer, self.appointment), (TaskSerializer, self.task),
                (ActivityTimelineSerializer, self.event), (OutreachConsentSerializer, self.consent),
                (OutreachRecipientSerializer, self.recipient), (NotificationSerializer, self.notification)]

    def test_direct_serializers_hide_linked_client_but_keep_parent(self):
        for serializer, obj in self.cases():
            with self.subTest(serializer=serializer.__name__):
                data = serializer(obj, context={"actor": self.actor}).data
                self.assertEqual(data["id"], obj.pk)
                self.assertIsNone(data["client"])
                self.assert_private_absent(data)

    def test_missing_actor_cannot_implicitly_authorize_client_data(self):
        for serializer, obj in self.cases():
            with self.subTest(serializer=serializer.__name__):
                data = serializer(obj).data
                self.assertIsNone(data["client"])
                self.assert_private_absent(data)

    def test_owner_and_explicit_client_view_controls(self):
        self.permission(True)
        for actor in (self.owner, self.actor):
            for serializer, obj in self.cases():
                with self.subTest(actor=actor.pk, serializer=serializer.__name__):
                    data = serializer(obj, context={"actor": actor}).data
                    self.assertEqual(data["client"], self.customer.pk)
                    if "client_name" in data:
                        self.assertEqual(data["client_name"], self.name)

    def test_parent_lists_and_details_remain_readable_without_client_view(self):
        # External delivery keeps the parent/projection contract. Internal personal
        # feed rows additionally require current source access (personal API suite).
        Notification.objects.filter(pk=self.notification.pk).update(channel="email")
        for route, obj in (("deals", self.deal), ("leads", self.lead), ("appointments", self.appointment), ("tasks", self.task),
                           ("activity-events", self.event), ("outreach/consents", self.consent), ("outreach/recipients", self.recipient), ("notifications", self.notification)):
            with self.subTest(route=route):
                detail = self.api.get(f"/api/{route}/{obj.pk}/", {"business": self.business.pk})
                self.assertEqual(detail.status_code, 200, detail.data)
                self.assert_private_absent(detail.data)
                listing = self.api.get(f"/api/{route}/", {"business": self.business.pk})
                self.assertEqual(listing.status_code, 200, listing.data)
                self.assertEqual(listing.data["count"], 1)
                self.assert_private_absent(listing.data)

    def test_deal_board_and_crm_card_do_not_reintroduce_client(self):
        for path in ("/api/deals/board/", f"/api/deals/{self.deal.pk}/crm-card/"):
            with self.subTest(path=path):
                response = self.api.get(path, {"business": self.business.pk})
                self.assertEqual(response.status_code, 200, response.data)
                self.assert_private_absent(response.data)

    def test_all_crm_card_nested_serializers_keep_owner_context(self):
        card = deal_crm_card(self.deal, actor=self.owner)
        self.assertEqual(card["client"]["full_name"], self.name)
        self.assertEqual(card["lead"]["client_name"], self.name)
        self.assertEqual(card["appointment"]["client_name"], self.name)
        self.assertTrue(any(task["client_name"] == self.name for task in card["tasks"]))

    def test_own_and_team_client_scopes_follow_existing_read_policy(self):
        team = Team.objects.create(business=self.business, name="Projection team")
        TeamMember.objects.create(team=team, member=self.member, is_lead=True)
        TeamMember.objects.create(team=team, member=self.peer_member)
        for scope in ("own", "team"):
            self.permission(True, scope)
            with self.subTest(scope=scope):
                # Client has no assignee fields; existing policy does not invent a Lead-derived owner.
                self.assertIsNone(readable_link(self.customer, actor=self.actor, business=self.business, resource="clients"))
                response = self.api.get(f"/api/deals/{self.deal.pk}/")
                self.assertEqual(response.status_code, 200)
                self.assertIsNone(response.data["client"])
                self.assert_private_absent(response.data)

    def test_client_capability_disable_hides_projection_even_for_owner(self):
        BusinessCapability.objects.update_or_create(business=self.business, module_key="clients", defaults={"is_enabled": False})
        self.api.force_authenticate(self.owner)
        response = self.api.get(f"/api/leads/{self.lead.pk}/")
        self.assertEqual(response.status_code, 200, response.data)
        self.assertIsNone(response.data["client"])
        self.assert_private_absent(response.data)

    def test_parent_own_scope_and_denial_are_not_bypassed(self):
        RolePermission.objects.filter(business_role=self.role, resource="deals", action="view").update(scope="own")
        foreign_parent = Deal.objects.create(business=self.business, client=self.customer, pipeline=self.deal.pipeline, stage=self.deal.stage,
            title="Peer parent", owner=self.peer)
        response = self.api.get("/api/deals/", {"business": self.business.pk})
        self.assertEqual(response.status_code, 200)
        self.assertEqual([row["id"] for row in response.data["results"]], [self.deal.pk])
        self.assertEqual(self.api.get(f"/api/deals/{foreign_parent.pk}/").status_code, 404)
        RolePermission.objects.filter(business_role=self.role, resource="deals", action="view").update(is_allowed=False)
        self.assertEqual(self.api.get(f"/api/deals/{self.deal.pk}/").status_code, 404)

    def test_hidden_contact_search_does_not_infer_matching_parent(self):
        for route in ("deals", "leads", "tasks"):
            for workspace in (False, True) if route != "tasks" else (False,):
                for term in (self.name, self.phone, self.email):
                    with self.subTest(route=route, workspace=workspace, term=term):
                        params = {"business": self.business.pk, "search": term}
                        if workspace:
                            params["workspace"] = "true"
                        response = self.api.get(f"/api/{route}/", params)
                        self.assertEqual(response.status_code, 200, response.data)
                        self.assertEqual(response.data["count"], 0)

    def test_permitted_contact_and_parent_own_content_search_controls(self):
        self.permission(True)
        for route in ("deals", "leads", "tasks"):
            response = self.api.get(f"/api/{route}/", {"search": self.name})
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.data["count"], 1)
        self.permission(False, "none")
        for route in ("deals", "leads", "tasks"):
            response = self.api.get(f"/api/{route}/", {"search": "Public parent" if route != "tasks" else "Public task"})
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.data["count"], 1)

    def test_timeline_name_search_and_typed_copies_do_not_disclose_client(self):
        detail = self.api.get(f"/api/activity-events/{self.event.pk}/")
        self.assertEqual(detail.status_code, 200)
        self.assert_private_absent(detail.data)
        self.assertEqual(detail.data["metadata"]["safe_status"], "open")
        response = self.api.get("/api/activity-events/", {"q": self.name})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 0)
        self.event.refresh_from_db()
        self.assertIn(self.name, self.event.text)

    def test_work_queue_labels_and_ids_do_not_disclose_hidden_client(self):
        data = build_work_queues(business=self.business, user=self.actor, now=self.now)
        self.assert_private_absent(data)
        self.assertTrue(data["queues"]["stale_leads"])
        self.assertTrue(data["queues"]["upcoming_appointments"])
        for rows in data["queues"].values():
            for row in rows:
                if "client_id" in row:
                    self.assertIsNone(row["client_id"])

    def test_ai_context_and_rule_sources_do_not_copy_client(self):
        context = build_crm_context(self.business, user=self.actor)
        self.assertTrue(context["latest_leads"])
        self.assertTrue(context["upcoming_appointments"])
        self.assert_private_absent(context)
        brief = build_owner_daily_brief(business=self.business, user=self.actor)
        self.assertTrue(brief["sources"])
        self.assert_private_absent(brief)

    def test_task_nested_labels_without_direct_client_are_guarded(self):
        self.task.client = None
        self.task.save(update_fields=["client"])
        response = self.api.get(f"/api/tasks/{self.task.pk}/")
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data["lead"], self.lead.pk)
        self.assertEqual(response.data["conversation"], self.conversation.pk)
        self.assert_private_absent(response.data)

    def test_outreach_preview_inline_and_action_mask_contacts(self):
        for path, params in ((f"/api/outreach/campaigns/{self.campaign.pk}/preview-audience/", {}),
                             (f"/api/outreach/campaigns/{self.campaign.pk}/", {"include_preview": "true"})):
            with self.subTest(path=path):
                response = self.api.get(path, params)
                self.assertEqual(response.status_code, 200, response.data)
                self.assert_private_absent(response.data)
        preview = preview_campaign_audience(self.campaign)
        self.assertEqual(preview["count"], 1)
        self.assert_private_absent(preview)

    def test_outreach_failed_appointment_projection_hides_client(self):
        response = self.api.get("/api/outreach/campaigns/appointment-automation-status/", {"business": self.business.pk})
        self.assertEqual(response.status_code, 200, response.data)
        self.assertTrue(response.data["failed_notifications"])
        self.assert_private_absent(response.data)
        self.assert_private_absent(appointment_automation_status(self.business))

    def test_parent_csv_client_reference_requires_view(self):
        for exporter in (export_deals, export_leads):
            with self.subTest(exporter=exporter.__name__):
                rows = list(csv.DictReader(io.StringIO(exporter(self.business, user=self.actor).content.decode())))
                self.assertEqual(len(rows), 1)
                self.assertEqual(rows[0]["client_id"], "")
        self.permission(True)
        self.assertEqual(list(csv.DictReader(io.StringIO(export_deals(self.business, user=self.actor).content.decode())))[0]["client_id"], str(self.customer.pk))

    @override_settings(EXPORT_SYNC_MAX_ROWS=0)
    def test_stored_parent_export_client_scope_revocation_requires_new_file(self):
        self.permission(True)
        _, job = request_entity_export(business=self.business, actor=self.actor, export_key="leads")
        job = process_export_job(job.pk)
        self.assertEqual(job.status, "succeeded", job.error)
        assert_export_download_access(job, self.actor)
        self.permission(False, "none")
        with self.assertRaises(PermissionDenied):
            assert_export_download_access(job, self.actor)

    def test_inbox_existing_client_response_respects_link_view(self):
        response = self.api.post(f"/api/inbox/conversations/{self.conversation.pk}/create-client/", {}, format="json")
        self.assertEqual(response.status_code, 200, response.data)
        self.assertFalse(response.data["created"])
        self.assertIsNone(response.data["client"])

    def test_next_read_permission_revocation_is_not_cached_globally(self):
        self.permission(True)
        allowed = self.api.get(f"/api/deals/{self.deal.pk}/")
        self.assertEqual(allowed.data["client"], self.customer.pk)
        self.permission(False, "none")
        hidden = self.api.get(f"/api/deals/{self.deal.pk}/")
        self.assertEqual(hidden.status_code, 200)
        self.assertIsNone(hidden.data["client"])

    def test_incoherent_foreign_client_is_hidden_even_for_owner_of_both(self):
        other = Business.objects.create(owner=self.owner, name="Other linked business", slug="other-linked-client")
        client = Client.objects.create(business=other, full_name=self.name, phone=self.phone, email=self.email)
        Deal.objects.filter(pk=self.deal.pk).update(client=client)
        self.deal.refresh_from_db()
        data = DealListSerializer(self.deal, context={"actor": self.owner}).data
        self.assertEqual(data["id"], self.deal.pk)
        self.assertIsNone(data["client"])
        self.assert_private_absent(data)

    def test_task_client_relation_respects_disabled_capability_for_owner(self):
        BusinessCapability.objects.update_or_create(business=self.business, module_key="clients", defaults={"is_enabled": False})
        task = Task.objects.select_related("business", "client", "lead__client", "conversation__client").get(pk=self.task.pk)
        data = TaskSerializer(task, context={"actor": self.owner}).data
        self.assertIsNone(data["client"])
        self.assertFalse(any(row["type"] == "client" for row in data["relations"]))
        self.assert_private_absent(data)

    def test_notification_action_preserves_allowed_contacts_without_sending(self):
        # Management of client delivery remains separate from personal staff state.
        Notification.objects.filter(pk=self.notification.pk).update(channel="email")
        self.api.force_authenticate(self.owner)
        response = self.api.post(f"/api/notifications/{self.notification.pk}/mark-read/", {}, format="json")
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data["client"], self.customer.pk)
        self.assertIn(self.name, response.data["text"])
        self.assertIsNotNone(response.data["read_at"])
        self.notification.refresh_from_db()
        self.assertEqual(self.notification.status, "failed")

    def test_external_identifier_search_preserves_permitted_non_phone_alias(self):
        self.permission(True)
        self.conversation.external_user_id = "synthetic-provider-alias"
        self.conversation.save(update_fields=["external_user_id"])
        response = self.api.get("/api/tasks/", {"business": self.business.pk, "search": "synthetic-provider-alias"})
        self.assertEqual(response.status_code, 200)
        rows = response.data.get("results", response.data) if isinstance(response.data, dict) else response.data
        self.assertEqual([row["id"] for row in rows], [self.task.pk])

    def test_parent_note_link_masks_client_without_censoring_parent_text(self):
        note = Note.objects.create(business=self.business, client=self.customer, author=self.owner,
                                   entity_type="Deal", entity_id=str(self.deal.pk), text="Authorized parent note")
        hidden = NoteSerializer(note, context={"actor": self.actor}).data
        self.assertIsNone(hidden["client"])
        self.assertEqual(hidden["text"], "Authorized parent note")
        allowed = NoteSerializer(note, context={"actor": self.owner}).data
        self.assertEqual(allowed["client"], self.customer.pk)
        self.assertEqual(allowed["text"], hidden["text"])

    def test_exact_client_filters_cannot_reconstruct_hidden_parent_link(self):
        routes = [(route, "client_ids") for route in ("deals", "leads", "appointments", "tasks")]
        routes += [("activity-events", "client_id"), ("outreach/consents", "client")]
        for allowed in (False, True):
            self.permission(allowed, "business" if allowed else "none")
            for route, key in routes:
                with self.subTest(route=route, allowed=allowed):
                    response = self.api.get(f"/api/{route}/", {"business": self.business.pk, key: str(self.customer.pk)})
                    self.assertEqual(response.status_code, 200, response.data)
                    self.assertEqual(response.data["count"], 1 if allowed else 0)
