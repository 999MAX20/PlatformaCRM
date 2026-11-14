import json
from types import SimpleNamespace
from unittest.mock import patch

from django.test import TestCase
from rest_framework.exceptions import PermissionDenied
from rest_framework.test import APIClient

from apps.bots import tests_runtime_configuration as fixtures
from apps.bots import tests_automatic_booking as booking_fixtures
from apps.bots.ai_settings import validate_ai_settings
from apps.bots.automation_policy import automatic_creation_actor
from apps.bots.models import BotConversation, BotMessage
from apps.bots.runtime_configuration import agent_runtime_fingerprint
from apps.clients.models import Client
from apps.crm.models import Deal, Pipeline, PipelineStage
from apps.leads.models import Lead
from apps.tasks.models import Task
from apps.conversations.ai_qualification import ConversationQualification
from apps.conversations.auto_pipeline import maybe_run_auto_pipeline, resolve_auto_pipeline_config
from apps.conversations.booking import store_offered_slots


class CustomerActionsTests(TestCase):
    def setUp(self):
        fixtures.RuntimeConfigurationTests.setUp(self)
        self.bot.settings_json = {'_automatic_actor_id': self.business.owner_id, 'auto_crm_pipeline': {
            'mode': 'customer_actions', 'enabled': True, 'auto_send_reply': False,
            'creation_policy': 'automatic', 'task_creation_policy': 'automatic',
            'appointment_creation_policy': 'staff_confirmation', 'create_appointment': False,
        }}
        self.bot.save()
        self.profile.allowed_tools_json = {'tools': ['create_client', 'create_task', 'create_lead', 'create_deal']}
        self.profile.save()
        self.qualification = ConversationQualification(intent='purchase_interest', confidence=.9, summary='Follow up',
            should_create_lead=True, should_create_deal=True, should_create_task=True, next_action='Call customer')

    def run_pipeline(self):
        with patch('apps.conversations.auto_pipeline.qualify_conversation', return_value=(self.qualification, None)):
            return maybe_run_auto_pipeline(conversation=self.conversation, message=self.message)

    def test_creates_client_task_once_without_legacy_entities(self):
        result = self.run_pipeline()
        self.assertEqual(result.status, 'proposed_actions')
        self.assertTrue(result.result.created['task'])
        self.run_pipeline()
        self.assertEqual(Client.objects.count(), 1)
        self.assertEqual(Task.objects.count(), 1)
        self.assertFalse(Lead.objects.exists() or Deal.objects.exists())

    def test_manual_task_policy_does_not_inherit_automatic_booking_consent(self):
        pipeline = self.bot.settings_json['auto_crm_pipeline']
        pipeline.update(task_creation_policy='staff_confirmation', appointment_creation_policy='automatic')
        self.bot.save()
        result = self.run_pipeline()
        self.assertFalse(Task.objects.exists())
        self.assertEqual(result.confirmation_policy['requires_explicit_confirmation'], ['create_task'])
        with self.assertRaises(PermissionDenied):
            automatic_creation_actor(self.conversation, {'create_task'})

    def test_direct_legacy_creation_is_denied(self):
        for action in ('create_lead', 'create_deal'):
            with self.assertRaises(PermissionDenied):
                automatic_creation_actor(self.conversation, {action})
        self.assertFalse(Lead.objects.exists() or Deal.objects.exists())

    def test_existing_legacy_history_and_links_survive_customer_actions(self):
        client = Client.objects.create(business=self.business, full_name="Existing client")
        lead = Lead.objects.create(business=self.business, client=client, message="Original enquiry", status="closed")
        pipeline = Pipeline.objects.create(business=self.business, name="History", slug="history")
        stage = PipelineStage.objects.create(business=self.business, pipeline=pipeline, name="Existing")
        deal = Deal.objects.create(business=self.business, client=client, lead=lead,
            pipeline=pipeline, stage=stage, title="Original deal", amount=123)
        self.conversation.client = client
        self.conversation.lead = lead
        self.conversation.deal = deal
        self.conversation.save()
        before_lead = Lead.objects.values().get(pk=lead.pk)
        before_deal = Deal.objects.values().get(pk=deal.pk)
        result = self.run_pipeline()
        self.assertEqual(result.status, "proposed_actions")
        self.conversation.refresh_from_db()
        self.assertEqual((self.conversation.client_id, self.conversation.lead_id, self.conversation.deal_id),
                         (client.pk, lead.pk, deal.pk))
        self.assertEqual(Lead.objects.values().get(pk=lead.pk), before_lead)
        self.assertEqual(Deal.objects.values().get(pk=deal.pk), before_deal)
        self.assertEqual((Lead.objects.count(), Deal.objects.count()), (1, 1))
        self.assertEqual(Task.objects.count(), 1)

    def test_disabled_client_capability_cannot_create_client(self):
        self.profile.allowed_tools_json = {'tools': ['create_task']}
        self.profile.save()
        self.assertEqual(self.run_pipeline().status, 'needs_review')
        self.assertFalse(Client.objects.exists() or Task.objects.exists())

    def test_reply_only_does_not_require_or_create_client(self):
        self.profile.allowed_tools_json = {'tools': []}
        self.profile.save()
        self.bot.settings_json['auto_crm_pipeline']['auto_send_reply'] = True
        self.bot.save()
        with patch('apps.conversations.auto_pipeline.suggest_bot_reply', return_value=(SimpleNamespace(output_text='Available services'), None, [], [])), \
             patch('apps.bots.outbound_delivery.send_message', return_value={'ok': True}):
            result = self.run_pipeline()
        self.assertEqual(result.reply_message.text, 'Available services')
        self.assertFalse(Client.objects.exists() or Task.objects.exists())

    def test_modern_settings_ignore_legacy_thresholds_and_channel_overrides(self):
        self.bot.settings_json['auto_crm_pipeline'].update(min_lead_confidence=.99, min_deal_confidence=1)
        self.bot.save()
        self.channel.config_json = {'auto_crm_pipeline': {'mode': 'off', 'enabled': False, 'auto_send_reply': True, 'max_auto_reply_chars': 1500}}
        self.channel.save()
        config = resolve_auto_pipeline_config(conversation=self.conversation, channel=self.channel)
        self.assertTrue(config.enabled)
        self.assertFalse(config.auto_send_reply)
        self.assertEqual(config.max_auto_reply_chars, 900)
        self.assertEqual(self.run_pipeline().status, 'proposed_actions')

    def test_configuration_strips_legacy_controls_and_preserves_other_settings(self):
        api = APIClient(); api.force_authenticate(self.business.owner)
        settings = {**self.bot.settings_json, 'memory_enabled': False}
        settings['auto_crm_pipeline'].update(require_review_on_fallback=False, min_lead_confidence=.1,
                                             confirmation_mode='draft_deal')
        response = api.put(f'/api/bots/{self.bot.pk}/configuration/', {'bot': {'settings_json': settings},
            'profile': {'id': self.profile.pk, 'allowed_tools_json': self.profile.allowed_tools_json}}, format='json')
        self.assertEqual(response.status_code, 200, response.data)
        self.bot.refresh_from_db(); self.profile.refresh_from_db()
        self.assertEqual(self.profile.allowed_tools_json['tools'], ['create_client', 'create_task'])
        self.assertFalse(self.bot.settings_json['memory_enabled'])
        for key in ('min_lead_confidence', 'min_deal_confidence', 'require_review_on_fallback', 'confirmation_mode'):
            self.assertNotIn(key, self.bot.settings_json['auto_crm_pipeline'])

    def test_direct_settings_endpoint_cannot_grant_new_automatic_action(self):
        self.bot.settings_json['auto_crm_pipeline'].update(task_creation_policy='staff_confirmation', appointment_creation_policy='automatic')
        self.bot.save()
        settings = {**self.bot.settings_json, 'auto_crm_pipeline': {
            **self.bot.settings_json['auto_crm_pipeline'], 'task_creation_policy': 'automatic'}}
        api = APIClient(); api.force_authenticate(self.business.owner)
        response = api.patch(f'/api/bots/{self.bot.pk}/', {'settings_json': settings}, format='json')
        self.assertEqual(response.status_code, 400, response.data)

    def test_invalid_settings_return_validation_error_without_partial_save(self):
        api = APIClient()
        api.force_authenticate(self.business.owner)
        before = self.bot.settings_json
        for settings in (None, [], "invalid", {"auto_crm_pipeline": "invalid"}):
            with self.subTest(settings=settings):
                response = api.put(f'/api/bots/{self.bot.pk}/configuration/',
                    {'bot': {'settings_json': settings}, 'profile': {'id': self.profile.pk, 'name': 'Changed'}}, format='json')
                self.assertEqual(response.status_code, 400, response.data)
                self.bot.refresh_from_db()
                self.profile.refresh_from_db()
                self.assertEqual(self.bot.settings_json, before)
                self.assertNotEqual(self.profile.name, 'Changed')

    def test_review_marker_from_real_result_cannot_suppress_handoff(self):
        self.bot.settings_json['auto_crm_pipeline'].update(mode='lead_task', require_review_on_fallback=False)
        self.bot.save()
        response = SimpleNamespace(is_mock=False, provider='test', output_text=json.dumps({
            'intent': 'price_question', 'request_kind': 'business', 'confidence': .99, 'summary': 'Owner rule matched',
            'requires_human_review': True, 'is_fallback': True, 'reason': 'Fallback qualification used.',
        }))
        with patch('apps.conversations.ai_qualification.run_ai_request', return_value=(response, None)):
            result = maybe_run_auto_pipeline(conversation=self.conversation, message=self.message)
        self.assertEqual(result.status, 'needs_review')
        self.conversation.refresh_from_db()
        self.assertTrue(self.conversation.handoff_required)
        self.assertFalse(Client.objects.exists() or Task.objects.exists() or Lead.objects.exists() or Deal.objects.exists())


class CustomerActionsBookingTests(booking_fixtures.AutomaticBookingTests):
    def setUp(self):
        super().setUp()
        self.bot.settings_json['auto_crm_pipeline'].update(mode='customer_actions',
            task_creation_policy='staff_confirmation', appointment_creation_policy='automatic')
        self.bot.save()
        self.profile.allowed_tools_json = {'tools': ['create_client', 'create_appointment']}
        self.profile.save()
        store_offered_slots(conversation=self.conversation, scheduling_context={'next_available_slots': [self.slot]},
            runtime_fingerprint=agent_runtime_fingerprint(self.conversation), offer_message_id=self.offer.pk)

    def test_staff_booking_is_not_enabled_by_automatic_task_policy(self):
        self.bot.settings_json['auto_crm_pipeline'].update(task_creation_policy='automatic', appointment_creation_policy='staff_confirmation')
        self.bot.save()
        result = self.book()
        self.assertEqual(result.status, 'requires_staff')

    def test_revoking_all_tools_still_hands_off_an_offered_slot_selection(self):
        self.profile.allowed_tools_json = {'tools': []}
        self.profile.save()
        self._assert_pipeline_review_handoff()
