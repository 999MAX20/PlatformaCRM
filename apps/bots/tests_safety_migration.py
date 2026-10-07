from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import TransactionTestCase


class CustomerSafetyMigrationTests(TransactionTestCase):
    def test_existing_history_and_owned_audience_preserved_shared_stays_private(self):
        before = [("ai_core", "0007_agent_conversations"), ("bots", "0010_botmessage_delivery_attempts_and_more")]
        after = [("ai_core", "0008_customer_knowledge_visibility")]
        executor = MigrationExecutor(connection)
        executor.migrate(before)
        try:
            executor = MigrationExecutor(connection)
            apps = executor.loader.project_state(list(executor.loader.applied_migrations)).apps
            owner = apps.get_model("accounts", "User").objects.create(username="safety-migration", email="migration@example.test")
            business = apps.get_model("businesses", "Business").objects.create(owner=owner, name="Migration", slug="safety-migration")
            Bot = apps.get_model("bots", "Bot")
            inbox = Bot.objects.create(business=business, name="Inbox", settings_json={"scenario": "inbox"})
            legacy = Bot.objects.create(business=business, name="Legacy", settings_json={})
            crm = Bot.objects.create(business=business, name="Staff", settings_json={"scenario": "crm"})
            Knowledge = apps.get_model("ai_core", "BusinessKnowledgeItem")
            items = [Knowledge.objects.create(business=business, bot=bot, title=str(index), content="Synthetic preserved material")
                     for index, bot in enumerate((inbox, legacy, crm, None))]
            items[-1].connected_agents.add(inbox)
            conversation = apps.get_model("bots", "BotConversation").objects.create(business=business, bot=inbox,
                channel="website", handoff_required=True, bot_enabled=False, metadata_json={"preserved": True})
            message = apps.get_model("bots", "BotMessage").objects.create(conversation=conversation,
                direction="inbound", text="Preserved synthetic message")
            executor = MigrationExecutor(connection)
            executor.migrate(after)
            current = executor.loader.project_state(after).apps
            migrated = current.get_model("ai_core", "BusinessKnowledgeItem").objects.filter(pk__in=[item.pk for item in items]).order_by("pk")
            self.assertEqual(list(migrated.values_list("customer_visible", flat=True)), [True, True, False, False])
            self.assertEqual(list(migrated.values_list("content", flat=True)), ["Synthetic preserved material"] * 4)
            self.assertTrue(migrated.last().connected_agents.filter(pk=inbox.pk).exists())
            saved = current.get_model("bots", "BotConversation").objects.get(pk=conversation.pk)
            self.assertEqual(saved.ai_safety_state, {})
            self.assertEqual(saved.metadata_json, {"preserved": True})
            self.assertTrue(saved.handoff_required)
            self.assertFalse(saved.bot_enabled)
            self.assertEqual(current.get_model("bots", "BotMessage").objects.get(pk=message.pk).text, "Preserved synthetic message")
        finally:
            MigrationExecutor(connection).migrate(after)
