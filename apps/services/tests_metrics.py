"""AUD09: full permitted service counts, never a first-page estimate."""
from datetime import timedelta

from django.test import TestCase
from django.db import connection
from django.test.utils import CaptureQueriesContext
from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.businesses.models import Business, BusinessMember, BusinessRole, RolePermission
from apps.clients.models import Client
from apps.scheduling.models import Appointment, Resource
from apps.services.models import Service
from apps.services.selectors import with_appointment_counts


class ServiceMetricsTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.owner = User.objects.create_user(username="metrics-owner", email="metrics-owner@example.invalid")
        cls.business = Business.objects.create(owner=cls.owner, name="Metrics", slug="metrics")
        cls.foreign_owner = User.objects.create_user(username="metrics-foreign", email="metrics-foreign@example.invalid")
        cls.foreign = Business.objects.create(owner=cls.foreign_owner, name="Other", slug="other-metrics")
        cls.crm_client = Client.objects.create(business=cls.business, full_name="Synthetic client")
        cls.services = Service.objects.bulk_create([
            Service(business=cls.business, name=f"Service {i:03}", duration_minutes=30 if i < 100 else 90)
            for i in range(105)
        ])
        cls.inactive = Service.objects.create(business=cls.business, name="Inactive", is_active=False, duration_minutes=200)
        cls.archived = Service.objects.create(business=cls.business, name="Archived", is_archived=True)
        Service.objects.create(business=cls.foreign, name="Foreign", duration_minutes=999)
        now = timezone.now()
        Appointment.objects.bulk_create([
            Appointment(business=cls.business, client=cls.crm_client, service=service,
                        start_at=now-timedelta(days=i), end_at=now-timedelta(days=i)+timedelta(minutes=30))
            for i, service in enumerate(cls.services)
        ])
        Appointment.objects.bulk_create([
            Appointment(business=cls.business, client=cls.crm_client, service=cls.services[-1],
                        start_at=now+timedelta(days=i+1), end_at=now+timedelta(days=i+1, minutes=30))
            for i in range(110)
        ])
        Appointment.objects.create(business=cls.business, client=cls.crm_client, service=cls.services[-1],
                                   start_at=now, end_at=now+timedelta(minutes=30), is_archived=True)

    def setUp(self):
        self.api = APIClient()
        self.api.force_authenticate(self.owner)

    def page(self, **params):
        response = self.api.get('/api/services/', {'business': self.business.pk, 'page_size': 10, **params})
        self.assertEqual(response.status_code, 200, response.data)
        self.assertIn('summary', response.data)
        return response.data

    def test_summary_covers_more_than_100_services_and_bookings(self):
        first = self.page()
        self.assertEqual(first['count'], 106)
        self.assertEqual(first['summary'], {'active': 105, 'average_duration_minutes': 33, 'used_in_bookings': 105})
        self.assertEqual(self.page(page=2)['summary'], first['summary'])
        self.assertEqual(len(first['results']), 10)

    def test_filtered_list_and_detail_count_old_and_repeated_bookings(self):
        data = self.page(search='Service 104')
        self.assertEqual(data['summary'], {'active': 1, 'average_duration_minutes': 90, 'used_in_bookings': 1})
        self.assertEqual(data['results'][0]['appointment_count'], 111)
        response = self.api.get(f'/api/services/{self.services[-1].pk}/')
        self.assertEqual(response.data['appointment_count'], 111)

    def test_inactive_empty_and_archive_filters(self):
        self.assertEqual(self.page(status='inactive')['summary'], {'active': 0, 'average_duration_minutes': None, 'used_in_bookings': 0})
        self.assertEqual(self.page(search='absent')['summary'], {'active': 0, 'average_duration_minutes': None, 'used_in_bookings': 0})
        archived = self.page(status='archived', include_archived='true')
        self.assertEqual(archived['count'], 1)
        self.assertEqual(archived['summary']['active'], 0)

    def test_foreign_business_and_bad_pagination(self):
        self.assertEqual(self.page(business=self.foreign.pk)['summary']['active'], 0)
        self.assertEqual(self.api.get('/api/services/', {'business':self.business.pk, 'page':999}).status_code, 404)

    def test_current_role_denial_and_membership_revocation(self):
        actor = User.objects.create_user(username='metrics-reader', email='metrics-reader@example.invalid')
        role = BusinessRole.objects.create(business=self.business, name='Metrics reader')
        permission = RolePermission.objects.create(business_role=role, resource='appointments', action='view', scope='business')
        member = BusinessMember.objects.create(business=self.business, user=actor, role='operator', business_role=role)
        self.api.force_authenticate(actor)
        self.assertEqual(self.page()['summary']['used_in_bookings'], 105)
        permission.is_allowed = False
        permission.save()
        self.assertEqual(self.page()['summary']['used_in_bookings'], 0)
        permission.is_allowed = True
        permission.save()
        member.is_active = False
        member.save()
        self.assertEqual(self.page()['count'], 0)

    def test_own_scope_counts_only_readable_appointments(self):
        actor = User.objects.create_user(username='own-metrics', email='own-metrics@example.invalid')
        role = BusinessRole.objects.create(business=self.business, name='Own metrics')
        RolePermission.objects.create(business_role=role, resource='appointments', action='view', scope='own')
        BusinessMember.objects.create(business=self.business, user=actor, role='operator', business_role=role)
        resource = Resource.objects.create(business=self.business, name='Own resource', linked_user=actor)
        own = Appointment.objects.filter(service=self.services[-1], is_archived=False).first()
        own.resource = resource
        own.save(update_fields=['resource'])
        # Selector itself must respect appointment scope even if its caller has a broader service queryset.
        service = with_appointment_counts(Service.objects.filter(pk=self.services[-1].pk), actor=actor).get()
        self.assertEqual(service.appointment_count, 1)
        self.api.force_authenticate(actor)
        self.assertEqual(self.api.get('/api/appointments/', {'business': self.business.pk}).data['count'], 1)
        self.assertEqual(self.page()['count'], 0)  # Existing Service OWN policy remains unchanged.

    def test_cross_business_legacy_link_cannot_inflate_counts(self):
        now = timezone.now()
        Appointment.objects.create(business=self.foreign, client=self.crm_client, service=self.services[-1],
                                   start_at=now, end_at=now+timedelta(minutes=30))
        BusinessMember.objects.create(business=self.foreign, user=self.owner, role='admin')
        self.assertEqual(self.page(search='Service 104')['results'][0]['appointment_count'], 111)

    def test_counts_do_not_add_a_query_per_row(self):
        with CaptureQueriesContext(connection) as small:
            self.page(page_size=10)
        with CaptureQueriesContext(connection) as large:
            self.page(page_size=100)
        self.assertLessEqual(len(large), len(small)+1)
