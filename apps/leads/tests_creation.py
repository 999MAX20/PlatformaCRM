from unittest.mock import patch

from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.activities.models import ActivityEvent
from apps.businesses.models import Business, BusinessMember, BusinessRole, RolePermission
from apps.clients.models import Client
from apps.core.models import AuditLog
from apps.leads.models import Lead
from apps.notifications.models import Notification


class LeadCreationTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.owner = User.objects.create_user(username="initial-lead-owner", email="initial-lead@example.test")
        cls.business = Business.objects.create(owner=cls.owner, name="Initial leads", slug="initial-leads")
        cls.customer = Client.objects.create(business=cls.business, full_name="Customer")
        cls.other = Business.objects.create(owner=cls.owner, name="Other", slug="initial-leads-other")
        cls.other_customer = Client.objects.create(business=cls.other, full_name="Other customer")
        cls.staff = User.objects.create_user(username="initial-lead-staff", email="initial-lead-staff@example.test")
        cls.role = BusinessRole.objects.create(business=cls.business, name="Read only")
        RolePermission.objects.create(business_role=cls.role, resource="leads", action="view", scope="business")
        RolePermission.objects.create(business_role=cls.role, resource="leads", action="create", is_allowed=False)
        BusinessMember.objects.create(business=cls.business, user=cls.staff, role="operator", business_role=cls.role)

    def setUp(self):
        self.api = APIClient()
        self.api.force_authenticate(self.owner)

    def create(self, **values):
        return self.api.post('/api/leads/', {
            'business': self.business.pk, 'client': self.customer.pk, 'message': 'Initial enquiry', **values,
        }, format='json')

    def test_lost_requires_nonblank_reason_and_persists_nothing(self):
        for reason in (None, '', '   '):
            with self.subTest(reason=reason):
                response = self.create(status='lost', **({'lost_reason': reason} if reason is not None else {}))
                self.assertEqual(response.status_code, 400, response.data)
        self.assertFalse(Lead.objects.exists())
        self.assertFalse(ActivityEvent.objects.exists())
        self.assertFalse(AuditLog.objects.exists())

    def test_lost_initial_state_has_server_metadata_and_creation_history(self):
        before = timezone.now()
        response = self.create(status='lost', lost_reason='  Chose another service  ')
        self.assertEqual(response.status_code, 201, response.data)
        lead = Lead.objects.get()
        self.assertEqual(lead.lost_reason, 'Chose another service')
        self.assertIsNotNone(lead.lost_at)
        self.assertGreaterEqual(lead.lost_at, before)
        self.assertEqual(lead.lost_by_id, self.owner.pk)
        self.assertEqual(lead.previous_status, '')
        event = ActivityEvent.objects.get(event_type='lead_created')
        self.assertEqual(event.metadata['initial_status'], 'lost')
        self.assertEqual(event.metadata['lost_reason'], lead.lost_reason)
        self.assertEqual(event.actor_id, self.owner.pk)
        self.assertEqual(AuditLog.objects.get(entity_type='Lead').metadata['initial_status'], 'lost')
        self.assertFalse(Notification.objects.exists())

    def test_new_and_closed_creation_preserve_normal_flow_and_clear_loss_metadata(self):
        for status in ('new', 'closed'):
            response = self.create(status=status)
            self.assertEqual(response.status_code, 201, response.data)
            lead = Lead.objects.get(pk=response.data['id'])
            self.assertEqual(lead.status, status)
            self.assertEqual(lead.lost_reason, '')
            self.assertIsNone(lead.lost_at)
            self.assertIsNone(lead.lost_by_id)
            self.assertEqual(lead.responsible_user_id, self.owner.pk)
            self.assertEqual(ActivityEvent.objects.get(entity_type='Lead', entity_id=str(lead.pk)).metadata['initial_status'], status)

    def test_nonlost_reason_is_rejected(self):
        response = self.create(status='new', lost_reason='Conflicting reason')
        self.assertEqual(response.status_code, 400, response.data)
        self.assertFalse(Lead.objects.exists())

    def test_server_metadata_cannot_be_forged_on_creation(self):
        response = self.create(status='lost', lost_reason='Valid', lost_at='2001-01-01T00:00:00Z', lost_by=self.staff.pk, previous_status='closed')
        self.assertEqual(response.status_code, 400, response.data)
        self.assertFalse(Lead.objects.exists())

    def test_denied_role_and_cross_business_client_cannot_create(self):
        self.assertEqual(self.create(client=self.other_customer.pk).status_code, 400)
        self.api.force_authenticate(self.staff)
        self.assertEqual(self.create().status_code, 403)
        self.assertEqual(self.create(business=self.other.pk, client=self.other_customer.pk).status_code, 403)
        self.assertFalse(Lead.objects.exists())

    def test_creation_audit_failure_rolls_back_entity_and_activity(self):
        with patch('apps.leads.creation.write_audit_log', side_effect=RuntimeError('audit unavailable')):
            self.assertEqual(self.create().status_code, 500)
        self.assertFalse(Lead.objects.exists())
        self.assertFalse(ActivityEvent.objects.exists())

    def test_lead_created_automation_failure_rolls_back_initial_state(self):
        with patch('apps.leads.views.run_automations_for_event', side_effect=RuntimeError('automation unavailable')):
            self.assertEqual(self.create(status='lost', lost_reason='Valid').status_code, 500)
        self.assertFalse(Lead.objects.exists())
        self.assertFalse(ActivityEvent.objects.exists())
        self.assertFalse(AuditLog.objects.exists())
