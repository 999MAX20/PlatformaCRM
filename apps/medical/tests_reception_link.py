from datetime import timedelta
from unittest.mock import patch

from django.test import TestCase, override_settings
from rest_framework.exceptions import PermissionDenied

from apps.businesses.models import RolePermission
from apps.clients.models import Client
from apps.core.domain_errors import InvalidTransition
from apps.integrations.models import BusinessEvent
from apps.scheduling.models import Appointment
from apps.scheduling.record_commands import create_record
from .reception_link import link_reception_appointment
from . import tests_reception_booking as fixtures
from .tests_patient_services import key


@override_settings(MEDICAL_DATA_KEYS={"test": key(7)}, MEDICAL_DATA_ACTIVE_KEY_ID="test",
                   MEDICAL_IDENTITY_INDEX_KEY=key(8))
class ReceptionLinkTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        fixtures.ReceptionBookingTests.setUpTestData.__func__(cls)
        RolePermission.objects.create(business_role=cls.reception_member.business_role,
            resource="appointments", action="update", scope="business", is_allowed=True)

    request = fixtures.ReceptionBookingTests.request
    claim = fixtures.ReceptionBookingTests.claim
    book = fixtures.ReceptionBookingTests.book

    def setUp(self):
        fixtures.ReceptionBookingTests.setUp(self)
        self.existing = create_record(business=self.business, actor=self.reception, client=self.patient.client,
            service=self.service, resource=self.staff, start_at=self.start, branch=self.first,
            responsible_user=self.reception)

    def link(self, **changes):
        return link_reception_appointment(**({"actor": self.reception, "business_id": self.business.pk,
            "request_id": self.item.pk, "expected_revision": 2, "appointment_id": self.existing.pk,
            "expected_updated_at": self.existing.updated_at, "confirmed": True,
            "idempotency_key": "synthetic-link"} | changes))

    def test_link_and_replay_do_not_create_another_booking_or_event(self):
        events = BusinessEvent.objects.count()
        item, appointment, replayed = self.link()
        same, _, repeated = self.link()
        self.assertFalse(replayed)
        self.assertTrue(repeated)
        self.assertEqual(item.pk, same.pk)
        self.assertEqual(item.booked_appointment_id, appointment.pk)
        self.assertEqual((item.state, item.revision), ("booked", 3))
        self.assertEqual(Appointment.objects.count(), 2)
        self.assertEqual(BusinessEvent.objects.count(), events)

    def test_stale_cancelled_source_or_different_branch_cannot_be_linked(self):
        for changes in ({"expected_updated_at": self.existing.updated_at - timedelta(seconds=1)},
                        {"appointment_id": self.appointment.pk, "expected_updated_at": self.appointment.updated_at}):
            with self.subTest(changes=changes), self.assertRaises(InvalidTransition):
                self.link(**changes)
        for changes in ({"status": "cancelled"}, {"status": "created", "branch": self.second}):
            Appointment.objects.filter(pk=self.existing.pk).update(**changes)
            with self.assertRaises(InvalidTransition):
                self.link()
        self.item.refresh_from_db()
        self.assertEqual(self.item.state, "pending")

    def test_other_patient_and_revoked_update_permission_are_denied(self):
        client = Client.objects.create(business=self.business, full_name="Another synthetic patient")
        Appointment.objects.filter(pk=self.existing.pk).update(client=client)
        with self.assertRaises(PermissionDenied):
            self.link()
        Appointment.objects.filter(pk=self.existing.pk).update(client=self.patient.client)
        self.link()
        RolePermission.objects.filter(business_role=self.reception_member.business_role,
            resource="appointments", action="update").update(is_allowed=False)
        with self.assertRaises(PermissionDenied):
            self.link()

    def test_audit_failure_keeps_existing_booking_and_request_unlinked(self):
        with patch("apps.medical.reception_link.write_actor_audit_log", side_effect=RuntimeError("synthetic")):
            with self.assertRaises(RuntimeError):
                self.link()
        self.item.refresh_from_db()
        self.assertIsNone(self.item.booked_appointment_id)
        self.assertEqual(Appointment.objects.count(), 2)
        self.assertFalse(self.link()[2])
