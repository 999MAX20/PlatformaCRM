from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from unittest import skipUnless

from django.db import close_old_connections, connection, connections
from django.test import TransactionTestCase

from apps.accounts.models import User
from apps.bots.models import Bot, BotConversation
from apps.businesses.models import Business, BusinessMember
from apps.clients.models import Client
from apps.conversations.pipeline import run_conversation_pipeline
from apps.crm.models import Deal
from apps.leads.models import Lead
from apps.tasks.models import Task


@skipUnless(connection.vendor == "postgresql", "PostgreSQL lock regression; required CI uses PostgreSQL")
class ConversationPostgresLockRegressionTests(TransactionTestCase):
    def setUp(self):
        self.owner = User.objects.create_user(
            username="pg-pipeline-owner", email="pg-pipeline-owner@example.com",
            password=None, role=User.Roles.BUSINESS_OWNER,
        )
        self.business = Business.objects.create(owner=self.owner, name="PG pipeline", slug="pg-pipeline")
        BusinessMember.objects.create(business=self.business, user=self.owner, role=BusinessMember.Roles.OWNER)
        self.bot = Bot.objects.create(business=self.business, name="Synthetic website", status=Bot.Statuses.ACTIVE)
        self.conversation = BotConversation.objects.create(
            business=self.business, bot=self.bot, channel=BotConversation.Channels.WEBSITE,
            external_user_id="pg-pipeline-visitor",
        )

    def identifiers(self, result):
        return result.client.id, result.lead.id, result.deal.id, result.task.id

    def assert_one_chain(self):
        for model in (Client, Lead, Deal, Task):
            self.assertEqual(model.objects.filter(business=self.business).count(), 1)

    def test_nullable_relations_can_create_one_chain(self):
        result = run_conversation_pipeline(conversation=self.conversation, actor=self.owner)
        self.assertTrue(all(result.created.values()))
        self.assert_one_chain()
        self.assertEqual(result.conversation.business_id, self.business.id)

    def test_linked_entities_and_assignee_are_reused_on_repeat(self):
        first = run_conversation_pipeline(conversation=self.conversation, actor=self.owner)
        BotConversation.objects.filter(id=self.conversation.id).update(assigned_to=self.owner)
        second = run_conversation_pipeline(conversation=self.conversation, actor=self.owner)
        self.assertEqual(self.identifiers(first), self.identifiers(second))
        self.assertFalse(any(second.created.values()))
        self.assert_one_chain()

    def test_two_connections_do_not_create_duplicate_chain(self):
        barrier = Barrier(2)
        conversation_id, owner_id = self.conversation.id, self.owner.id

        def invoke():
            close_old_connections()
            try:
                conversation = BotConversation.objects.get(id=conversation_id)
                owner = User.objects.get(id=owner_id)
                barrier.wait(timeout=5)
                result = run_conversation_pipeline(conversation=conversation, actor=owner)
                return self.identifiers(result)
            finally:
                connections.close_all()

        with ThreadPoolExecutor(max_workers=2) as executor:
            futures = [executor.submit(invoke) for _ in range(2)]
            results = [future.result(timeout=15) for future in futures]
        self.assertEqual(results[0], results[1])
        self.assert_one_chain()
