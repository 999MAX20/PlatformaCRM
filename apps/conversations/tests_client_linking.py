from unittest.mock import patch

from django.core import signing
from django.test import TestCase
from django.utils import timezone
from rest_framework.exceptions import ValidationError
from rest_framework.test import APIClient

from apps.activities.models import ActivityEvent
from apps.bots.models import BotMessage
from apps.businesses.access import Resources
from apps.clients.models import Client
from apps.conversations.client_linking import SALT, link_conversation_client
from apps.conversations.inbox_helpers import QUALIFICATION_PREVIEW_META_KEY, qualification_preview_for_execution
from apps.conversations import tests_inbox_context as context_fixture
from apps.core.models import AuditLog
from apps.tasks.models import Task


class ClientLinkingTests(TestCase):
    setUpTestData = classmethod(context_fixture.InboxContextTests.setUpTestData.__func__)
    permission = context_fixture.InboxContextTests.permission

    def setUp(self):
        self.api = APIClient()
        self.api.force_authenticate(self.owner)
        self.target = Client.objects.create(business=self.business, full_name="Replacement customer")
        self.url = f"/api/inbox/conversations/{self.conversation.pk}/link-client/"

    def post(self, **extra):
        return self.api.post(self.url, {"client_id": self.target.pk, **extra}, format="json")

    def unchanged(self):
        self.conversation.refresh_from_db()
        self.assertEqual((self.conversation.client_id, self.conversation.lead_id, self.conversation.deal_id),
                         (self.customer.pk, self.lead.pk, self.deal.pk))

    def test_preview_has_real_links_and_no_side_effects(self):
        response = self.post()
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data["requires_confirmation"])
        self.assertEqual(response.data["previous_client"]["title"], self.customer.full_name)
        self.assertEqual([row["entity"]["id"] for row in response.data["conflicts"]], [self.lead.pk, self.deal.pk])
        self.unchanged()
        self.assertEqual(ActivityEvent.objects.count(), 0)
        self.assertEqual(AuditLog.objects.count(), 0)

    def test_confirm_preserves_records_history_messages_and_retry_is_noop(self):
        self.now = timezone.now()
        appointment = context_fixture.InboxContextTests.appointment(self)
        message = BotMessage.objects.create(conversation=self.conversation, direction="inbound", text="Original request")
        task = Task.objects.create(business=self.business, client=self.customer, conversation=self.conversation, title="Original work")
        token = self.post().data["confirmation_token"]
        result = self.post(confirmation_token=token)
        self.assertEqual(result.status_code, 200)
        self.conversation.refresh_from_db()
        self.assertEqual(self.conversation.client_id, self.target.pk)
        self.assertIsNone(self.conversation.lead_id)
        self.assertIsNone(self.conversation.deal_id)
        for entity in (self.lead, self.deal, task, appointment):
            entity.refresh_from_db()
            self.assertEqual(entity.client_id, self.customer.pk)
        message.refresh_from_db()
        self.assertEqual(message.text, "Original request")
        self.assertEqual(message.conversation_id, self.conversation.pk)
        self.assertEqual(ActivityEvent.objects.count(), 1)
        audit = AuditLog.objects.get(metadata__kind="conversation_client_relinked")
        self.assertEqual(audit.metadata["detached"], {"lead": self.lead.pk, "deal": self.deal.pk})
        self.assertEqual(self.post(confirmation_token=token).status_code, 200)
        self.assertEqual(ActivityEvent.objects.count(), 1)
        self.assertEqual(AuditLog.objects.count(), 1)

    def test_replacement_invalidates_old_crm_approval_but_preserves_other_metadata(self):
        self.conversation.metadata_json = {
            QUALIFICATION_PREVIEW_META_KEY: {"qualification": {}, "last_message_id": None},
            "retained_history": {"original": "unchanged"},
        }
        self.conversation.save(update_fields=["metadata_json"])
        token = self.post().data["confirmation_token"]
        self.post(confirmation_token=token)
        self.conversation.refresh_from_db()
        self.assertEqual(self.conversation.metadata_json, {"retained_history": {"original": "unchanged"}})
        with self.assertRaises(ValidationError):
            qualification_preview_for_execution(self.conversation)

    def test_token_cannot_be_reused_by_another_actor(self):
        token = self.post().data["confirmation_token"]
        self.permission(Resources.CONVERSATIONS, action="update")
        self.permission(Resources.CLIENTS)
        self.api.force_authenticate(self.operator)
        self.assertTrue(self.post(confirmation_token=token).data["requires_confirmation"])
        self.unchanged()

    def test_target_client_access_is_rechecked(self):
        self.permission(Resources.CONVERSATIONS, action="update")
        self.permission(Resources.CLIENTS)
        self.api.force_authenticate(self.operator)
        token = self.post().data["confirmation_token"]
        self.permission(Resources.CLIENTS, allowed=False)
        self.assertEqual(self.post(confirmation_token=token).status_code, 403)
        self.unchanged()

    def test_same_client_is_noop_even_with_existing_links(self):
        self.assertEqual(self.post(client_id=self.customer.pk).status_code, 200)
        self.unchanged()
        self.assertEqual(AuditLog.objects.count(), 0)

    def test_no_conflicts_links_immediately_and_keeps_compatible_links(self):
        self.lead.client = self.target
        self.lead.save(update_fields=["client"])
        self.deal.client = self.target
        self.deal.save(update_fields=["client"])
        self.assertNotIn("requires_confirmation", self.post().data)
        self.conversation.refresh_from_db()
        self.assertEqual(self.conversation.client_id, self.target.pk)
        self.assertEqual(self.conversation.lead_id, self.lead.pk)
        self.assertEqual(self.conversation.deal_id, self.deal.pk)

    def test_only_incompatible_link_is_removed(self):
        self.lead.client = self.target
        self.lead.save(update_fields=["client"])
        preview = self.post().data
        self.assertEqual([row["kind"] for row in preview["conflicts"]], ["deal"])
        self.post(confirmation_token=preview["confirmation_token"])
        self.conversation.refresh_from_db()
        self.assertEqual(self.conversation.lead_id, self.lead.pk)
        self.assertIsNone(self.conversation.deal_id)

    def test_changed_relations_or_target_require_fresh_confirmation(self):
        token = self.post().data["confirmation_token"]
        self.conversation.deal = None
        self.conversation.save(update_fields=["deal"])
        response = self.post(confirmation_token=token)
        self.assertTrue(response.data["requires_confirmation"])
        self.assertEqual(len(response.data["conflicts"]), 1)
        self.conversation.refresh_from_db()
        self.assertEqual(self.conversation.client_id, self.customer.pk)
        third = Client.objects.create(business=self.business, full_name="Third")
        self.assertTrue(self.post(client_id=third.pk, confirmation_token=response.data["confirmation_token"]).data["requires_confirmation"])

    def test_invalid_and_expired_tokens_cannot_execute(self):
        token = self.post().data["confirmation_token"]
        for invalid in (token + "forged", "true"):
            self.assertTrue(self.post(confirmation_token=invalid).data["requires_confirmation"])
            self.unchanged()
        with patch("apps.conversations.client_linking.signing.loads", side_effect=signing.SignatureExpired):
            self.assertTrue(self.post(confirmation_token=token).data["requires_confirmation"])
        self.unchanged()

    def test_foreign_client_and_conversation_denied(self):
        foreign = Client.objects.create(business=self.other, full_name="Foreign secret")
        self.assertEqual(self.post(client_id=foreign.pk).status_code, 400)
        self.api.force_authenticate(self.other_owner)
        self.assertIn(self.post().status_code, (403, 404))
        self.unchanged()

    def test_permission_rechecked_before_execution(self):
        self.permission(Resources.CONVERSATIONS, action="update")
        self.permission(Resources.CLIENTS)
        self.api.force_authenticate(self.operator)
        token = self.post().data["confirmation_token"]
        self.permission(Resources.CONVERSATIONS, action="update", allowed=False)
        self.assertEqual(self.post(confirmation_token=token).status_code, 403)
        self.unchanged()

    def test_hidden_links_have_no_identity_in_preview_or_token(self):
        self.permission(Resources.CONVERSATIONS, action="update")
        self.permission(Resources.CLIENTS)
        self.permission(Resources.LEADS, allowed=False)
        self.permission(Resources.DEALS, allowed=False)
        self.api.force_authenticate(self.operator)
        preview = self.post().data
        self.assertEqual(preview["conflicts"], [{"kind": "lead", "entity": None}, {"kind": "deal", "entity": None}])
        self.assertRegex(signing.loads(preview["confirmation_token"], salt=SALT), r"^[0-9a-f]{64}$")
        self.assertEqual(self.post(confirmation_token=preview["confirmation_token"]).status_code, 200)

    def test_audit_failure_rolls_back_links_and_activity(self):
        token = self.post().data["confirmation_token"]
        with patch("apps.conversations.client_linking.write_actor_audit_log", side_effect=RuntimeError("audit unavailable")):
            with self.assertRaises(RuntimeError):
                link_conversation_client(self.conversation, actor=self.owner, client_id=self.target.pk, confirmation_token=token)
        self.unchanged()
        self.assertEqual(ActivityEvent.objects.count(), 0)

    def test_other_link_actions_reload_after_a_client_replacement(self):
        from apps.leads.models import Lead
        token = self.post().data["confirmation_token"]
        self.post(confirmation_token=token)
        new_lead = Lead.objects.create(business=self.business, client=self.target, message="New work")
        # The object obtained before waiting for the replacement lock is stale.
        with patch("apps.conversations.inbox_views.InboxConversationViewSet.get_object", return_value=self.conversation):
            response = self.api.post(f"/api/inbox/conversations/{self.conversation.pk}/link-lead/", {"lead_id": new_lead.pk})
        self.assertEqual(response.status_code, 200)
        self.conversation.refresh_from_db()
        self.assertEqual(self.conversation.client_id, self.target.pk)
        self.assertEqual(self.conversation.lead_id, new_lead.pk)
