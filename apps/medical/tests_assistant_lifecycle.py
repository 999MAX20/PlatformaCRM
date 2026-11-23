from unittest.mock import patch

from django.db import transaction
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied

from apps.core.models import AuditLog
from apps.scheduling.models import Appointment, Resource
from .models import DentalMedicalRecord, MedicalEncounter
from . import tests_assistant_acceptance as fixtures
from .tests_patient_services import key


@override_settings(MEDICAL_DATA_KEYS={"test": key(7)}, MEDICAL_DATA_ACTIVE_KEY_ID="test",
                   MEDICAL_IDENTITY_INDEX_KEY=key(8))
class AssistantLifecycleTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        fixtures.AssistantAcceptanceTests.setUpTestData.__func__(cls)

    setUp = fixtures.AssistantAcceptanceTests.setUp
    invite = fixtures.AssistantAcceptanceTests.invite
    accept = fixtures.AssistantAcceptanceTests.accept

    def change_appointment(self, **values):
        with transaction.atomic():
            appointment = Appointment.objects.get(pk=self.appointment.pk)
            for field, value in values.items():
                setattr(appointment, field, value)
            appointment.save(update_fields=list(values))

    def assert_ended(self):
        self.invitation.refresh_from_db()
        self.assertEqual(self.invitation.state, "ended")
        self.assertIsNotNone(self.invitation.closed_at)
        self.assertTrue(AuditLog.objects.filter(entity_type="AppointmentAssistant", entity_id=str(self.invitation.pk),
            metadata__kind="medical_assistant_basis_ended").exists())
        with self.assertRaises(PermissionDenied):
            self.accept()

    def test_cancel_then_restore_never_reactivates_pending_invitation(self):
        self.change_appointment(status="cancelled")
        self.change_appointment(status="created")
        self.assert_ended()

    def test_complete_then_restore_never_reactivates_accepted_invitation(self):
        self.accept()
        self.change_appointment(status="completed")
        self.change_appointment(status="created")
        self.assert_ended()
        self.assertIsNotNone(self.invitation.accepted_at)

    def test_change_clinician_then_return_does_not_restore_invitation(self):
        self.accept()
        other = Resource.objects.create(business=self.business, name="Synthetic replacement")
        self.change_appointment(resource=other)
        self.change_appointment(resource=self.staff)
        self.assert_ended()

    def test_relink_specialist_account_then_return_does_not_restore_invitation(self):
        with transaction.atomic():
            self.staff.linked_user = None
            self.staff.save(update_fields=["linked_user"])
        self.staff.linked_user = self.doctor
        self.staff.save(update_fields=["linked_user"])
        self.assert_ended()

    def test_archive_then_restore_does_not_restore_invitation(self):
        self.change_appointment(is_archived=True)
        self.change_appointment(is_archived=False)
        self.assert_ended()

    def test_branch_change_ends_invitation_and_simple_reschedule_keeps_it(self):
        self.change_appointment(status="confirmed", notes="Synthetic administrative note")
        self.invitation.refresh_from_db()
        self.assertEqual(self.invitation.state, "pending")
        self.change_appointment(branch=self.second)
        self.change_appointment(branch=self.first)
        self.assert_ended()

    def test_encounter_finalization_ends_basis_without_waiting_for_calendar(self):
        record = DentalMedicalRecord.objects.create(business=self.business, patient=self.patient,
            opened_by=self.doctor, number="synthetic-assistant-record")
        now = timezone.now()
        MedicalEncounter.objects.create(business=self.business, patient=self.patient, record=record,
            appointment=self.appointment, branch=self.first, primary_clinician=self.member,
            started_at=now, ended_at=now, finalized_at=now, finalized_by=self.doctor, state="finalized")
        self.assert_ended()

    def test_audit_failure_rolls_back_source_domain_transaction(self):
        with patch("apps.medical.assistant_lifecycle.write_actor_audit_log", side_effect=RuntimeError("synthetic failure")):
            with self.assertRaises(RuntimeError):
                self.change_appointment(status="cancelled")
        self.appointment.refresh_from_db()
        self.invitation.refresh_from_db()
        self.assertEqual((self.appointment.status, self.invitation.state), ("created", "pending"))

    def test_calendar_cancel_command_ends_invitation(self):
        from apps.scheduling.services import cancel_appointment
        cancel_appointment(appointment=self.appointment, actor=self.owner, reason="Synthetic cancellation")
        self.assert_ended()
