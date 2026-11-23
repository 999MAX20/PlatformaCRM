from datetime import timedelta
from unittest.mock import patch

from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.exceptions import NotFound, PermissionDenied, ValidationError

from apps.businesses.models import Business, RolePermission
from apps.core.domain_errors import InvalidTransition
from apps.core.idempotency import CRMCommandConflict
from apps.core.models import AuditLog
from apps.scheduling.models import Appointment
from apps.services.models import Service
from .models import ReceptionBookingRequest, TreatmentParticipation
from .reception_requests import request_primary_follow_up
from . import tests_encounter_services as fixtures
from .tests_patient_services import key


@override_settings(MEDICAL_DATA_KEYS={"test": key(7)}, MEDICAL_DATA_ACTIVE_KEY_ID="test",
                   MEDICAL_IDENTITY_INDEX_KEY=key(8))
class ReceptionCreationTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        fixtures.PrimaryEncounterDraftTests.setUpTestData.__func__(cls)

    def request(self, **changes):
        day = timezone.localdate() + timedelta(days=7)
        return request_primary_follow_up(**({"actor": self.doctor, "business_id": self.business.pk,
            "patient_id": self.patient.pk, "encounter_id": self.encounter_record.pk, "expected_revision": 1,
            "service_id": self.service.pk, "preferred_resource_id": self.staff.pk,
            "recommended_from": day, "recommended_until": day + timedelta(days=7),
            "patient_in_clinic": True, "idempotency_key": "synthetic-follow-up"} | changes))

    def test_doctor_without_calendar_create_can_send_once_without_booking(self):
        self.assertFalse(RolePermission.objects.filter(resource="appointments", action="create").exists())
        item, existing = self.request()
        replay, repeated = self.request()
        duplicate, reused = self.request(idempotency_key="second-click")
        self.assertFalse(existing)
        self.assertTrue(repeated and reused)
        self.assertEqual((item.pk, item.pk), (replay.pk, duplicate.pk))
        self.assertEqual(item.acceptance_due_at - item.created_at, timedelta(minutes=5))
        self.assertEqual(item.referring_clinician_id, self.member.pk)
        self.assertEqual(Appointment.objects.count(), 1)
        self.assertEqual(AuditLog.objects.filter(entity_type="ReceptionBookingRequest").count(), 1)

    def test_stale_and_conflicting_commands_do_not_change_intent(self):
        with self.assertRaises(InvalidTransition):
            self.request(expected_revision=2)
        item, _ = self.request()
        with self.assertRaises(CRMCommandConflict):
            self.request(patient_in_clinic=False)
        item.refresh_from_db()
        self.assertTrue(item.patient_in_clinic)

    def test_owner_assistant_and_removed_branch_are_denied(self):
        with self.assertRaises(PermissionDenied):
            self.request(actor=self.owner)
        self.assignment.kind = "assistant"
        self.assignment.save(update_fields=["kind"])
        with self.assertRaises(PermissionDenied):
            self.request()
        self.assignment.kind = "doctor"
        self.assignment.save(update_fields=["kind"])
        self.assignment.branches.clear()
        with self.assertRaises(PermissionDenied):
            self.request()
        self.assertFalse(ReceptionBookingRequest.objects.exists())

    def test_foreign_business_service_and_patient_are_denied(self):
        foreign = Business.objects.create(owner=self.owner, name="Foreign follow-up", slug="foreign-follow-up")
        service = Service.objects.create(business=foreign, name="Foreign follow-up service")
        for changes in ({"business_id": foreign.pk}, {"service_id": service.pk}, {"patient_id": self.patient.pk + 1000}):
            with self.subTest(changes=changes), self.assertRaises((PermissionDenied, NotFound)):
                self.request(**changes)

    def test_revoked_role_denies_replay_and_audit_failure_rolls_back(self):
        with patch("apps.medical.reception_requests.write_actor_audit_log", side_effect=RuntimeError("synthetic")):
            with self.assertRaises(RuntimeError):
                self.request()
        self.assertFalse(ReceptionBookingRequest.objects.exists())
        self.request()
        self.assignment.revoked_at = timezone.now()
        self.assignment.save(update_fields=["revoked_at"])
        with self.assertRaises(PermissionDenied):
            self.request()

    def test_invalid_period_and_boolean_duration_are_rejected(self):
        for changes in ({"recommended_until": timezone.localdate()}, {"duration_minutes": True},
                        {"patient_in_clinic": 1}):
            with self.subTest(changes=changes), self.assertRaises(ValidationError):
                self.request(**changes)

    def test_cancelled_source_requires_independent_participation_and_revocation_denies_replay(self):
        self.appointment.status = "cancelled"
        self.appointment.save(update_fields=["status"])
        with self.assertRaises(PermissionDenied):
            self.request()
        now = timezone.now()
        participation = TreatmentParticipation.objects.create(patient=self.patient, member=self.member,
            branch=self.first, proposed_by=self.owner, state="active", proposed_at=now, accepted_at=now)
        item, _ = self.request(participation_id=participation.pk)
        self.assertEqual(item.referring_clinician_id, self.member.pk)
        participation.state, participation.closed_at, participation.closed_by = "ended", timezone.now(), self.doctor
        participation.save()
        with self.assertRaises(PermissionDenied):
            self.request(participation_id=participation.pk)

    def test_reassignment_and_participation_from_another_branch_do_not_grant_access(self):
        self.appointment.resource = None
        self.appointment.save(update_fields=["resource"])
        with self.assertRaises(PermissionDenied):
            self.request()
        self.assignment.branches.add(self.second)
        now = timezone.now()
        participation = TreatmentParticipation.objects.create(patient=self.patient, member=self.member,
            branch=self.second, proposed_by=self.owner, state="active", proposed_at=now, accepted_at=now)
        with self.assertRaises(PermissionDenied):
            self.request(participation_id=participation.pk)
