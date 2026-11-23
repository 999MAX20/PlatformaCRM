from datetime import time, timedelta
from decimal import Decimal
from unittest.mock import patch

from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied

from apps.businesses.models import Business, RolePermission
from apps.core.domain_errors import InvalidTransition, ScheduleConflict
from apps.core.models import AuditLog
from apps.payments.models import Payment
from apps.integrations.models import BusinessEvent
from apps.scheduling.models import Appointment, Resource, WorkingHours
from .reception_booking import book_reception_request
from . import tests_reception_claims as fixtures
from .tests_patient_services import key


@override_settings(MEDICAL_DATA_KEYS={"test": key(7)}, MEDICAL_DATA_ACTIVE_KEY_ID="test",
                   MEDICAL_IDENTITY_INDEX_KEY=key(8))
class ReceptionBookingTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        fixtures.ReceptionClaimTests.setUpTestData.__func__(cls)
        cls.business.timezone = "UTC"
        cls.business.save(update_fields=["timezone"])
        cls.first.uses_business_defaults = True
        cls.first.save(update_fields=["uses_business_defaults"])
        cls.service.price_from, cls.service.duration_minutes = Decimal("100.00"), 30
        cls.service.save(update_fields=["price_from", "duration_minutes"])
        for action in ("view", "create"):
            RolePermission.objects.create(business_role=cls.reception_member.business_role,
                resource="appointments", action=action, scope="business", is_allowed=True)
        for weekday in range(7):
            WorkingHours.objects.create(business=cls.business, weekday=weekday, start_time=time(8), end_time=time(20))

    request = fixtures.ReceptionClaimTests.request
    claim = fixtures.ReceptionClaimTests.claim

    def setUp(self):
        fixtures.ReceptionClaimTests.setUp(self)
        self.item, _ = self.claim()
        self.start = (timezone.now() + timedelta(days=7)).replace(hour=10, minute=0, second=0, microsecond=0)

    def book(self, **changes):
        return book_reception_request(**({"actor": self.reception, "business_id": self.business.pk,
            "request_id": self.item.pk, "expected_revision": 2, "resource_id": self.staff.pk,
            "start_at": self.start, "expected_price": "100.00", "expected_duration_minutes": 30,
            "confirmed": True, "idempotency_key": "synthetic-booking"} | changes))

    def test_booking_and_request_commit_together_and_replay_returns_same_visit(self):
        item, appointment, replayed = self.book()
        same, visit, repeated = self.book()
        self.assertFalse(replayed)
        self.assertTrue(repeated)
        self.assertEqual((item.pk, appointment.pk), (same.pk, visit.pk))
        self.assertEqual((item.state, item.revision, item.booked_appointment_id), ("booked", 3, appointment.pk))
        self.assertEqual(appointment.client_id, self.patient.client_id)
        self.assertEqual(appointment.responsible_user_id, self.reception.pk)
        self.assertEqual(appointment.notes, "")
        self.assertEqual(Appointment.objects.count(), 2)
        self.assertFalse(Payment.objects.exists())
        self.assertEqual(BusinessEvent.objects.filter(event_type="appointment.created",
            external_id=str(appointment.pk)).count(), 1)
        with self.assertRaises(InvalidTransition):
            self.book(idempotency_key="another-booking")

    def test_audit_failure_rolls_back_calendar_request_and_allows_retry(self):
        audit_before = AuditLog.objects.count()
        events_before = BusinessEvent.objects.count()
        with patch("apps.medical.reception_booking.write_actor_audit_log", side_effect=RuntimeError("synthetic")):
            with self.assertRaises(RuntimeError):
                self.book()
        self.item.refresh_from_db()
        self.assertEqual((self.item.state, self.item.revision), ("pending", 2))
        self.assertIsNone(self.item.booked_appointment_id)
        self.assertEqual(Appointment.objects.count(), 1)
        self.assertEqual(AuditLog.objects.count(), audit_before)
        self.assertEqual(BusinessEvent.objects.count(), events_before)
        self.assertFalse(self.book()[2])

    def test_busy_slot_and_changed_terms_leave_request_pending(self):
        with self.assertRaises(InvalidTransition):
            self.book(expected_price="99.00")
        Appointment.objects.create(business=self.business, client=self.patient.client, service=self.service,
            resource=self.staff, branch=self.first, start_at=self.start, end_at=self.start + timedelta(minutes=30))
        with self.assertRaises(ScheduleConflict):
            self.book()
        self.item.refresh_from_db()
        self.assertEqual(self.item.state, "pending")
        self.assertIsNone(self.item.booked_appointment_id)

    def test_foreign_resource_and_request_scope_are_rejected(self):
        foreign = Business.objects.create(owner=self.owner, name="Foreign booking", slug="foreign-reception-booking")
        resource = Resource.objects.create(business=foreign, name="Foreign specialist")
        for changes in ({"business_id": foreign.pk}, {"resource_id": resource.pk}):
            with self.subTest(changes=changes), self.assertRaises(PermissionDenied):
                self.book(**changes)
        self.item.refresh_from_db()
        self.assertEqual(self.item.state, "pending")
        self.assertIsNone(self.item.booked_appointment_id)

    def test_only_current_assignee_can_book_with_calendar_permission(self):
        with self.assertRaises(PermissionDenied):
            self.book(actor=self.colleague)
        RolePermission.objects.filter(business_role=self.reception_member.business_role,
            resource="appointments", action="create").update(is_allowed=False)
        with self.assertRaises(PermissionDenied):
            self.book()
        self.assertEqual(Appointment.objects.count(), 1)

    def test_revoked_calendar_and_branch_permissions_deny_replay(self):
        self.book()
        permission = RolePermission.objects.get(business_role=self.reception_member.business_role,
            resource="appointments", action="view")
        permission.is_allowed = False
        permission.save(update_fields=["is_allowed"])
        with self.assertRaises(PermissionDenied):
            self.book()
        permission.is_allowed = True
        permission.save(update_fields=["is_allowed"])
        self.reception_assignment.branches.clear()
        with self.assertRaises(PermissionDenied):
            self.book()
