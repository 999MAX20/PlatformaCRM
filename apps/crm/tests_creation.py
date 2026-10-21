from unittest.mock import patch

from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework.exceptions import ValidationError

from apps.accounts.models import User
from apps.activities.models import ActivityEvent
from apps.businesses.models import Business, BusinessMember, BusinessRole, RolePermission
from apps.clients.models import Client
from apps.core.models import AuditLog
from apps.crm.models import Deal, DealStageHistory
from apps.crm.services import ensure_default_pipeline


class DealCreationTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.owner = User.objects.create_user(username='deal-initial-owner', email='deal-initial@example.test')
        cls.business = Business.objects.create(owner=cls.owner, name='Initial deals', slug='initial-deals')
        cls.customer = Client.objects.create(business=cls.business, full_name='Customer')
        cls.pipeline = ensure_default_pipeline(cls.business)
        cls.open_stage = cls.pipeline.stages.get(template_key='new')
        cls.won_stage = cls.pipeline.stages.get(is_won=True)
        cls.lost_stage = cls.pipeline.stages.get(is_lost=True)
        cls.staff = User.objects.create_user(username='deal-initial-staff', email='deal-initial-staff@example.test')
        cls.role = BusinessRole.objects.create(business=cls.business, name='No creation')
        RolePermission.objects.create(business_role=cls.role, resource='deals', action='create', is_allowed=False)
        BusinessMember.objects.create(business=cls.business, user=cls.staff, role='manager', business_role=cls.role)

    def setUp(self):
        self.api = APIClient()
        self.api.force_authenticate(self.owner)

    def create(self, **values):
        return self.api.post('/api/deals/', {'business': self.business.pk, 'client': self.customer.pk,
            'pipeline': self.pipeline.pk, 'stage': self.open_stage.pk, 'title': 'Initial deal', 'amount': '100.00', **values}, format='json')

    def test_initial_status_must_agree_with_stage(self):
        for stage, status in ((self.open_stage, 'lost'), (self.lost_stage, 'open'), (self.won_stage, 'lost')):
            response = self.create(stage=stage.pk, status=status, lost_reason='Valid reason')
            self.assertEqual(response.status_code, 400, response.data)
        self.assertFalse(Deal.objects.exists())

    def test_terminal_initial_state_has_server_dates_and_history(self):
        before = timezone.now()
        for stage in (self.won_stage, self.lost_stage):
            values = {'stage': stage.pk}
            if stage.is_lost:
                values['lost_reason'] = '  No budget  '
            response = self.create(**values)
            self.assertEqual(response.status_code, 201, response.data)
            deal = Deal.objects.get(pk=response.data['id'])
            status = 'won' if stage.is_won else 'lost'
            self.assertEqual(deal.status, status)
            self.assertGreaterEqual(deal.won_at if stage.is_won else deal.lost_at, before)
            self.assertEqual(deal.probability, stage.probability)
            self.assertIsNotNone(deal.stage_entered_at)
            self.assertEqual(deal.previous_status, '')
            self.assertIsNone(deal.previous_stage_id)
            if stage.is_lost:
                self.assertEqual(deal.lost_by_id, self.owner.pk)
                self.assertEqual(deal.lost_reason, 'No budget')
            history = DealStageHistory.objects.get(deal=deal)
            self.assertIsNone(history.from_stage_id)
            self.assertEqual(history.from_status, '')
            self.assertEqual(history.to_status, status)
            self.assertEqual(ActivityEvent.objects.get(entity_type='Deal', entity_id=str(deal.pk)).metadata['initial_status'], status)

    def test_lost_stage_requires_reason_even_when_status_omitted(self):
        for reason in ('', '   '):
            response = self.create(stage=self.lost_stage.pk, lost_reason=reason)
            self.assertEqual(response.status_code, 400, response.data)
        self.assertFalse(Deal.objects.exists())

    def test_normal_open_creation_and_required_stage_fields(self):
        response = self.create()
        self.assertEqual(response.status_code, 201, response.data)
        deal = Deal.objects.get()
        self.assertEqual(deal.status, 'open')
        self.assertIsNone(deal.lost_at)
        self.assertIsNone(deal.won_at)
        self.open_stage.required_fields_json = {'fields': ['owner']}
        self.open_stage.save()
        self.assertEqual(self.create().status_code, 400)
        self.assertEqual(Deal.objects.count(), 1)

    def test_client_cannot_supply_initial_server_metadata(self):
        for field, value in [('won_at', '2001-01-01T00:00:00Z'), ('stage_entered_at', '2001-01-01T00:00:00Z'), ('previous_status', 'won'), ('probability', 100)]:
            response = self.create(**{field: value})
            self.assertEqual(response.status_code, 400, response.data)
        self.assertFalse(Deal.objects.exists())

    def test_permission_and_cross_business_stage_denied(self):
        other = Business.objects.create(owner=self.owner, name='Other', slug='deal-initial-other')
        other_stage = ensure_default_pipeline(other).stages.first()
        self.assertEqual(self.create(stage=other_stage.pk).status_code, 400)
        self.api.force_authenticate(self.staff)
        self.assertEqual(self.create().status_code, 403)
        self.assertFalse(Deal.objects.exists())

    def test_audit_failure_rolls_back_deal_history_and_activity(self):
        with patch('apps.crm.creation.write_audit_log', side_effect=RuntimeError('audit unavailable')):
            self.assertEqual(self.create(stage=self.won_stage.pk).status_code, 500)
        self.assertFalse(Deal.objects.exists())
        self.assertFalse(DealStageHistory.objects.exists())
        self.assertFalse(ActivityEvent.objects.exists())
        self.assertFalse(AuditLog.objects.exists())

    def test_inactive_or_role_restricted_initial_stage_is_rejected(self):
        self.open_stage.is_active = False
        self.open_stage.save()
        self.assertEqual(self.create().status_code, 400)
        self.open_stage.is_active = True
        self.open_stage.allowed_roles_json = {'roles': ['platform_admin']}
        self.open_stage.save()
        self.assertEqual(self.create().status_code, 400)
        self.assertFalse(Deal.objects.exists())

    def test_inbox_default_stage_cannot_be_terminal_or_inactive(self):
        from apps.conversations.pipeline import default_pipeline_and_stage
        self.won_stage.order = 0
        self.won_stage.save()
        self.open_stage.is_active = False
        self.open_stage.save()
        _, stage = default_pipeline_and_stage(self.business)
        self.assertFalse(stage.is_won or stage.is_lost)
        self.assertTrue(stage.is_active)
        self.pipeline.stages.filter(is_won=False, is_lost=False).update(is_active=False)
        with self.assertRaises(ValidationError):
            default_pipeline_and_stage(self.business)

    def test_inbox_creation_without_open_stage_rolls_back_and_can_retry(self):
        from apps.bots.models import Bot, BotConversation
        from apps.leads.models import Lead
        bot = Bot.objects.create(business=self.business, name='Initial pipeline')
        conversation = BotConversation.objects.create(business=self.business, bot=bot,
            channel='website', external_user_id='initial-pipeline', client=self.customer)
        self.pipeline.stages.filter(is_won=False, is_lost=False).update(is_active=False)
        url = f'/api/inbox/conversations/{conversation.pk}/create-deal/'
        response = self.api.post(url, {'title': 'Inbox opportunity', 'amount': '100.00'}, format='json')
        self.assertEqual(response.status_code, 400, response.data)
        conversation.refresh_from_db()
        self.assertIsNone(conversation.lead_id)
        self.assertIsNone(conversation.deal_id)
        self.assertFalse(Lead.objects.exists())
        self.assertFalse(Deal.objects.exists())
        self.assertFalse(ActivityEvent.objects.exists())
        self.assertFalse(AuditLog.objects.exists())
        self.open_stage.is_active = True
        self.open_stage.save()
        response = self.api.post(url, {'title': 'Inbox opportunity', 'amount': '100.00'}, format='json')
        self.assertEqual(response.status_code, 201, response.data)
        deal = Deal.objects.get()
        self.assertEqual(deal.stage_id, self.open_stage.pk)
        self.assertEqual(deal.status, 'open')
