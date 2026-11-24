from datetime import timedelta
from unittest.mock import patch
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied
from rest_framework.test import APIClient
from apps.core.domain_errors import InvalidTransition
from apps.core.models import AuditLog
from apps.scheduling.models import Appointment, Resource
from . import tests_reception_booking as fixtures
from .models import ReceptionBookingRequest
from .reception_administration import request_administrative_follow_up, read_administrative_follow_up
from .reception_claims import claim_reception_request
from .reception_selectors import list_reception_requests
from .tests_patient_services import key


@override_settings(MEDICAL_DATA_KEYS={"test":key(7)},MEDICAL_DATA_ACTIVE_KEY_ID="test",MEDICAL_IDENTITY_INDEX_KEY=key(8))
class ReceptionAdministrationTests(TestCase):
    setUpTestData=classmethod(fixtures.ReceptionBookingTests.setUpTestData.__func__)

    def setUp(self):
        self.offline=Resource.objects.create(business=self.business,name="Synthetic specialist without login",resource_type="staff")
        Appointment.objects.filter(pk=self.appointment.pk).update(resource=self.offline)
        self.appointment.refresh_from_db()
        self.scope=dict(actor=self.reception,business_id=self.business.pk,branch_id=self.first.pk,client_id=self.patient.client_id)

    def request(self,**changes):
        day=timezone.localdate()+timedelta(days=7)
        return request_administrative_follow_up(**(self.scope | dict(source_appointment_id=self.appointment.pk,
            expected_updated_at=self.appointment.updated_at,service_id=self.service.pk,preferred_resource_id=self.offline.pk,
            recommended_from=day,recommended_until=day+timedelta(days=7),patient_in_clinic=True,
            reason="Synthetic recommendation handed over",idempotency_key="administrative") | changes))

    def test_no_login_referrer_and_real_author_with_duplicate_guard(self):
        item,replayed=self.request()
        self.assertFalse(replayed);self.assertIsNone(item.referring_clinician_id)
        self.assertEqual((item.created_by_id,item.referring_resource_id),(self.reception.pk,self.offline.pk))
        self.assertEqual(self.request()[0].pk,item.pk)
        self.assertEqual(self.request(idempotency_key="another-click")[0].pk,item.pk)
        self.assertEqual(ReceptionBookingRequest.objects.count(),1)
        self.assertEqual(Appointment.objects.count(),1)
        row=list_reception_requests(actor=self.reception,business_id=self.business.pk,branch_id=self.first.pk)["results"][0]
        self.assertEqual(row["referring_clinician_name"],self.offline.name)
        event=AuditLog.objects.get(entity_type="ReceptionBookingRequest")
        self.assertEqual(event.actor_id,self.reception.pk)
        self.assertEqual(event.metadata["referring_resource_id"],self.offline.pk)
        claimed,_=claim_reception_request(actor=self.reception,business_id=self.business.pk,request_id=item.pk,
            expected_revision=1,idempotency_key="claim-admin")
        self.assertEqual(claimed.state,"pending")
        from .reception_booking import book_reception_request
        start=(timezone.now()+timedelta(days=7)).replace(hour=10,minute=0,second=0,microsecond=0)
        booked,visit,_=book_reception_request(actor=self.reception,business_id=self.business.pk,request_id=item.pk,
            expected_revision=2,resource_id=self.offline.pk,start_at=start,expected_price="100.00",
            expected_duration_minutes=30,confirmed=True,idempotency_key="book-offline-specialist")
        self.assertEqual(booked.state,"booked");self.assertEqual(visit.resource_id,self.offline.pk)
        self.assertEqual(Appointment.objects.count(),2)

    def test_current_role_branch_calendar_and_replay_are_required(self):
        for change in ({"actor":self.owner},{"actor":self.doctor},{"branch_id":self.second.pk},{"business_id":999999},{"client_id":999999}):
            with self.assertRaises(PermissionDenied):self.request(**change)
        self.request()
        self.reception_assignment.branches.clear()
        with self.assertRaises(PermissionDenied):self.request()

    def test_source_change_cancellation_and_audit_rollback(self):
        with self.assertRaises(InvalidTransition):self.request(expected_updated_at=self.appointment.updated_at-timedelta(seconds=1))
        with patch("apps.medical.reception_administration.write_actor_audit_log",side_effect=RuntimeError("audit")):
            with self.assertRaises(RuntimeError):self.request()
        self.assertFalse(ReceptionBookingRequest.objects.exists())
        Appointment.objects.filter(pk=self.appointment.pk).update(status="cancelled")
        with self.assertRaises(PermissionDenied):self.request()

    def test_http_options_and_separate_author(self):
        api=APIClient();api.force_authenticate(self.reception)
        scope={key:value for key,value in self.scope.items() if key!="actor"}
        root="/api/reception/booking-requests/"
        options=api.get(root+"administrative-options/",scope|{"kind":"appointments"})
        self.assertEqual(options.status_code,200,options.data)
        self.assertEqual(options.data["results"][0]["name"],self.offline.name)
        self.assertEqual(options["Cache-Control"],"no-store, private")
        day=timezone.localdate()+timedelta(days=7)
        payload=scope|dict(source_appointment_id=self.appointment.pk,expected_updated_at=self.appointment.updated_at.isoformat(),
            service_id=self.service.pk,preferred_resource_id=self.offline.pk,recommended_from=day.isoformat(),
            recommended_until=day.isoformat(),patient_in_clinic=True,reason="Synthetic HTTP recommendation")
        result=api.post(root+"administrative/",payload,format="json",HTTP_IDEMPOTENCY_KEY="admin-http")
        self.assertEqual(result.status_code,200,result.data)
        self.assertEqual(ReceptionBookingRequest.objects.get(pk=result.data["id"]).created_by_id,self.reception.pk)
        self.assertEqual(api.post(root+"administrative/",payload|{"referring_clinician_id":self.member.pk},format="json",HTTP_IDEMPOTENCY_KEY="forged").status_code,400)
        api.force_authenticate(self.owner)
        self.assertEqual(api.get(root+"administrative-options/",scope|{"kind":"appointments"}).status_code,403)
