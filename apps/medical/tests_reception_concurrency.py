from unittest import skipUnless
from datetime import timedelta

from django.db import connection
from django.test import TransactionTestCase, override_settings
from rest_framework.exceptions import PermissionDenied

from apps.core.models import AuditLog
from apps.scheduling.models import Appointment
from .models import ReceptionBookingRequest
from . import tests_reception_requests as fixtures
from . import tests_reception_claims as claim_fixtures
from . import tests_reception_booking as booking_fixtures
from . import tests_reception_link as link_fixtures
from . import tests_reception_transfer as transfer_fixtures
from . import tests_order_concurrency as concurrency
from .tests_patient_services import key
from .reception_contacts import update_reception_contact
from . import tests_reception_administration as administration_fixtures


@skipUnless(connection.vendor == "postgresql", "Reception handover races require PostgreSQL row locks")
@override_settings(MEDICAL_DATA_KEYS={"test": key(7)}, MEDICAL_DATA_ACTIVE_KEY_ID="test",
                   MEDICAL_IDENTITY_INDEX_KEY=key(8))
class ReceptionTransferConcurrencyTests(TransactionTestCase):
    def setUp(self):
        booking_fixtures.ReceptionBookingTests.setUpTestData.__func__(self)
        booking_fixtures.ReceptionBookingTests.setUp(self)

    request = fixtures.ReceptionCreationTests.request
    claim = claim_fixtures.ReceptionClaimTests.claim
    book = booking_fixtures.ReceptionBookingTests.book
    transfer = transfer_fixtures.ReceptionTransferTests.transfer
    parallel = concurrency.OrderConcurrencyTests.parallel

    def test_close_and_book_commit_only_one_outcome(self):
        close = lambda: update_reception_contact(actor=self.reception, business_id=self.business.pk,
            request_id=self.item.pk, expected_revision=2, action="declined", reason="Synthetic explicit refusal",
            idempotency_key="close-race")[1]
        self.assertCountEqual(self.parallel([close, lambda: self.book()[2]]), [False, "conflict"])
        self.item.refresh_from_db()
        self.assertEqual(self.item.revision, 3)
        self.assertEqual(Appointment.objects.count(), 2 if self.item.state == "booked" else 1)

    def test_duplicate_contact_records_one_attempt(self):
        contact = lambda: update_reception_contact(actor=self.reception, business_id=self.business.pk,
            request_id=self.item.pk, expected_revision=2, action="no_answer", reason="Synthetic contact",
            idempotency_key="contact-race")[1]
        self.assertCountEqual(self.parallel([contact, contact]), [False, True])
        self.assertEqual(self.item.contact_attempts.count(), 1)

    def test_same_handover_replays_once(self):
        self.assertCountEqual(self.parallel([lambda: self.transfer()[1], lambda: self.transfer()[1]]), [False, True])
        self.item.refresh_from_db()
        self.assertEqual((self.item.assignee_id, self.item.revision), (self.colleague_member.pk, 3))
        self.assertEqual(AuditLog.objects.filter(entity_type="ReceptionBookingRequest",
            metadata__kind="medical_follow_up_transferred").count(), 1)

    def test_handover_and_booking_do_not_both_succeed(self):
        def book_or_deny():
            try:
                return self.book()[2]
            except PermissionDenied:
                return "denied"
        results = self.parallel([lambda: self.transfer()[1], book_or_deny])
        self.assertEqual(results.count(False), 1)
        self.assertEqual(sum(result in ("denied", "conflict") for result in results), 1)
        self.item.refresh_from_db()
        self.assertEqual(self.item.revision, 3)
        if self.item.state == "booked":
            self.assertEqual(self.item.assignee_id, self.reception_member.pk)
            self.assertEqual(Appointment.objects.count(), 2)
        else:
            self.assertEqual((self.item.state, self.item.assignee_id), ("pending", self.colleague_member.pk))
            self.assertEqual(Appointment.objects.count(), 1)
        self.assertEqual(AuditLog.objects.filter(entity_type="ReceptionBookingRequest",
            metadata__kind__in=["medical_follow_up_transferred", "medical_follow_up_booked"]).count(), 1)


@skipUnless(connection.vendor == "postgresql", "Reception races require PostgreSQL row locks")
@override_settings(MEDICAL_DATA_KEYS={"test": key(7)}, MEDICAL_DATA_ACTIVE_KEY_ID="test",
                   MEDICAL_IDENTITY_INDEX_KEY=key(8))
class ReceptionConcurrencyTests(TransactionTestCase):
    def setUp(self):
        fixtures.ReceptionCreationTests.setUpTestData.__func__(self)

    request = fixtures.ReceptionCreationTests.request
    parallel = concurrency.OrderConcurrencyTests.parallel

    def test_same_command_creates_one_request(self):
        self.assertCountEqual(self.parallel([lambda: self.request()[1], lambda: self.request()[1]]), [False, True])
        self.assertEqual(ReceptionBookingRequest.objects.count(), 1)
        self.assertEqual(AuditLog.objects.filter(entity_type="ReceptionBookingRequest").count(), 1)
        self.assertEqual(Appointment.objects.count(), 1)


    def test_separate_clicks_reuse_one_active_request(self):
        self.assertCountEqual(self.parallel([lambda: self.request(idempotency_key="first")[1],
            lambda: self.request(idempotency_key="second")[1]]), [False, True])
        self.assertEqual(ReceptionBookingRequest.objects.count(), 1)
        self.assertEqual(AuditLog.objects.filter(entity_type="ReceptionBookingRequest").count(), 1)
        self.assertEqual(Appointment.objects.count(), 1)

@skipUnless(connection.vendor == "postgresql", "Reception claim races require PostgreSQL row locks")
@override_settings(MEDICAL_DATA_KEYS={"test": key(7)}, MEDICAL_DATA_ACTIVE_KEY_ID="test",
                   MEDICAL_IDENTITY_INDEX_KEY=key(8))
class ReceptionClaimConcurrencyTests(TransactionTestCase):
    def setUp(self):
        claim_fixtures.ReceptionClaimTests.setUpTestData.__func__(self)
        claim_fixtures.ReceptionClaimTests.setUp(self)

    request = fixtures.ReceptionCreationTests.request
    claim = claim_fixtures.ReceptionClaimTests.claim
    parallel = concurrency.OrderConcurrencyTests.parallel

    def test_overlapping_workers_publish_one_escalation(self):
        from django.utils import timezone
        from .models import ReceptionDuty, ReceptionNotice
        from .reception_notifications import escalate_reception_request
        now = timezone.now()
        ReceptionDuty.objects.create(business=self.business, branch=self.first, lead=self.reception_member,
            starts_at=now-timedelta(hours=1), ends_at=now+timedelta(hours=1))
        ReceptionBookingRequest.objects.filter(pk=self.item.pk).update(acceptance_due_at=now-timedelta(minutes=1))
        self.assertCountEqual(self.parallel([lambda: escalate_reception_request(self.item.pk), lambda: escalate_reception_request(self.item.pk)]), [True,False])
        self.assertEqual(ReceptionNotice.objects.filter(kind="escalated").count(),1)

    def test_two_receptionists_cannot_both_accept(self):
        self.assertCountEqual(self.parallel([lambda: self.claim()[1],
            lambda: self.claim(actor=self.colleague)[1]]), [False, "conflict"])
        self.item.refresh_from_db()
        self.assertIn(self.item.assignee_id, [self.reception_member.pk, self.colleague_member.pk])
        self.assertEqual(self.item.revision, 2)
        self.assertEqual(AuditLog.objects.filter(entity_type="ReceptionBookingRequest", action="update").count(), 1)


@skipUnless(connection.vendor == "postgresql", "Administrative referral races require PostgreSQL row locks")
@override_settings(MEDICAL_DATA_KEYS={"test":key(7)}, MEDICAL_DATA_ACTIVE_KEY_ID="test", MEDICAL_IDENTITY_INDEX_KEY=key(8))
class ReceptionAdministrationConcurrencyTests(TransactionTestCase):
    def setUp(self):
        administration_fixtures.ReceptionAdministrationTests.setUpTestData.__func__(self)
        administration_fixtures.ReceptionAdministrationTests.setUp(self)

    request=administration_fixtures.ReceptionAdministrationTests.request
    parallel=concurrency.OrderConcurrencyTests.parallel

    def test_distinct_commands_keep_one_source_referral(self):
        self.assertCountEqual(self.parallel([lambda:self.request(idempotency_key="one")[1],lambda:self.request(idempotency_key="two")[1]]),[False,True])
        self.assertEqual(ReceptionBookingRequest.objects.count(),1)
        self.assertEqual(AuditLog.objects.filter(entity_type="ReceptionBookingRequest").count(),1)


@skipUnless(connection.vendor == "postgresql", "Reception booking races require PostgreSQL row locks")
@override_settings(MEDICAL_DATA_KEYS={"test": key(7)}, MEDICAL_DATA_ACTIVE_KEY_ID="test",
                   MEDICAL_IDENTITY_INDEX_KEY=key(8))
class ReceptionBookingConcurrencyTests(TransactionTestCase):
    def setUp(self):
        booking_fixtures.ReceptionBookingTests.setUpTestData.__func__(self)
        booking_fixtures.ReceptionBookingTests.setUp(self)

    request = fixtures.ReceptionCreationTests.request
    claim = claim_fixtures.ReceptionClaimTests.claim
    book = booking_fixtures.ReceptionBookingTests.book
    parallel = concurrency.OrderConcurrencyTests.parallel

    def test_same_booking_command_replays_without_another_visit(self):
        self.assertCountEqual(self.parallel([lambda: self.book()[2], lambda: self.book()[2]]), [False, True])
        self.item.refresh_from_db()
        self.assertEqual((self.item.state, self.item.revision), ("booked", 3))
        self.assertEqual(Appointment.objects.count(), 2)

    def test_two_booking_commands_cannot_create_two_visits(self):
        self.assertCountEqual(self.parallel([lambda: self.book(idempotency_key="first")[2],
            lambda: self.book(idempotency_key="second")[2]]), [False, "conflict"])
        self.assertEqual(Appointment.objects.count(), 2)
        self.item.refresh_from_db()
        self.assertEqual(self.item.revision, 3)


@skipUnless(connection.vendor == "postgresql", "Reception link races require PostgreSQL row locks")
@override_settings(MEDICAL_DATA_KEYS={"test": key(7)}, MEDICAL_DATA_ACTIVE_KEY_ID="test",
                   MEDICAL_IDENTITY_INDEX_KEY=key(8))
class ReceptionLinkConcurrencyTests(TransactionTestCase):
    def setUp(self):
        link_fixtures.ReceptionLinkTests.setUpTestData.__func__(self)
        link_fixtures.ReceptionLinkTests.setUp(self)

    request = fixtures.ReceptionCreationTests.request
    claim = claim_fixtures.ReceptionClaimTests.claim
    book = booking_fixtures.ReceptionBookingTests.book
    link = link_fixtures.ReceptionLinkTests.link
    parallel = concurrency.OrderConcurrencyTests.parallel

    def test_link_and_new_booking_choose_one_result(self):
        results = self.parallel([lambda: self.link()[2],
            lambda: self.book(start_at=self.start + timedelta(hours=1))[2]])
        self.assertCountEqual(results, [False, "conflict"])
        self.item.refresh_from_db()
        self.assertEqual((self.item.state, self.item.revision), ("booked", 3))
        if results[0] is False:
            self.assertEqual(self.item.booked_appointment_id, self.existing.pk)
            self.assertEqual(Appointment.objects.count(), 2)
        else:
            self.assertNotEqual(self.item.booked_appointment_id, self.existing.pk)
            self.assertEqual(Appointment.objects.count(), 3)
        self.assertTrue(Appointment.objects.filter(pk=self.existing.pk).exists())
