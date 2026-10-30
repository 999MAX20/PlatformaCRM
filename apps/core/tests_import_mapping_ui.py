import tempfile
from types import SimpleNamespace
from unittest.mock import patch

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.businesses.models import Business, BusinessMember, BusinessRole, RolePermission
from apps.core.import_export import FIELDS_BY_ENTITY
from apps.core.models import ImportJob


class ImportMappingUITests(TestCase):
    def setUp(self):
        media = tempfile.TemporaryDirectory()
        self.addCleanup(media.cleanup)
        settings = override_settings(MEDIA_ROOT=media.name)
        settings.enable()
        self.addCleanup(settings.disable)
        scanner = patch('apps.core.antivirus.scan_stream', return_value=SimpleNamespace(clean=True))
        scanner.start()
        self.addCleanup(scanner.stop)
        self.owner = User.objects.create_user(username='mapping-owner', email='mapping-owner@example.test', role='business_owner')
        self.business = Business.objects.create(owner=self.owner, name='Import', slug='mapping-owner')
        self.api = APIClient()
        self.api.force_authenticate(self.owner)

    def upload(self):
        content = 'amount,corrected,external_id\n' + ''.join(f'invalid,25,sale-{n}\n' for n in range(61))
        response = self.api.post('/api/import-jobs/', {
            'business': self.business.pk, 'entity_type': 'sales',
            'source_file': SimpleUploadedFile('sales.csv', content.encode(), content_type='text/csv'),
        }, format='multipart')
        self.assertEqual(response.status_code, 201, response.data)
        return response.data

    def test_full_errors_persist_but_regular_response_stays_bounded(self):
        data = self.upload()
        job = ImportJob.objects.get(pk=data['id'])
        self.assertEqual(len(job.errors_json['rows']), 61)
        self.assertEqual(len(data['errors_json']['rows']), 50)
        self.assertEqual(data['errors_json']['count'], 61)
        self.assertEqual(data['summary_json']['errors'], 61)
        rows = []
        for page in range(1, 5):
            response = self.api.get(f'/api/import-jobs/{job.pk}/errors/', {'page': page, 'page_size': 20})
            self.assertEqual(response.status_code, 200, response.data)
            self.assertEqual(response.data['count'], 61)
            rows.extend(response.data['results'])
        self.assertEqual([row['row'] for row in rows], list(range(1, 62)))
        self.assertTrue(all(row['field'] == 'amount' for row in rows))
        self.assertEqual(self.api.get(f'/api/import-jobs/{job.pk}/errors/?page=5').status_code, 404)

    def test_remapping_rechecks_and_clears_errors_before_confirmation(self):
        data = self.upload()
        url = f"/api/import-jobs/{data['id']}"
        self.assertEqual(self.api.post(url + '/confirm/').status_code, 400)
        mapping = {'amount': 'corrected', 'external_id': 'external_id'}
        response = self.api.post(url + '/preview/', {'mapping': mapping}, format='json')
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data['errors_json'], {'rows': [], 'count': 0})
        self.assertEqual(response.data['mapping_json'], mapping)
        self.assertEqual(self.api.get(url + '/errors/').data['results'], [])
        response = self.api.post(url + '/confirm/')
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data['imported_count'], 61)
        self.assertEqual(self.api.post(url + '/confirm/').status_code, 400)

    def test_mapping_metadata_is_server_owned_for_each_entity(self):
        from apps.core.serializers import ImportJobSerializer
        for entity, fields in FIELDS_BY_ENTITY.items():
            job = ImportJob(business=self.business, actor=self.owner, entity_type=entity)
            self.assertEqual(ImportJobSerializer(job).data['mapping_fields'], fields)
        response = self.api.post('/api/import-jobs/', {'mapping_fields': ['fake']}, format='json')
        self.assertEqual(response.status_code, 400)
        self.assertIn('mapping_fields', response.data)

    def test_errors_deny_other_actor_even_in_same_business_and_other_tenant(self):
        data = self.upload()
        other = User.objects.create_user(username='mapping-other', email='mapping-other@example.test', role='business_owner')
        Business.objects.create(owner=other, name='Other', slug='mapping-other')
        self.api.force_authenticate(other)
        url = f"/api/import-jobs/{data['id']}/errors/"
        self.assertEqual(self.api.get(url).status_code, 404)
        BusinessMember.objects.create(business=self.business, user=other, role='manager')
        self.assertEqual(self.api.get(url).status_code, 404)

    def test_error_page_size_is_capped(self):
        data = self.upload()
        job = ImportJob.objects.get(pk=data['id'])
        job.errors_json = {'rows': [{'row': n, 'field': 'amount', 'message': 'Invalid'} for n in range(205)]}
        job.save(update_fields=['errors_json'])
        response = self.api.get(f'/api/import-jobs/{job.pk}/errors/?page_size=999')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 205)
        self.assertEqual(len(response.data['results']), 100)

    def test_current_read_permission_is_required_even_for_job_author(self):
        data = self.upload()
        actor = User.objects.create_user(username='mapping-reader', email='mapping-reader@example.test', role='business_operator')
        role = BusinessRole.objects.create(business=self.business, name='Import reader')
        BusinessMember.objects.create(business=self.business, user=actor, role='operator', business_role=role)
        permission = RolePermission.objects.create(business_role=role, resource='clients', action='view', scope='business')
        ImportJob.objects.filter(pk=data['id']).update(actor=actor)
        self.api.force_authenticate(actor)
        url = f"/api/import-jobs/{data['id']}/errors/"
        self.assertEqual(self.api.get(url).status_code, 200)
        permission.is_allowed = False
        permission.save(update_fields=['is_allowed'])
        response = self.api.get(url)
        self.assertEqual(response.status_code, 404, response.data)
