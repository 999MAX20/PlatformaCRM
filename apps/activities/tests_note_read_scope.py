from datetime import timedelta
import json
from uuid import uuid4

from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.activities.models import Note
from apps.activities.serializers import NoteSerializer
from apps.bots.models import Bot, BotConversation, BotMessage
from apps.businesses.models import Business, BusinessCapability, BusinessMember, BusinessRole, RolePermission, Team, TeamMember
from apps.clients.models import Client
from apps.conversations.models import Conversation, Message
from apps.crm.models import Deal, Pipeline, PipelineStage
from apps.leads.models import Lead
from apps.payments.models import Payment
from apps.scheduling.models import Appointment, Resource
from apps.services.models import Service
from apps.tasks.models import Task


class NoteLinkedReadScopeTests(TestCase):
    def setUp(self):
        self.api = APIClient()
        self.owner = User.objects.create_user(username="note-owner", email="note-owner@example.invalid")
        self.actor = User.objects.create_user(username="note-reader", email="note-reader@example.invalid", role="business_operator")
        self.peer = User.objects.create_user(username="note-peer", email="note-peer@example.invalid", role="business_operator")
        self.business = Business.objects.create(owner=self.owner, name="Notes A", slug="notes-scope-a")
        self.role = BusinessRole.objects.create(business=self.business, name="Scoped history")
        self.member = BusinessMember.objects.create(business=self.business, user=self.actor, role="operator", business_role=self.role)
        self.peer_member = BusinessMember.objects.create(business=self.business, user=self.peer, role="operator")
        for resource in ("clients", "leads", "deals", "appointments", "tasks", "conversations", "payments", "analytics"):
            RolePermission.objects.create(business_role=self.role, resource=resource, action="view",
                                          scope="own" if resource == "tasks" else "business")
        for action in ("create", "update", "delete"):
            RolePermission.objects.create(business_role=self.role, resource="clients", action=action, scope="business")
        RolePermission.objects.create(business_role=self.role, resource="tasks", action="update", scope="own")
        self.customer = Client.objects.create(business=self.business, full_name="Synthetic note client")
        self.visible_task = Task.objects.create(business=self.business, client=self.customer, title="Own", assignee=self.actor)
        self.hidden_task = Task.objects.create(business=self.business, client=self.customer, title="Other", assignee=self.owner, created_by=self.owner)
        self.visible = self.note(self.visible_task, "visible-note-marker")
        self.hidden = self.note(self.hidden_task, "hidden-note-marker", author=self.actor)
        self.unlinked = Note.objects.create(business=self.business, client=self.customer, text="unlinked-note-marker")
        lead = Lead.objects.create(business=self.business, client=self.customer, responsible_user=self.actor)
        pipeline = Pipeline.objects.create(business=self.business, name="Notes pipeline", slug="notes-pipeline")
        stage = PipelineStage.objects.create(business=self.business, pipeline=pipeline, name="Open")
        deal = Deal.objects.create(business=self.business, client=self.customer, pipeline=pipeline, stage=stage, title="Notes deal", owner=self.actor)
        service = Service.objects.create(business=self.business, name="Generic service", duration_minutes=30)
        resource = Resource.objects.create(business=self.business, name="Workplace", linked_user=self.actor)
        appointment = Appointment.objects.create(business=self.business, client=self.customer, service=service, resource=resource,
                                                start_at=timezone.now() + timedelta(days=2), end_at=timezone.now() + timedelta(days=2, minutes=30))
        conversation = Conversation.objects.create(business=self.business, client=self.customer, channel="manual")
        message = Message.objects.create(conversation=conversation, sender_type="client", text="Synthetic")
        bot = Bot.objects.create(business=self.business, name="Synthetic bot")
        bot_conversation = BotConversation.objects.create(business=self.business, bot=bot, client=self.customer, channel="website", assigned_to=self.actor)
        bot_message = BotMessage.objects.create(conversation=bot_conversation, sender_type="client", direction="inbound", text="Synthetic")
        payment = Payment.objects.create(business=self.business, client=self.customer, kind="receipt", amount=1, currency="KZT",
                                         occurred_at=timezone.now(), method="cash", submission_id=uuid4(), request_hash="0" * 64)
        self.targets = [(self.customer, "clients"), (lead, "leads"), (deal, "deals"), (appointment, "appointments"),
                        (self.visible_task, "tasks"), (conversation, "conversations"), (message, "conversations"),
                        (bot_conversation, "conversations"), (bot_message, "conversations"), (payment, "payments")]
        self.api.force_authenticate(self.actor)

    def note(self, entity, text, **extra):
        return Note.objects.create(business=self.business, client=self.customer, entity_type=entity.__class__.__name__,
                                   entity_id=str(entity.pk), text=text, **extra)

    def listing(self, **params):
        response = self.api.get("/api/notes/", params)
        self.assertEqual(response.status_code, 200)
        return response

    def test_list_count_and_serialization_intersect_linked_own_scope(self):
        response = self.listing()
        self.assertEqual(response.data["count"], 2)
        self.assertEqual({row["id"] for row in response.data["results"]}, {self.visible.pk, self.unlinked.pk})
        self.assertNotIn("hidden-note-marker", json.dumps(response.data))
        detail = self.api.get(f"/api/notes/{self.visible.pk}/")
        self.assertEqual(detail.status_code, 200)
        self.assertEqual(detail.data, NoteSerializer(self.visible, context={"actor": self.actor}).data)

    def test_detail_does_not_reveal_forbidden_note_even_to_its_author(self):
        response = self.api.get(f"/api/notes/{self.hidden.pk}/")
        self.assertEqual(response.status_code, 404)
        self.assertNotIn("hidden-note-marker", json.dumps(response.data))

    def test_each_supported_resource_deny_hides_its_notes(self):
        for entity, resource in self.targets:
            note = self.note(entity, f"denied-{entity.__class__.__name__}")
            permission = self.role.permissions.get(resource=resource, action="view")
            permission.is_allowed = False
            permission.save()
            try:
                with self.subTest(resource=resource, entity=entity.__class__.__name__):
                    self.assertNotIn(note.pk, {row["id"] for row in self.listing().data["results"]})
                    self.assertEqual(self.api.get(f"/api/notes/{note.pk}/").status_code, 404)
            finally:
                permission.is_allowed = True
                permission.save()

    def test_owner_keeps_allowed_recognized_and_unlinked_history(self):
        notes = [self.note(entity, f"allowed-{entity.__class__.__name__}") for entity, _ in self.targets]
        self.api.force_authenticate(self.owner)
        ids = {row["id"] for row in self.listing().data["results"]}
        self.assertTrue({note.pk for note in notes}.issubset(ids))
        self.assertIn(self.hidden.pk, ids)
        self.assertIn(self.unlinked.pk, ids)

    def test_filtering_happens_before_pagination_and_counts(self):
        Note.objects.bulk_create([Note(business=self.business, client=self.customer, entity_type="Task",
                                      entity_id=str(self.hidden_task.pk), text=f"hidden-bulk-{i}") for i in range(60)])
        response = self.listing()
        self.assertEqual(response.data["count"], 2)
        self.assertEqual(len(response.data["results"]), 2)

    def test_case_alias_and_message_parent_scope(self):
        bot_conversation = next(entity for entity, _ in self.targets if isinstance(entity, BotConversation))
        bot_message = next(entity for entity, _ in self.targets if isinstance(entity, BotMessage))
        self.role.permissions.filter(resource="conversations", action="view").update(is_allowed=False)
        for alias, entity in (("tAsK", self.hidden_task), ("bot_conversation", bot_conversation), ("BOT_MESSAGE", bot_message)):
            note = Note.objects.create(business=self.business, client=self.customer, entity_type=alias, entity_id=str(entity.pk), text="alias-hidden")
            with self.subTest(alias=alias):
                self.assertEqual(self.api.get(f"/api/notes/{note.pk}/").status_code, 404)

    def test_team_scope_changes_only_the_permitted_linked_set(self):
        team = Team.objects.create(business=self.business, name="Notes team")
        TeamMember.objects.create(team=team, member=self.member)
        TeamMember.objects.create(team=team, member=self.peer_member)
        task = Task.objects.create(business=self.business, client=self.customer, title="Peer", assignee=self.peer)
        note = self.note(task, "peer-note")
        self.assertEqual(self.api.get(f"/api/notes/{note.pk}/").status_code, 404)
        self.role.permissions.filter(resource="tasks", action="view").update(scope="team")
        self.assertEqual(self.api.get(f"/api/notes/{note.pk}/").status_code, 200)
        self.assertEqual(self.api.get(f"/api/notes/{self.hidden.pk}/").status_code, 404)

    def test_capability_and_current_view_revocation_apply_on_next_read(self):
        self.assertEqual(self.api.get(f"/api/notes/{self.visible.pk}/").status_code, 200)
        self.role.permissions.filter(resource="tasks", action="view").update(is_allowed=False)
        self.assertEqual(self.api.get(f"/api/notes/{self.visible.pk}/").status_code, 404)
        self.role.permissions.filter(resource="tasks", action="view").update(is_allowed=True)
        BusinessCapability.objects.update_or_create(business=self.business, module_key="tasks", defaults={"is_enabled": False})
        self.assertEqual(self.api.get(f"/api/notes/{self.visible.pk}/").status_code, 404)

    def test_archived_linked_history_remains_available(self):
        Task.objects.filter(pk=self.visible_task.pk).update(is_archived=True)
        self.assertEqual(self.api.get(f"/api/notes/{self.visible.pk}/").status_code, 200)

    def test_foreign_dangling_and_malformed_recognized_links_are_hidden(self):
        other = Business.objects.create(owner=self.owner, name="Other notes", slug="other-notes-scope")
        task = Task.objects.create(business=other, title="Foreign")
        for target in (str(task.pk), "missing-id", "999999999999"):
            note = Note.objects.create(business=self.business, client=self.customer, entity_type="Task", entity_id=target, text="invalid-target-marker")
            with self.subTest(target_class=target[:8]):
                self.assertEqual(self.api.get(f"/api/notes/{note.pk}/").status_code, 404)

    def test_hidden_get_object_cannot_be_used_for_blind_mutation(self):
        url = f"/api/notes/{self.hidden.pk}/"
        self.assertEqual(self.api.patch(url, {"text": "Changed"}, format="json").status_code, 404)
        self.assertEqual(self.api.delete(url).status_code, 404)
        self.hidden.refresh_from_db()
        self.assertEqual(self.hidden.text, "hidden-note-marker")

    def test_inherited_archive_action_cannot_serialize_a_forbidden_note(self):
        response = self.api.post(f"/api/notes/{self.hidden.pk}/archive/", {}, format="json")
        self.assertEqual(response.status_code, 404)
        self.assertNotIn("hidden-note-marker", json.dumps(response.data))

    def test_visible_note_create_update_and_delete_keep_existing_guards(self):
        response = self.api.post("/api/notes/", {"business": self.business.pk, "client": self.customer.pk,
                                 "entity_type": "Task", "entity_id": str(self.visible_task.pk), "text": "Created"}, format="json")
        self.assertEqual(response.status_code, 201)
        url = f"/api/notes/{response.data['id']}/"
        self.assertEqual(self.api.patch(url, {"text": "Edited"}, format="json").status_code, 200)
        self.assertEqual(self.api.delete(url).status_code, 204)

    def test_crm_card_preexisting_note_scope_remains_consistent(self):
        response = self.api.get(f"/api/clients/{self.customer.pk}/crm-card/")
        self.assertEqual(response.status_code, 200)
        self.assertNotIn("hidden-note-marker", json.dumps(response.data["notes"]))
        self.assertIn("visible-note-marker", json.dumps(response.data["notes"]))
