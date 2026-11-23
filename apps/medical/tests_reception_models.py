from datetime import timedelta

from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.test import TestCase
from django.utils import timezone

from apps.businesses.models import Business
from apps.clients.models import Client
from apps.scheduling.models import Appointment
from apps.services.models import Service
from .models import ReceptionBookingRequest
from . import tests_appointment_access as fixtures


class ReceptionRequestIntegrityTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        fixtures.AppointmentMedicalBasisTests.setUpTestData.__func__(cls)

    def request(self, **changes):
        day = timezone.localdate() + timedelta(days=7)
        return ReceptionBookingRequest(**({"business": self.business, "patient": self.patient,
            "source_appointment": self.appointment, "branch": self.first,
            "referring_clinician": self.member, "created_by": self.doctor,
            "service": self.service, "preferred_resource": self.staff,
            "recommended_from": day, "recommended_until": day + timedelta(days=7)} | changes))

    def test_new_intent_is_not_a_booking(self):
        item = self.request()
        item.full_clean()
        item.save()
        item.refresh_from_db()
        self.assertEqual(item.state, "new")
        self.assertIsNone(item.booked_appointment_id)
        self.assertIsNone(item.assignee_id)
        self.assertEqual(Appointment.objects.count(), 1)

    def test_database_prevents_duplicate_active_intent_but_preserves_closed_history(self):
        first = self.request()
        first.save()
        with self.assertRaises(IntegrityError), transaction.atomic():
            self.request().save()
        first.state, first.closed_at, first.closure_reason = "cancelled", timezone.now(), "Synthetic cancellation"
        first.full_clean()
        first.save()
        replacement = self.request()
        replacement.full_clean()
        replacement.save()
        self.assertNotEqual(first.pk, replacement.pk)
        self.assertEqual(ReceptionBookingRequest.objects.count(), 2)

    def test_invalid_period_duration_claim_and_terminal_states_fail_at_database_boundary(self):
        for changes in ({"recommended_until": timezone.localdate()}, {"duration_minutes": 0},
                        {"assignee": self.member}, {"state": "booked"},
                        {"state": "expired", "closed_at": timezone.now()}, {"state": "unknown"}):
            with self.subTest(changes=changes), self.assertRaises(IntegrityError), transaction.atomic():
                self.request(**changes).save()

    def test_foreign_links_and_another_patients_booking_rejected(self):
        foreign = Business.objects.create(owner=self.owner, name="Foreign referral", slug="foreign-referral")
        foreign_service = Service.objects.create(business=foreign, name="Foreign service")
        other_client = Client.objects.create(business=self.business, full_name="Other synthetic patient")
        other = Appointment.objects.create(business=self.business, client=other_client, branch=self.first,
            service=self.service, resource=self.staff, start_at=self.appointment.start_at,
            end_at=self.appointment.end_at)
        for changes in ({"business": foreign}, {"service": foreign_service},
                        {"source_appointment": other}, {"booked_appointment": self.appointment},
                        {"booked_appointment": other}):
            with self.subTest(changes=list(changes)), self.assertRaises(ValidationError):
                self.request(**changes).full_clean()

    def test_original_source_and_author_remain_immutable(self):
        item = self.request()
        item.save()
        item.created_at += timedelta(seconds=1)
        with self.assertRaises(ValidationError):
            item.full_clean()
