from unittest.mock import patch

from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.bots.models import Bot, BotConversation, BotMessage
from apps.businesses.models import Business, BusinessMember, BusinessRole, RolePermission, Team, TeamMember
from apps.activities.models import ActivityEvent
from apps.core.models import AuditLog
from apps.notifications.models import Notification
from apps.clients.models import Client
from apps.conversations.models import Conversation, Message


class MessageHistoryBoundaryTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.owner = User.objects.create_user(username="history-owner", email="history-owner@example.test", role="business_owner")
        cls.actor = User.objects.create_user(username="history-operator", email="history-operator@example.test", role="business_operator")
        cls.peer = User.objects.create_user(username="history-peer", email="history-peer@example.test", role="business_operator")
        cls.business = Business.objects.create(owner=cls.owner, name="Messages", slug="message-history")
        cls.role = BusinessRole.objects.create(business=cls.business, name="View all, update own")
        for action, scope in (("view", "business"), ("create", "business"), ("update", "own")):
            RolePermission.objects.create(business_role=cls.role, resource="conversations", action=action, scope=scope)
        for user in (cls.actor, cls.peer):
            BusinessMember.objects.create(business=cls.business, user=user, role="operator", business_role=cls.role)
        cls.bot = Bot.objects.create(business=cls.business, name="Inbox")
        cls.own = BotConversation.objects.create(business=cls.business, bot=cls.bot, channel="website", assigned_to=cls.actor)
        cls.other = BotConversation.objects.create(business=cls.business, bot=cls.bot, channel="website", assigned_to=cls.peer)
        cls.sent = BotMessage.objects.create(conversation=cls.other, direction="outbound", sender_type="manager", text="Original", status="sent")
        cls.inbound = BotMessage.objects.create(conversation=cls.own, direction="inbound", text="Owned")
        customer = Client.objects.create(business=cls.business, full_name="Customer")
        cls.legacy = Conversation.objects.create(business=cls.business, client=customer, channel="manual")
        cls.legacy_message = Message.objects.create(conversation=cls.legacy, sender_type="client", text="Historical")

    def setUp(self):
        self.api = APIClient()
        self.api.force_authenticate(self.owner)

    def test_saved_messages_cannot_be_rewritten_or_requeued_without_direction(self):
        for path, payload in ((f"/api/bot-messages/{self.sent.pk}/", {"status": "queued", "text": "Forged", "sender_type": "ai", "payload_json": {"provider": "forged"}}),
                              (f"/api/messages/{self.legacy_message.pk}/", {"text": "Forged", "sender_type": "manager", "raw_payload": {"forged": True}})):
            response = self.api.patch(path, payload, format="json")
            self.assertEqual(response.status_code, 405, response.data)
        self.sent.refresh_from_db()
        self.legacy_message.refresh_from_db()
        self.assertEqual((self.sent.status, self.sent.text), ("sent", "Original"))
        self.assertEqual(self.legacy_message.text, "Historical")

    def test_create_requires_update_access_to_the_parent_conversation(self):
        self.api.force_authenticate(self.actor)
        response = self.api.post("/api/bot-messages/", {"conversation": self.other.pk, "direction": "inbound", "sender_type": "client", "text": "Injected"}, format="json")
        self.assertEqual(response.status_code, 403, response.data)
        self.assertFalse(BotMessage.objects.filter(text="Injected").exists())

    def test_own_message_reads_follow_conversation_scope(self):
        RolePermission.objects.filter(business_role=self.role, action="view").update(scope="own")
        self.api.force_authenticate(self.actor)
        response = self.api.get("/api/bot-messages/")
        self.assertEqual(response.status_code, 200, response.data)
        rows = response.data.get("results", []) if isinstance(response.data, dict) else response.data
        self.assertEqual([row["id"] for row in rows], [self.inbound.pk])
        self.assertEqual(self.api.get(f"/api/bot-messages/{self.sent.pk}/").status_code, 404)

    def test_put_delete_and_reparent_cannot_modify_history(self):
        for actor in (self.owner, self.actor):
            self.api.force_authenticate(actor)
            for path in (f"/api/bot-messages/{self.sent.pk}/", f"/api/messages/{self.legacy_message.pk}/"):
                for method in (self.api.put, self.api.delete):
                    self.assertEqual(method(path, {"conversation": self.own.pk, "text": "Changed"}, format="json").status_code, 405)
        self.sent.refresh_from_db()
        self.assertEqual(self.sent.conversation_id, self.other.pk)
        self.assertTrue(Message.objects.filter(pk=self.legacy_message.pk).exists())

    def test_inbound_cannot_supply_provider_state_or_impersonate_staff(self):
        base = {"conversation": self.own.pk, "direction": "inbound", "text": "Input"}
        forbidden = {"status": "queued", "payload_json": {"provider": "forged"}, "external_message_id": "external",
                     "error_text": "Forged", "delivery_attempts": 0, "delivery_max_attempts": 100,
                     "delivery_next_retry_at": None, "delivery_locked_at": None,
                     "delivery_idempotency_key": "forged", "sent_at": timezone.now().isoformat(),
                     "delivered_at": None, "read_at": None, "created_at": timezone.now().isoformat()}
        before = BotMessage.objects.count()
        for key, value in forbidden.items():
            with self.subTest(field=key):
                response = self.api.post("/api/bot-messages/", {**base, key: value}, format="json")
                self.assertEqual(response.status_code, 400, response.data)
        for sender in ("manager", "system", "ai", "bot"):
            self.assertEqual(self.api.post("/api/bot-messages/", {**base, "sender_type": sender}, format="json").status_code, 400)
        self.assertEqual(self.api.post("/api/bot-messages/", {**base, "direction": "outbound"}, format="json").status_code, 400)
        self.assertEqual(BotMessage.objects.count(), before)
        for extra in ({"sender_type": "manager"}, {"raw_payload": {"forged": True}}, {"created_at": timezone.now().isoformat()}):
            response = self.api.post("/api/messages/", {"conversation": self.legacy.pk, "text": "Input", "sender_type": "client", **extra}, format="json")
            self.assertEqual(response.status_code, 400, response.data)

    def test_supported_inbound_text_keeps_registration_and_server_defaults(self):
        self.api.force_authenticate(self.actor)
        response = self.api.post("/api/bot-messages/", {"conversation": self.own.pk, "direction": "inbound", "text": "New incoming"}, format="json")
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual((response.data["sender_type"], response.data["status"], response.data["payload_json"]), ("client", "received", {}))
        self.own.refresh_from_db()
        self.assertEqual(self.own.unread_count, 1)
        self.assertIsNotNone(self.own.last_inbound_at)
        self.api.force_authenticate(self.owner)
        response = self.api.post("/api/messages/", {"conversation": self.legacy.pk, "text": "Manual incoming", "sender_type": "client"}, format="json")
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(response.data["raw_payload"], {})

    def test_intake_requires_both_parent_view_update_and_create_permission(self):
        self.api.force_authenticate(self.actor)
        payload = {"conversation": self.own.pk, "direction": "inbound", "text": "Denied"}
        for action in ("view", "update", "create"):
            permission = RolePermission.objects.get(business_role=self.role, action=action)
            permission.is_allowed = False
            permission.save()
            response = self.api.post("/api/bot-messages/", payload, format="json")
            self.assertEqual(response.status_code, 403, response.data)
            permission.is_allowed = True
            permission.save()
        self.assertFalse(BotMessage.objects.filter(text="Denied").exists())

    def test_team_scope_uses_parent_for_list_detail_and_create(self):
        RolePermission.objects.filter(business_role=self.role, action__in=("view", "update")).update(scope="team")
        team = Team.objects.create(business=self.business, name="Team")
        for user in (self.actor, self.peer):
            TeamMember.objects.create(team=team, member=BusinessMember.objects.get(business=self.business, user=user))
        outside = BotConversation.objects.create(business=self.business, bot=self.bot, channel="website", assigned_to=self.owner)
        hidden = BotMessage.objects.create(conversation=outside, direction="inbound", text="Hidden")
        self.api.force_authenticate(self.actor)
        response = self.api.get("/api/bot-messages/")
        rows = response.data.get("results", []) if isinstance(response.data, dict) else response.data
        self.assertEqual({row["id"] for row in rows}, {self.sent.pk, self.inbound.pk})
        self.assertEqual(self.api.get(f"/api/bot-messages/{self.sent.pk}/").status_code, 200)
        self.assertEqual(self.api.get(f"/api/bot-messages/{hidden.pk}/").status_code, 404)
        self.assertEqual(self.api.post("/api/bot-messages/", {"conversation": self.other.pk, "direction": "inbound", "text": "Team input"}).status_code, 201)
        self.assertEqual(self.api.post("/api/bot-messages/", {"conversation": outside.pk, "direction": "inbound", "text": "Denied"}).status_code, 403)

    def test_foreign_tenant_message_and_intake_are_inaccessible(self):
        foreign = Business.objects.create(owner=self.peer, name="Foreign", slug="history-foreign")
        bot = Bot.objects.create(business=foreign, name="Foreign")
        conversation = BotConversation.objects.create(business=foreign, bot=bot, channel="website")
        message = BotMessage.objects.create(conversation=conversation, direction="inbound", text="Foreign")
        self.assertEqual(self.api.get(f"/api/bot-messages/{message.pk}/").status_code, 404)
        self.assertEqual(self.api.post("/api/bot-messages/", {"conversation": conversation.pk, "direction": "inbound", "text": "Denied"}).status_code, 403)
        customer = Client.objects.create(business=foreign, full_name="Foreign")
        legacy = Conversation.objects.create(business=foreign, client=customer, channel="manual")
        message = Message.objects.create(conversation=legacy, sender_type="client", text="Foreign legacy")
        self.assertEqual(self.api.get(f"/api/messages/{message.pk}/").status_code, 404)
        self.assertEqual(self.api.post("/api/messages/", {"conversation": legacy.pk, "text": "Denied", "sender_type": "client"}).status_code, 403)

    def test_inbound_registration_or_audit_failure_rolls_back_message_and_effects(self):
        self.api.raise_request_exception = False
        before = (BotMessage.objects.count(), ActivityEvent.objects.count(), AuditLog.objects.count(), Notification.objects.count())
        for target in ("apps.bots.serializers.register_bot_message", "apps.core.viewsets.write_audit_log"):
            with patch(target, side_effect=RuntimeError("Injected write failure")):
                response = self.api.post("/api/bot-messages/", {"conversation": self.own.pk, "direction": "inbound", "text": "Rollback"}, format="json")
            self.assertEqual(response.status_code, 500)
            self.own.refresh_from_db()
            self.assertEqual(self.own.unread_count, 0)
            self.assertEqual((BotMessage.objects.count(), ActivityEvent.objects.count(), AuditLog.objects.count(), Notification.objects.count()), before)

    @override_settings(OUTBOUND_MESSAGES_RUN_INLINE=False)
    def test_send_retry_keep_parent_permissions_and_server_authorship(self):
        self.api.force_authenticate(self.actor)
        own_url = f"/api/inbox/conversations/{self.own.pk}"
        other_url = f"/api/inbox/conversations/{self.other.pk}"
        self.assertEqual(self.api.post(f"{other_url}/messages/", {"text": "Forbidden"}).status_code, 403)
        self.assertEqual(self.api.post(f"{other_url}/retry-message/", {"message_id": self.sent.pk}).status_code, 403)
        self.assertEqual(self.api.post(f"{own_url}/messages/", {"text": "Impersonate", "sender_type": "ai"}).status_code, 400)
        with patch("apps.bots.outbound_delivery.schedule_outbound_delivery") as schedule:
            payload = {"text": "Real reply", "payload_json": {"forged": True}, "status": "sent"}
            response = self.api.post(f"{own_url}/messages/", payload, format="json", HTTP_IDEMPOTENCY_KEY="history-send")
            self.assertEqual(response.status_code, 201, response.data)
            repeat = self.api.post(f"{own_url}/messages/", payload, format="json", HTTP_IDEMPOTENCY_KEY="history-send")
            self.assertEqual(repeat.data["id"], response.data["id"])
            schedule.assert_called_once()
        message = BotMessage.objects.get(pk=response.data["id"])
        self.assertEqual((message.sender_type, message.direction, message.status), ("manager", "outbound", "queued"))
        self.assertNotIn("forged", message.payload_json)
        message.status = "failed"
        message.save(update_fields=["status"])
        with patch("apps.bots.outbound_delivery.schedule_outbound_delivery") as schedule:
            response = self.api.post(f"{own_url}/retry-message/", {"message_id": message.pk, "text": "Forged retry"}, HTTP_IDEMPOTENCY_KEY="history-retry")
            self.assertEqual(response.status_code, 201, response.data)
            repeat = self.api.post(f"{own_url}/retry-message/", {"message_id": message.pk}, HTTP_IDEMPOTENCY_KEY="history-retry")
            self.assertEqual(repeat.status_code, 201, repeat.data)
            schedule.assert_called_once()
        message.refresh_from_db()
        self.assertEqual((message.text, message.status), ("Real reply", "queued"))
        self.assertEqual(self.api.post(f"{own_url}/retry-message/", {"message_id": self.sent.pk}).status_code, 400)
        self.assertEqual(self.api.post(f"{own_url}/retry-message/", {"message_id": self.inbound.pk}).status_code, 400)
        self.assertEqual(self.api.post(f"{own_url}/retry-message/", {"message_id": message.pk}).status_code, 400)
        message.status = "sent"
        message.save(update_fields=["status"])
        self.assertEqual(self.api.post(f"{own_url}/retry-message/", {"message_id": message.pk}).status_code, 400)

    def test_intake_rechecks_parent_after_validation_under_lock(self):
        from apps.conversations.message_history import InboundMessageSerializerMixin

        self.api.force_authenticate(self.actor)
        original = InboundMessageSerializerMixin.assert_parent_access
        checked = []

        def reassign_after_validation(serializer, conversation):
            original(serializer, conversation)
            checked.append(conversation.pk)
            if len(checked) == 1:
                BotConversation.objects.filter(pk=conversation.pk).update(assigned_to=self.peer)

        with patch.object(InboundMessageSerializerMixin, "assert_parent_access", reassign_after_validation):
            response = self.api.post("/api/bot-messages/", {"conversation": self.own.pk, "direction": "inbound", "text": "Stale input"}, format="json")
        self.assertEqual(response.status_code, 403, response.data)
        self.assertFalse(BotMessage.objects.filter(text="Stale input").exists())
        self.own.refresh_from_db()
        self.assertEqual(self.own.assigned_to_id, self.peer.pk)

    def test_serializers_reject_history_edits_and_contextless_intake(self):
        from apps.bots.serializers import BotMessageSerializer
        from apps.conversations.serializers import MessageSerializer
        from rest_framework.exceptions import PermissionDenied

        for serializer, instance in ((BotMessageSerializer, self.sent), (MessageSerializer, self.legacy_message)):
            edit = serializer(instance, data={"text": "Changed"}, partial=True)
            self.assertFalse(edit.is_valid())
        creation = BotMessageSerializer(data={"conversation": self.own.pk, "direction": "inbound", "text": "No actor"})
        with self.assertRaises(PermissionDenied):
            creation.is_valid(raise_exception=True)
