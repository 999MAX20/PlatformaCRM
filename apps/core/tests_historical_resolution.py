from unittest.mock import patch
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.core.management.base import CommandError
from rest_framework.exceptions import ValidationError
from apps.businesses.models import Business
from apps.bots.models import Bot, BotConversation, BotMessage
from apps.integrations.models import BusinessConnector, ConnectorSyncRun
from apps.core.models import AuditLog
from apps.core.management.commands.resolve_stand_test_failures import resolve
from apps.bots.outbound_delivery import retry_outbound_message, claim_outbound_message, outbound_delivery_health
from apps.integrations.connectors import run_connector_healthcheck
from apps.integrations.sync_service import execute_connector_sync, retry_connector_sync_run
from apps.integrations.crm_mapping import touch_connector_activity

class HistoricalResolutionTests(TestCase):
    def setUp(self):
        owner = get_user_model().objects.create_user(username='resolution-owner')
        business = Business.objects.create(pk=2, owner=owner, name='Test', slug='resolution')
        bot = Bot.objects.create(pk=13, business=business, name='Test')
        conversation = BotConversation.objects.create(business=business, bot=bot, channel='website')
        for pk in [29, 30, 36]:
            BotMessage.objects.create(pk=pk, conversation=conversation, direction='outbound', sender_type='manager', status='failed', text='stale test', error_text='Channel provider is not connected.', payload_json={'history': pk})
        self.connector = BusinessConnector.objects.create(pk=4, business=business, provider='1c', name='1C', status='needs_attention', last_error='missing credentials')
        self.run = ConnectorSyncRun.objects.create(pk=9, business=business, connector=self.connector, mode='healthcheck', status='failed', error='missing credentials')

    def test_resolution_preserves_history_is_idempotent_and_blocks_replay(self):
        old = list(BotMessage.objects.order_by('pk').values())
        self.assertTrue(resolve())
        self.assertFalse(resolve())
        self.assertEqual(AuditLog.objects.count(), 5)
        for before, after in zip(old, BotMessage.objects.order_by('pk').values()):
            self.assertEqual(after['status'], 'cancelled')
            self.assertEqual({k:v for k,v in before.items() if k!='status'}, {k:v for k,v in after.items() if k!='status'})
        with patch('apps.bots.outbound_delivery.send_message') as send:
            for message in BotMessage.objects.all():
                with self.assertRaises(ValidationError): retry_outbound_message(message)
                self.assertIsNone(claim_outbound_message(message.pk))
            send.assert_not_called()
        self.connector.refresh_from_db(); self.run.refresh_from_db()
        self.assertEqual(self.connector.last_error, 'missing credentials')
        self.assertEqual(self.run.error, 'missing credentials')
        self.assertEqual(self.run.status, 'deferred')
        for action in [run_connector_healthcheck, execute_connector_sync]:
            with self.assertRaises(ValidationError): action(self.connector)
        with self.assertRaises(ValidationError): retry_connector_sync_run(self.run)
        touch_connector_activity(self.connector);self.connector.refresh_from_db()
        self.assertEqual(self.connector.status, 'deferred')
        self.assertEqual(ConnectorSyncRun.objects.count(), 1)
        self.assertEqual(outbound_delivery_health()['failed'], 0)

    def test_uncertain_delivery_rejected_without_partial_changes(self):
        BotMessage.objects.filter(pk=36).update(external_message_id='provider-confirmation')
        with self.assertRaises(CommandError): resolve()
        self.assertEqual(BotMessage.objects.filter(status='failed').count(), 3)
        self.assertEqual(AuditLog.objects.count(), 0)

    def test_wrong_tenant_rejected(self):
        self.run.business = Business.objects.create(owner=self.connector.business.owner,name='Other',slug='other')
        self.run.save(update_fields=['business'])
        with self.assertRaises(CommandError): resolve()
        self.assertEqual(AuditLog.objects.count(), 0)

    def test_audit_failure_rolls_back_all_changes(self):
        with patch.object(AuditLog.objects, 'create', side_effect=RuntimeError('audit unavailable')):
            with self.assertRaises(RuntimeError): resolve()
        self.assertEqual(BotMessage.objects.filter(status='failed').count(), 3)
        self.connector.refresh_from_db();self.assertEqual(self.connector.status,'needs_attention')
