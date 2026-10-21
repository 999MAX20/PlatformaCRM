import tempfile
from types import SimpleNamespace
from unittest.mock import patch

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.activities.models import ActivityEvent
from apps.businesses.access import ensure_default_roles
from apps.businesses.capabilities import apply_business_type_defaults
from apps.businesses.models import Business, BusinessMember, BusinessRole
from apps.clients.models import Client
from apps.core.models import AuditLog, ImportJob
from apps.integrations.models import BusinessEvent, ConnectorSyncRun
from apps.leads.models import Lead
from apps.crm.models import Deal, DealStageHistory
from apps.crm.services import ensure_default_pipeline


class LeadImportLifecycleTests(TestCase):
    def setUp(self):
        media = tempfile.TemporaryDirectory()
        self.addCleanup(media.cleanup)
        override = override_settings(MEDIA_ROOT=media.name)
        override.enable()
        self.addCleanup(override.disable)
        scanner = patch('apps.core.antivirus.scan_stream', return_value=SimpleNamespace(clean=True))
        scanner.start()
        self.addCleanup(scanner.stop)
        self.owner = User.objects.create_user(username='import-state-owner', email='import-state@example.test')
        self.business = Business.objects.create(owner=self.owner, name='Import states', slug='import-states')
        ensure_default_roles(self.business)
        BusinessMember.objects.create(business=self.business, user=self.owner, role='owner',
            business_role=BusinessRole.objects.get(business=self.business, preset_key='owner'))
        apply_business_type_defaults(self.business, configured_by=self.owner)
        self.api = APIClient()
        self.api.force_authenticate(self.owner)

    def upload(self, rows):
        file = SimpleUploadedFile('leads.csv', ('full_name,phone,message,status,lost_reason\n' + rows).encode(), content_type='text/csv')
        response = self.api.post('/api/import-jobs/', {'business': self.business.pk, 'entity_type': 'leads', 'source_file': file}, format='multipart')
        self.assertEqual(response.status_code, 201, response.data)
        return response

    def test_preview_rejects_lost_without_reason_and_unknown_status(self):
        response = self.upload('Lost,+77010000001,Enquiry,lost,\nUnknown,+77010000002,Enquiry,not-a-status,\n')
        self.assertFalse(response.data['preview_json']['import_summary']['ready'])
        self.assertEqual({e['field'] for e in response.data['errors_json']['rows']}, {'lost_reason', 'status'})
        confirm = self.api.post(f"/api/import-jobs/{response.data['id']}/confirm/")
        self.assertEqual(confirm.status_code, 400, confirm.data)
        self.assertFalse(Lead.objects.exists())
        self.assertFalse(Client.objects.exists())
        self.assertFalse(BusinessEvent.objects.exists())
        self.assertFalse(ConnectorSyncRun.objects.exists())

    def test_valid_lost_and_default_new_import_have_history_and_single_events(self):
        response = self.upload('Lost,+77010000001,Lost enquiry,lost,Chose another service\nNew,+77010000002,New enquiry,,\n')
        self.assertTrue(response.data['preview_json']['import_summary']['ready'])
        confirm = self.api.post(f"/api/import-jobs/{response.data['id']}/confirm/")
        self.assertEqual(confirm.status_code, 200, confirm.data)
        lost = Lead.objects.get(status='lost')
        self.assertEqual(lost.lost_reason, 'Chose another service')
        self.assertIsNotNone(lost.lost_at)
        self.assertEqual(lost.lost_by_id, self.owner.pk)
        self.assertEqual(Lead.objects.filter(status='new', lost_at=None, lost_reason='').count(), 1)
        self.assertEqual(ActivityEvent.objects.filter(event_type='lead_created').count(), 2)
        self.assertEqual(BusinessEvent.objects.filter(event_type='lead.imported').count(), 2)
        self.assertEqual(AuditLog.objects.filter(entity_type='Lead').count(), 2)
        self.assertEqual(self.api.post(f"/api/import-jobs/{response.data['id']}/confirm/").status_code, 400)
        self.assertEqual(Lead.objects.count(), 2)

    def test_confirm_revalidates_file_instead_of_trusting_preview(self):
        response = self.upload('New,+77010000001,Enquiry,new,\n')
        job = ImportJob.objects.get(pk=response.data['id'])
        with open(job.source_file.path, 'w', encoding='utf-8') as source:
            source.write('full_name,phone,message,status,lost_reason\nChanged,+77010000001,Enquiry,lost,\n')
        confirm = self.api.post(f'/api/import-jobs/{job.pk}/confirm/')
        self.assertEqual(confirm.status_code, 400, confirm.data)
        self.assertFalse(Lead.objects.exists())
        self.assertFalse(Client.objects.exists())

    def test_later_invalid_row_rejects_whole_file_without_partial_creation(self):
        response = self.upload('Valid,+77010000001,First,new,\nInvalid,+77010000002,Second,lost,\n')
        confirm = self.api.post(f"/api/import-jobs/{response.data['id']}/confirm/")
        self.assertEqual(confirm.status_code, 400)
        self.assertFalse(Client.objects.exists())
        self.assertFalse(Lead.objects.exists())
        self.assertFalse(ActivityEvent.objects.filter(entity_type='Lead').exists())

    def test_event_failure_rolls_back_then_retry_creates_exactly_one_result(self):
        response = self.upload('Lost,+77010000001,Enquiry,lost,No budget\n')
        url = f"/api/import-jobs/{response.data['id']}/confirm/"
        with patch('apps.core.import_export.record_import_event', side_effect=RuntimeError('event unavailable')):
            self.assertEqual(self.api.post(url).status_code, 500)
        self.assertFalse(Client.objects.exists())
        self.assertFalse(Lead.objects.exists())
        self.assertFalse(ActivityEvent.objects.filter(entity_type='Lead').exists())
        self.assertFalse(AuditLog.objects.filter(entity_type='Lead').exists())
        self.assertFalse(BusinessEvent.objects.exists())
        self.assertFalse(ConnectorSyncRun.objects.exists())
        job = ImportJob.objects.get(pk=response.data['id'])
        self.assertEqual(job.status, 'previewed')
        self.assertEqual(self.api.post(url).status_code, 200)
        self.assertEqual(Lead.objects.count(), 1)
        self.assertEqual(ActivityEvent.objects.filter(event_type='lead_created').count(), 1)
        self.assertEqual(BusinessEvent.objects.filter(event_type='lead.imported').count(), 1)

    def test_same_rows_reimport_does_not_duplicate_initial_history(self):
        for _ in range(2):
            response = self.upload('Lost,+77010000001,Enquiry,lost,No budget\n')
            self.assertEqual(self.api.post(f"/api/import-jobs/{response.data['id']}/confirm/").status_code, 200)
        self.assertEqual(Lead.objects.count(), 1)
        self.assertEqual(ActivityEvent.objects.filter(event_type='lead_created').count(), 1)
        self.assertEqual(BusinessEvent.objects.filter(event_type='lead.imported').count(), 1)

    def test_permission_revocation_before_confirm_leaves_no_rows(self):
        from apps.businesses.models import RolePermission
        actor = User.objects.create_user(username='import-state-staff', email='import-state-staff@example.test', role='staff')
        role = BusinessRole.objects.create(business=self.business, name='Importer')
        permission = RolePermission.objects.create(business_role=role, resource='leads', action='create', scope='business')
        RolePermission.objects.create(business_role=role, resource='clients', action='view', scope='business')
        BusinessMember.objects.create(business=self.business, user=actor, role='staff', business_role=role)
        self.api.force_authenticate(actor)
        response = self.upload('Lost,+77010000001,Enquiry,lost,No budget\n')
        permission.is_allowed = False
        permission.save()
        self.assertEqual(self.api.post(f"/api/import-jobs/{response.data['id']}/confirm/").status_code, 403)
        self.assertFalse(Lead.objects.exists())
        self.assertFalse(Client.objects.exists())

    def test_deal_import_requires_active_open_stage_and_recovers_after_configuration_fix(self):
        pipeline = ensure_default_pipeline(self.business)
        pipeline.stages.filter(is_won=False, is_lost=False).update(is_active=False)
        file = SimpleUploadedFile('deals.csv', b'title,client_name,amount\nOpportunity,Customer,100.00\n', content_type='text/csv')
        response = self.api.post('/api/import-jobs/', {'business': self.business.pk, 'entity_type': 'deals', 'source_file': file}, format='multipart')
        self.assertEqual(response.status_code, 201, response.data)
        url = f"/api/import-jobs/{response.data['id']}/confirm/"
        self.assertEqual(self.api.post(url).status_code, 400)
        self.assertFalse(Client.objects.exists())
        self.assertFalse(Deal.objects.exists())
        self.assertFalse(DealStageHistory.objects.exists())
        self.assertFalse(BusinessEvent.objects.exists())
        pipeline.stages.filter(template_key='new').update(is_active=True)
        self.assertEqual(self.api.post(url).status_code, 200)
        deal = Deal.objects.get()
        self.assertEqual(deal.status, 'open')
        self.assertFalse(deal.stage.is_won or deal.stage.is_lost)
        self.assertEqual(DealStageHistory.objects.get(deal=deal).to_status, 'open')
        self.assertEqual(ActivityEvent.objects.filter(event_type='deal_created').count(), 1)
