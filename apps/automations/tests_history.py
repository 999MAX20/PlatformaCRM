"""AUD07: complete, filtered and permission-scoped automation history."""
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.automations.models import AutomationRule, AutomationRun
from apps.businesses.models import Business, BusinessMember, BusinessRole, RolePermission


class AutomationHistoryTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.owner = User.objects.create_user(username='history-owner', email='history@example.invalid')
        cls.business = Business.objects.create(owner=cls.owner, name='History', slug='history')
        cls.other = Business.objects.create(owner=cls.owner, name='Other', slug='history-other')
        cls.foreign_owner = User.objects.create_user(username='foreign-history', email='foreign@example.invalid')
        cls.foreign = Business.objects.create(owner=cls.foreign_owner, name='Foreign', slug='history-foreign')
        cls.rules = AutomationRule.objects.bulk_create([
            AutomationRule(business=cls.business, name=f'Rule {i:03}', trigger_type='lead_created', is_active=i < 101)
            for i in range(105)
        ])
        cls.runs = AutomationRun.objects.bulk_create([
            AutomationRun(business=cls.business, rule=cls.rules[0], entity_type='lead', entity_id=str(i),
                          trigger_type='lead_created' if i < 100 else 'task_overdue',
                          status='success' if i < 100 else 'failed' if i < 105 else 'cancelled')
            for i in range(107)
        ])
        # Equal timestamps require a stable id tie-breaker across pages.
        AutomationRun.objects.filter(business=cls.business).update(created_at=timezone.now())
        for business in [cls.other, cls.foreign]:
            rule = AutomationRule.objects.create(business=business, name='Other rule', trigger_type='lead_created', is_active=True)
            AutomationRun.objects.create(business=business, rule=rule, trigger_type='lead_created', status='failed')

    def setUp(self):
        self.api = APIClient()
        self.api.force_authenticate(self.owner)

    def page(self, **params):
        response = self.api.get('/api/automation-runs/', {'business': self.business.pk, 'page_size': 10, **params})
        self.assertEqual(response.status_code, 200, response.data)
        self.assertIn('summary', response.data)
        return response.data

    def test_complete_metrics_and_every_history_page(self):
        first = self.page()
        self.assertEqual(first['count'], 107)
        self.assertEqual(first['summary'], {'total': 107, 'failed': 7, 'retryable': 7})
        ids = []
        for page in range(1, 12):
            data = self.page(page=page)
            self.assertEqual(data['summary'], first['summary'])
            ids.extend(row['id'] for row in data['results'])
        self.assertEqual(ids, sorted([run.pk for run in self.runs], reverse=True))
        oldest = self.api.get(f'/api/automation-runs/{self.runs[0].pk}/')
        self.assertEqual(oldest.status_code, 200)
        self.assertEqual(oldest.data['entity_id'], '0')

    def test_filters_apply_to_counts_before_pagination(self):
        data = self.page(status='failed', trigger_type='task_overdue', page_size=2)
        self.assertEqual(data['summary'], {'total': 5, 'failed': 5, 'retryable': 5})
        self.assertEqual(len(data['results']), 2)
        self.assertTrue(all(row['status'] == 'failed' for row in data['results']))
        empty = self.page(status='success', trigger_type='task_overdue')
        self.assertEqual(empty['results'], [])
        self.assertEqual(empty['summary'], {'total': 0, 'failed': 0, 'retryable': 0})

    def test_invalid_filters_and_missing_page(self):
        for params in [{'business': 'bad'}, {'business': -1}, {'business': 2**80},
                       {'status': 'unknown'}, {'trigger_type': 'unknown'}]:
            with self.subTest(params=params):
                self.assertEqual(self.api.get('/api/automation-runs/', params).status_code, 400)
        self.assertEqual(self.api.get('/api/automation-runs/', {'business': self.business.pk, 'page': 99}).status_code, 404)

    def test_business_filter_does_not_grant_access_or_mix_accessible_businesses(self):
        self.assertEqual(self.page(business=self.other.pk)['count'], 1)
        self.assertEqual(self.page(business=self.foreign.pk)['summary']['total'], 0)
        response = self.api.get('/api/automation-runs/')
        self.assertEqual(response.data['count'], 108)  # Existing cross-accessible contract without a filter.

    def test_current_permission_denial_and_membership_revocation(self):
        actor = User.objects.create_user(username='history-reader', email='reader@example.invalid')
        role = BusinessRole.objects.create(business=self.business, name='History reader')
        permission = RolePermission.objects.create(business_role=role, resource='automations', action='view', scope='business')
        member = BusinessMember.objects.create(business=self.business, user=actor, role='operator', business_role=role)
        self.api.force_authenticate(actor)
        self.assertEqual(self.page()['count'], 107)
        permission.is_allowed = False
        permission.save()
        self.assertEqual(self.page()['summary']['total'], 0)
        self.assertEqual(self.api.get('/api/automation-rules/', {'business': self.business.pk}).data['summary'], {'total': 0, 'active': 0})
        self.assertEqual(self.api.get(f'/api/automation-runs/{self.runs[0].pk}/').status_code, 404)
        permission.is_allowed = True
        permission.save()
        member.is_active = False
        member.save()
        self.assertEqual(self.page()['count'], 0)

    def test_own_scope_and_page_size_limit(self):
        self.assertEqual(len(self.page(page_size=1000)['results']), 100)
        actor = User.objects.create_user(username='history-own', email='own@example.invalid')
        role = BusinessRole.objects.create(business=self.business, name='Own history')
        RolePermission.objects.create(business_role=role, resource='automations', action='view', scope='own')
        BusinessMember.objects.create(business=self.business, user=actor, role='operator', business_role=role)
        self.api.force_authenticate(actor)
        # AutomationRun has no user ownership link: existing OWN scope is empty.
        self.assertEqual(self.page()['summary'], {'total': 0, 'failed': 0, 'retryable': 0})

    def test_rule_metrics_are_complete_and_business_scoped(self):
        response = self.api.get('/api/automation-rules/', {'business': self.business.pk, 'page_size': 10})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data.get('summary'), {'total': 105, 'active': 101})
        self.assertEqual(response.data['count'], 105)
        response = self.api.get('/api/automation-rules/', {'business': self.foreign.pk})
        self.assertEqual(response.data['summary'], {'total': 0, 'active': 0})
        self.assertEqual(self.api.get('/api/automation-rules/', {'business': 'bad'}).status_code, 400)
