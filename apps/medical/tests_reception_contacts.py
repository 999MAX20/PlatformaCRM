from datetime import datetime, time, timedelta, timezone
from unittest.mock import patch

from django.test import TestCase, override_settings
from rest_framework.exceptions import PermissionDenied
from apps.core.domain_errors import InvalidTransition
from apps.scheduling.models import WorkingHours
from .tests_patient_services import key
from . import tests_reception_claims as fixtures
from .reception_contacts import update_reception_contact, expiry_ready
from .models import ReceptionContactAttempt


@override_settings(MEDICAL_DATA_KEYS={"test": key(7)}, MEDICAL_DATA_ACTIVE_KEY_ID="test", MEDICAL_IDENTITY_INDEX_KEY=key(8))
class ReceptionContactTests(TestCase):
    setUpTestData = classmethod(fixtures.ReceptionClaimTests.setUpTestData.__func__)
    request, claim = fixtures.ReceptionClaimTests.request, fixtures.ReceptionClaimTests.claim

    def setUp(self):
        fixtures.ReceptionClaimTests.setUp(self)
        self.item, _ = self.claim()
        self.business.timezone = "UTC"; self.business.save(update_fields=["timezone"])
        self.first.uses_business_defaults = True; self.first.save(update_fields=["uses_business_defaults"])
        for day in range(7):
            WorkingHours.objects.update_or_create(business=self.business, resource=None, weekday=day,
                defaults={"start_time": time(9), "end_time": time(18), "is_day_off": day >= 5})
        self.friday = datetime(2026, 11, 27, 10, tzinfo=timezone.utc)

    def contact(self, **changes):
        return update_reception_contact(**(dict(actor=self.reception, business_id=self.business.pk,
            request_id=self.item.pk, expected_revision=self.item.revision, action="no_answer",
            reason="Synthetic phone attempt", idempotency_key=f"contact-{self.item.revision}") | changes))

    def test_two_working_days_expiry_and_reopen_preserve_attempts(self):
        with patch("django.utils.timezone.now", return_value=self.friday):
            self.item, _ = self.contact()
        self.assertEqual(self.item.contact_due_at, datetime(2026, 11, 30, 18, tzinfo=timezone.utc))
        with patch("django.utils.timezone.now", return_value=self.friday + timedelta(hours=2)):
            self.item, _ = self.contact()
        with patch("django.utils.timezone.now", return_value=self.item.contact_due_at):
            with self.assertRaises(InvalidTransition): self.contact(action="expired")
        with patch("django.utils.timezone.now", return_value=self.friday + timedelta(days=3)):
            self.item, _ = self.contact()
            with self.assertRaises(InvalidTransition): self.contact(action="expired")
        with patch("django.utils.timezone.now", return_value=self.item.contact_due_at):
            self.item, _ = self.contact(action="expired")
        self.assertEqual(self.item.state, "expired")
        with patch("django.utils.timezone.now", return_value=self.item.contact_due_at + timedelta(minutes=1)):
            self.item, _ = self.contact(action="reopen")
        self.assertEqual((self.item.state, self.item.contact_cycle, self.item.assignee_id), ("new", 2, None))
        self.assertIsNone(self.item.contact_due_at)
        self.assertEqual(ReceptionContactAttempt.objects.count(), 3)

    def test_refusal_is_explicit_current_assignee_and_replay(self):
        for changes in ({"actor": self.colleague}, {"actor": self.owner}, {"business_id": 999999}):
            with self.assertRaises(PermissionDenied): self.contact(**changes)
        item, replayed = self.contact(action="declined", idempotency_key="refusal")
        same, repeated = self.contact(action="declined", idempotency_key="refusal")
        self.assertFalse(replayed); self.assertTrue(repeated)
        self.assertEqual(item.pk, same.pk); self.assertEqual(item.state, "declined")
        self.assertEqual(ReceptionContactAttempt.objects.count(), 0)

    def test_role_branch_revocation_and_audit_rollback(self):
        self.reception_assignment.branches.set([self.second])
        with self.assertRaises(PermissionDenied): self.contact()
        self.reception_assignment.branches.set([self.first])
        with patch("apps.medical.reception_contacts.write_actor_audit_log", side_effect=RuntimeError("audit unavailable")):
            with self.assertRaises(RuntimeError): self.contact()
        self.assertEqual(ReceptionContactAttempt.objects.count(), 0)
        self.item.refresh_from_db(); self.assertEqual(self.item.revision, 2)
        self.reception_assignment.revoked_at = self.reception_assignment.granted_at + timedelta(seconds=1)
        self.reception_assignment.save(update_fields=["revoked_at"])
        with self.assertRaises(PermissionDenied): self.contact()

    def test_missing_schedule_and_successful_contact_never_fake_no_answer(self):
        WorkingHours.objects.filter(business=self.business).delete()
        self.item, _ = self.contact(action="contacted")
        self.assertIsNone(self.item.contact_due_at)
        self.assertFalse(expiry_ready(self.item, self.friday + timedelta(days=100)))
        with self.assertRaises(InvalidTransition): self.contact(action="expired")

    def test_http_validation_conflict_current_scope_and_history(self):
        from rest_framework.test import APIClient
        api = APIClient(); api.force_authenticate(self.reception)
        url = f"/api/reception/booking-requests/{self.item.pk}/contact/"
        payload = dict(business_id=self.business.pk, expected_revision=2, action="no_answer", reason="Synthetic HTTP attempt")
        for delta in ({"expected_revision": True}, {"reason": ""}, {"action": "booked"}, {"extra": 1}):
            self.assertEqual(api.post(url, payload | delta, format="json", HTTP_IDEMPOTENCY_KEY="bad").status_code, 400)
        response = api.post(url, payload, format="json", HTTP_IDEMPOTENCY_KEY="http-attempt")
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response["Cache-Control"], "no-store, private")
        self.assertEqual(api.post(url, payload, format="json", HTTP_IDEMPOTENCY_KEY="stale").status_code, 409)
        history = api.get(url.replace("contact/", "history/"), {"business_id": self.business.pk}).data["results"]
        self.assertEqual((history[0]["outcome"], history[0]["cycle"]), ("no_answer", 1))
        self.reception_assignment.branches.set([self.second])
        self.assertEqual(api.post(url, payload, format="json", HTTP_IDEMPOTENCY_KEY="http-attempt").status_code, 403)
        api.force_authenticate(None)
        self.assertEqual(api.post(url, payload, format="json").status_code, 401)

    def test_duplicate_open_request_blocks_reopening(self):
        self.item, _ = self.contact(action="declined")
        other, _ = self.request(idempotency_key="new-referral")
        self.assertNotEqual(other.pk, self.item.pk)
        with self.assertRaises(InvalidTransition): self.contact(action="reopen")
        self.item.refresh_from_db(); self.assertEqual(self.item.state, "declined")

    def test_branch_holiday_and_split_hours_are_not_contact_days(self):
        from apps.branches.models import ScheduleDay
        from .reception_contacts import contact_deadline
        self.first.uses_business_defaults = False; self.first.save(update_fields=["uses_business_defaults"])
        for weekday in range(5):
            ScheduleDay.objects.create(business=self.business, branch=self.first, weekday=weekday,
                intervals=[{"start": "09:00", "end": "12:00"}, {"start": "14:00", "end": "18:00"}])
        ScheduleDay.objects.create(business=self.business, branch=self.first, date=self.friday.date() + timedelta(days=3), intervals=[])
        self.item.refresh_from_db()
        self.assertEqual(contact_deadline(self.item, self.friday), datetime(2026, 12, 1, 18, tzinfo=timezone.utc))


@override_settings(MEDICAL_DATA_KEYS={"test": key(7)}, MEDICAL_DATA_ACTIVE_KEY_ID="test", MEDICAL_IDENTITY_INDEX_KEY=key(8))
class ReceptionCancelledBookingTests(TestCase):
    from . import tests_reception_booking as booking
    setUpTestData = classmethod(booking.ReceptionBookingTests.setUpTestData.__func__)
    setUp = booking.ReceptionBookingTests.setUp
    request, claim, book = booking.ReceptionBookingTests.request, booking.ReceptionBookingTests.claim, booking.ReceptionBookingTests.book
    contact = ReceptionContactTests.contact

    def test_only_cancelled_booking_can_return_to_queue_without_deleting_visit(self):
        from apps.scheduling.models import Appointment
        self.item, visit, _ = self.book()
        with self.assertRaises(InvalidTransition): self.contact(action="reopen")
        Appointment.objects.filter(pk=visit.pk).update(status="cancelled")
        self.item, _ = self.contact(action="reopen")
        self.assertEqual((self.item.state, self.item.contact_cycle), ("new", 2))
        self.assertIsNone(self.item.booked_appointment_id)
        self.assertTrue(Appointment.objects.filter(pk=visit.pk, status="cancelled").exists())
