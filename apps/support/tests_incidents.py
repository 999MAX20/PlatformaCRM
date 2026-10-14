from datetime import timedelta
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework.test import APIClient

from apps.core.models import AuditLog
from apps.core.models import ServiceComponentState
from apps.support.incidents import link_incident
from apps.support.models import IncidentLink, SupportCase
from apps.support.tests_domain import SupportFixture


class IncidentLinkTests(SupportFixture):
    def setUp(self):
        self.case = self.create()
        self.now = timezone.now()
        self.row = ServiceComponentState.objects.create(business=self.business, component="exports", episode=1,
            state="degraded", started_at=self.now-timedelta(minutes=10), observed_at=self.now, affected_count=3)
        self.api = APIClient()
        self.api.force_authenticate(self.platform_manager)

    def payload(self, **extra):
        return {"business": self.business.pk, "component": "exports", "episode": 1, **extra}

    def url(self, case=None):
        return f"/api/platform/support-cases/{(case or self.case).pk}/incidents/"

    def test_link_replay_is_immutable_and_does_not_change_public_state(self):
        public_before = self.api.get(f"/api/platform/support-cases/{self.case.pk}/").data
        first = self.api.post(self.url(), self.payload(), format="json")
        self.assertEqual(first.status_code, 200, first.data)
        self.assertEqual(self.api.post(self.url(), self.payload(), format="json").data, first.data)
        self.assertEqual(IncidentLink.objects.count(), 1)
        self.assertEqual(AuditLog.objects.filter(metadata__event="incident_linked").count(), 1)
        self.assertEqual(self.api.get(f"/api/platform/support-cases/{self.case.pk}/").data, public_before)
        result = self.api.get('/api/platform/support-incidents/', self.payload())
        self.assertEqual(result.status_code, 200, result.data)
        self.assertEqual(result.data['count'], 1)
        self.assertEqual(result.data['incident']['current']['state'], 'degraded')

    def test_foreign_case_cannot_be_linked_even_with_matching_component_episode(self):
        foreign = self.create(actor=self.other_owner, business=self.other_business)
        ServiceComponentState.objects.create(business=self.other_business, component="exports", episode=1,
            state="degraded", started_at=self.now, observed_at=self.now)
        self.assertEqual(self.api.post(self.url(foreign), self.payload(), format="json").status_code, 404)
        self.assertFalse(IncidentLink.objects.exists())

    def test_clinic_cannot_read_link_or_incident_or_inject_on_creation(self):
        self.api.post(self.url(), self.payload(), format="json")
        for actor in [self.employee, self.owner, self.clinic_admin]:
            self.api.force_authenticate(actor)
            self.assertEqual(self.api.get(self.url()).status_code, 403)
            self.assertEqual(self.api.post(self.url(), self.payload(), format="json").status_code, 403)
            self.assertEqual(self.api.get('/api/platform/support-incidents/', self.payload()).status_code, 403)
            response=self.api.get(f'/api/support/cases/{self.case.pk}/?business={self.business.pk}')
            self.assertNotIn('incident', str(response.data))
        self.api.force_authenticate(self.employee)
        result=self.api.post(f'/api/support/cases/?business={self.business.pk}',
            {'subject':'Test','text':'Test','incident':{'component':'exports','episode':1}},format='json',HTTP_IDEMPOTENCY_KEY='inject')
        self.assertEqual(result.status_code,400)

    def test_role_loss_denies_existing_link_replay(self):
        self.api.post(self.url(), self.payload(), format="json")
        get_user_model().objects.filter(pk=self.platform_manager.pk).update(role='staff')
        self.assertEqual(self.api.post(self.url(), self.payload(), format="json").status_code,403)

    def test_stale_recovered_and_new_episode_are_distinct(self):
        self.api.post(self.url(), self.payload(), format="json")
        self.row.observed_at=self.now-timedelta(minutes=4);self.row.save()
        result=self.api.get(self.url()).data['results'][0]
        self.assertEqual(result['current']['state'],'unknown')
        self.assertEqual(result['snapshot']['state'],'degraded')
        self.row.state='healthy';self.row.observed_at=timezone.now();self.row.recovered_at=self.row.observed_at;self.row.save()
        result=self.api.get(self.url()).data['results'][0]
        self.assertEqual(result['current']['state'],'healthy')
        self.assertIsNotNone(result['current']['recovered_at'])
        self.row.episode=2;self.row.state='degraded';self.row.started_at=timezone.now();self.row.recovered_at=None;self.row.save()
        result=self.api.get(self.url()).data['results'][0]
        self.assertTrue(result['historical']);self.assertIsNone(result['current'])
        self.assertEqual(result['snapshot']['state'],'degraded')
        self.assertEqual(result['episode'],1)
        self.assertEqual(self.api.get('/api/platform/support-incidents/',self.payload()).status_code,200)
        self.row.delete()
        self.assertIsNone(self.api.get(self.url()).data['results'][0]['current'])

    def test_invalid_missing_or_changed_episode_does_not_link(self):
        self.assertEqual(self.api.post(self.url(),self.payload(component='secret'),format='json').status_code,400)
        self.assertEqual(self.api.post(self.url(),self.payload(episode=0),format='json').status_code,400)
        self.assertEqual(self.api.post(self.url(),self.payload(episode=2),format='json').status_code,409)
        self.assertEqual(self.api.post(self.url(),self.payload(component='files'),format='json').status_code,404)
        self.assertFalse(IncidentLink.objects.exists())

    def test_create_and_link_is_atomic_and_idempotent(self):
        payload={'business':self.business.pk,'subject':'Incident help','text':'Please investigate','incident':{'component':'exports','episode':1}}
        first=self.api.post('/api/platform/support-cases/',payload,format='json',HTTP_IDEMPOTENCY_KEY='incident-create')
        self.assertEqual(first.status_code,201,first.data)
        self.assertEqual(self.api.post('/api/platform/support-cases/',payload,format='json',HTTP_IDEMPOTENCY_KEY='incident-create').data['id'],first.data['id'])
        self.assertEqual(IncidentLink.objects.count(),1)
        payload['incident']['episode']=2
        self.assertEqual(self.api.post('/api/platform/support-cases/',payload,format='json',HTTP_IDEMPOTENCY_KEY='incident-create').status_code,409)
        count=SupportCase.objects.count()
        self.assertEqual(self.api.post('/api/platform/support-cases/',payload,format='json',HTTP_IDEMPOTENCY_KEY='invalid-new').status_code,409)
        self.assertEqual(SupportCase.objects.count(),count)

    def test_audit_failure_rolls_back_link(self):
        with patch('apps.support.incidents.audit_case',side_effect=RuntimeError('audit failed')):
            with self.assertRaises(RuntimeError):
                link_incident(actor=self.platform_manager,case_id=self.case.pk,business_id=self.business.pk,component='exports',episode=1)
        self.assertFalse(IncidentLink.objects.exists())

    def test_link_pages_are_bounded_and_history_is_not_editable(self):
        self.api.post(self.url(),self.payload(),format='json')
        self.row.episode=2;self.row.started_at=timezone.now();self.row.save()
        self.api.post(self.url(),self.payload(episode=2),format='json')
        response=self.api.get(self.url(),{'page_size':1})
        self.assertEqual(response.data['count'],2);self.assertEqual(len(response.data['results']),1)
        self.assertEqual(self.api.delete(self.url()).status_code,405)
        self.assertEqual(self.api.patch(self.url(),{},format='json').status_code,405)
