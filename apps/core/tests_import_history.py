from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.businesses.models import Business, BusinessMember, BusinessRole, RolePermission
from apps.core.models import ImportJob


class ImportHistoryTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(username='history-owner', email='history-owner@example.test', role='business_owner')
        self.business = Business.objects.create(owner=self.owner, name='History', slug='history')
        self.other_business = Business.objects.create(owner=self.owner, name='Second', slug='history-second')
        self.other = User.objects.create_user(username='history-other', email='history-other@example.test', role='business_owner')
        self.foreign = Business.objects.create(owner=self.other, name='Foreign', slug='history-foreign')
        self.api = APIClient()
        self.api.force_authenticate(self.owner)

    def job(self, entity='leads', **kwargs):
        values = {'business': self.business, 'actor': self.owner, 'entity_type': entity,
                  'original_filename': f'{entity}.csv', 'status': 'imported', 'total_rows': 1, 'imported_count': 1}
        return ImportJob.objects.create(**{**values, **kwargs})

    def test_entity_filter_precedes_pagination_and_all_pages_are_reachable(self):
        expected = [self.job().pk for _ in range(43)]
        for _ in range(24):
            self.job('clients')
        ImportJob.objects.all().update(created_at=timezone.now())
        actual = []
        for page, size in [(1, 20), (2, 20), (3, 3)]:
            response = self.api.get('/api/import-jobs/', {'business': self.business.pk, 'entity_type': 'leads', 'page': page})
            self.assertEqual(response.status_code, 200, response.data)
            self.assertEqual(response.data['count'], 43)
            self.assertEqual(len(response.data['results']), size)
            self.assertTrue(all(row['entity_type'] == 'leads' for row in response.data['results']))
            actual.extend(row['id'] for row in response.data['results'])
        self.assertEqual(actual, list(reversed(expected)))
        detail = self.api.get(f'/api/import-jobs/{expected[0]}/', {'business': self.business.pk, 'entity_type': 'leads'})
        self.assertEqual(detail.status_code, 200)
        self.assertEqual(detail.data['original_filename'], 'leads.csv')

    def test_optional_filters_preserve_unfiltered_contract_and_actor_tenant_scope(self):
        first = self.job()
        second = self.job('clients', business=self.other_business)
        self.job(business=self.foreign, actor=self.other)
        BusinessMember.objects.create(business=self.business, user=self.other, role='manager')
        self.job(actor=self.other)
        response = self.api.get('/api/import-jobs/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual({row['id'] for row in response.data['results']}, {first.pk, second.pk})
        response = self.api.get('/api/import-jobs/', {'business': self.business.pk})
        self.assertEqual([row['id'] for row in response.data['results']], [first.pk])
        self.assertEqual(self.api.get('/api/import-jobs/', {'business': self.foreign.pk}).data['count'], 0)

    def test_invalid_filters_are_client_errors(self):
        for query in [{'entity_type': 'unknown'}, {'entity_type': ''}, {'business': 'wrong'}, {'business': -1}]:
            with self.subTest(query=query):
                response = self.api.get('/api/import-jobs/', query)
                self.assertEqual(response.status_code, 400, response.data)

    def test_detail_respects_requested_context(self):
        job = self.job()
        for query in [{'entity_type': 'clients'}, {'business': self.other_business.pk}]:
            self.assertEqual(self.api.get(f'/api/import-jobs/{job.pk}/', query).status_code, 404)

    def test_page_size_cap_and_empty_results(self):
        ImportJob.objects.bulk_create([ImportJob(business=self.business, actor=self.owner, entity_type='leads') for _ in range(105)])
        response = self.api.get('/api/import-jobs/', {'page_size': 1000})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 105)
        self.assertEqual(len(response.data['results']), 100)
        response = self.api.get('/api/import-jobs/', {'entity_type': 'sales'})
        self.assertEqual(response.data['count'], 0)
        self.assertEqual(response.data['results'], [])
        self.assertEqual(self.api.get('/api/import-jobs/?page=99').status_code, 404)

    def test_current_view_permission_and_membership_are_required(self):
        role = BusinessRole.objects.create(business=self.business, name='History reader')
        member = BusinessMember.objects.create(business=self.business, user=self.other, role='operator', business_role=role)
        permission = RolePermission.objects.create(business_role=role, resource='clients', action='view', scope='business')
        job = self.job(actor=self.other)
        self.api.force_authenticate(self.other)
        params = {'business': self.business.pk, 'entity_type': 'leads'}
        self.assertEqual(self.api.get('/api/import-jobs/', params).data['count'], 1)
        permission.is_allowed = False
        permission.save(update_fields=['is_allowed'])
        self.assertEqual(self.api.get('/api/import-jobs/', params).data['count'], 0)
        self.assertEqual(self.api.get(f'/api/import-jobs/{job.pk}/', params).status_code, 404)
        permission.is_allowed = True
        permission.save(update_fields=['is_allowed'])
        member.is_active = False
        member.save(update_fields=['is_active'])
        self.assertEqual(self.api.get('/api/import-jobs/', params).data['count'], 0)
