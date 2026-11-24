from datetime import timedelta
from unittest.mock import patch

from django.db import DatabaseError
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.test import APIClient

from apps.core.domain_errors import InvalidTransition
from apps.notifications.models import Notification
from apps.notifications.module_sources import source_projection
from . import tests_reception_claims as fixtures
from .models import ReceptionBookingRequest, ReceptionDuty, ReceptionNotice
from .reception_duties import save_reception_duty, current_duty_recipient
from .reception_notifications import escalate_reception_request, ReceptionNotificationSource
from .participation_notifications import MedicalNotificationUnavailable
from .tests_patient_services import key


@override_settings(MEDICAL_DATA_KEYS={"test": key(7)}, MEDICAL_DATA_ACTIVE_KEY_ID="test", MEDICAL_IDENTITY_INDEX_KEY=key(8))
class ReceptionDutyTests(TestCase):
    setUpTestData = classmethod(fixtures.ReceptionClaimTests.setUpTestData.__func__)
    setUp = fixtures.ReceptionClaimTests.setUp
    request, claim = fixtures.ReceptionClaimTests.request, fixtures.ReceptionClaimTests.claim

    def configure(self, **changes):
        now = timezone.now()
        return save_reception_duty(**(dict(actor=self.owner, business_id=self.business.pk, branch_id=self.first.pk,
            lead_id=self.reception_member.pk, deputy_id=self.colleague_member.pk, lead_available=True,
            starts_at=now-timedelta(minutes=1), ends_at=now+timedelta(hours=8), expected_revision=0,
            reason="Synthetic duty", idempotency_key="duty") | changes))

    def test_current_lead_deputy_expiry_and_duplicate_escalation(self):
        self.configure()
        ReceptionBookingRequest.objects.filter(pk=self.item.pk).update(acceptance_due_at=timezone.now()-timedelta(minutes=1))
        self.assertTrue(escalate_reception_request(self.item.pk))
        self.assertFalse(escalate_reception_request(self.item.pk))
        self.assertEqual(ReceptionNotice.objects.filter(kind="escalated", recipient=self.reception).count(), 1)
        self.reception_assignment.branches.clear()
        self.assertTrue(escalate_reception_request(self.item.pk))
        self.assertEqual(ReceptionNotice.objects.filter(kind="escalated", recipient=self.colleague).count(), 1)
        ReceptionDuty.objects.update(ends_at=timezone.now())
        self.assertIsNone(current_duty_recipient(self.item, timezone.now()))
        self.item.refresh_from_db(); self.assertEqual(self.item.state, "new"); self.assertIsNone(self.item.assignee_id)

    def test_claimed_request_never_escalates_or_reassigns(self):
        self.configure(); self.claim()
        ReceptionBookingRequest.objects.filter(pk=self.item.pk).update(acceptance_due_at=timezone.now()-timedelta(minutes=1))
        self.assertFalse(escalate_reception_request(self.item.pk))
        self.assertFalse(ReceptionNotice.objects.filter(kind="escalated").exists())

    def test_owner_only_scope_revision_and_audit_rollback(self):
        for change in ({"actor": self.reception}, {"business_id": 999999}, {"lead_id": self.member.pk}, {"branch_id": self.second.pk}):
            with self.assertRaises(PermissionDenied): self.configure(**change)
        with self.assertRaises(ValidationError): self.configure(deputy_id=self.reception_member.pk)
        with patch("apps.medical.reception_duties.write_actor_audit_log", side_effect=RuntimeError("audit")):
            with self.assertRaises(RuntimeError): self.configure()
        self.assertFalse(ReceptionDuty.objects.exists())
        self.configure()
        with self.assertRaises(InvalidTransition): self.configure(idempotency_key="stale")

    def test_new_notice_private_source_and_revocation(self):
        notices = Notification.objects.filter(medical_reception_notice__request=self.item)
        self.assertEqual(notices.count(), 2)
        notice = notices.get(recipient=self.reception)
        self.assertEqual((notice.text, notice.client_id, notice.appointment_id), ("", None, None))
        self.assertEqual(source_projection(notice)["message_key"], "medical.reception.notice.new.onsite")
        self.assertEqual(source_projection(notice)["message_params"]["patient"], self.patient.client.full_name)
        self.assertIn(f"request={self.item.pk}", source_projection(notice)["action_url"])
        ids = list(notices.values_list("pk", flat=True))
        self.assertEqual(ReceptionNotificationSource.filter_ids(actor=self.reception, business=self.business, notification_ids=ids)[1], {notice.pk})
        self.reception_assignment.branches.clear()
        self.assertFalse(ReceptionNotificationSource.filter_ids(actor=self.reception, business=self.business, notification_ids=ids)[1])
        self.assertFalse(ReceptionNotificationSource.filter_ids(actor=self.owner, business=self.business, notification_ids=ids)[1])

    def test_feed_result_and_module_revocation(self):
        from apps.notifications.personal_selectors import personal_states
        from apps.businesses.models import BusinessCapability
        self.claim()
        self.assertTrue(personal_states(actor=self.doctor, business=self.business).exists())
        self.assertTrue(personal_states(actor=self.reception, business=self.business).exists())
        BusinessCapability.objects.filter(business=self.business,module_key="medical_records").update(is_enabled=False)
        self.assertFalse(personal_states(actor=self.reception, business=self.business).exists())
        self.assertFalse(personal_states(actor=self.doctor, business=self.business).exists())

    def test_notice_failure_rolls_back_claim_then_retry(self):
        with patch("apps.medical.reception_notifications.Notification.objects.create", side_effect=DatabaseError("storage")):
            with self.assertRaises(MedicalNotificationUnavailable): self.claim()
        self.item.refresh_from_db(); self.assertEqual(self.item.state, "new")
        self.claim(); self.assertTrue(ReceptionNotice.objects.filter(kind="changed").exists())

    def test_duty_api_options_and_write(self):
        api=APIClient(); api.force_authenticate(self.owner)
        url="/api/medical/role-management/reception-duty/"
        scope={"business_id": self.business.pk}
        self.assertEqual(api.get(url, scope).status_code, 200)
        options=api.get(url, scope | {"kind": "members", "branch_id": self.first.pk})
        self.assertEqual(options.status_code, 200, options.data)
        self.assertEqual({row["id"] for row in options.data["results"]}, {self.reception_member.pk, self.colleague_member.pk})
        self.assertEqual(options["Cache-Control"], "no-store, private")
        now=timezone.now()
        data=scope | {"branch_id":self.first.pk,"lead_id":self.reception_member.pk,"deputy_id":self.colleague_member.pk,
            "lead_available":False,"starts_at":now.isoformat(),"ends_at":(now+timedelta(hours=8)).isoformat(),"expected_revision":0,"reason":"Synthetic shift"}
        self.assertEqual(api.post(url,data,format="json",HTTP_IDEMPOTENCY_KEY="http-duty").status_code,200)
        self.assertEqual(api.post(url,data,format="json",HTTP_IDEMPOTENCY_KEY="http-duty").data["replayed"],True)
        api.force_authenticate(self.reception)
        self.assertEqual(api.get(url,scope).status_code,403)

    def test_queue_link_is_tenant_and_branch_scoped(self):
        api=APIClient(); api.force_authenticate(self.reception)
        url="/api/reception/booking-requests/"
        scope={"business_id":self.business.pk,"branch_id":self.first.pk,"request_id":self.item.pk}
        self.assertEqual([r["id"] for r in api.get(url,scope).data["results"]],[self.item.pk])
        self.assertEqual(api.get(url,scope | {"request_id":999999}).data["results"],[])
        self.assertEqual(api.get(url,scope | {"branch_id":self.second.pk}).status_code,403)
        self.assertIn(api.get(url,scope | {"business_id":999999}).status_code,[403,404])
