from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.test import TestCase
from django.utils import timezone

from apps.businesses.models import BusinessMember, BusinessRole
from apps.scheduling.models import Appointment
from .models import AppointmentAssistant, MedicalRoleAssignment
from . import tests_appointment_access as appointment_fixtures


class AssistantInvitationIntegrityTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        appointment_fixtures.AppointmentMedicalBasisTests.setUpTestData.__func__(cls)
        cls.assistant = get_user_model().objects.create_user(username="synthetic-assistant")
        cls.assistant_member = BusinessMember.objects.create(business=cls.business, user=cls.assistant, role="specialist")
        role = BusinessRole.objects.create(business=cls.business, name="Synthetic assistant")
        cls.assistant_role = MedicalRoleAssignment.objects.create(member=cls.assistant_member,
            business_role=role, kind="assistant", granted_by=cls.owner)

    def invitation(self, **changes):
        return AppointmentAssistant(**({"business": self.business, "patient": self.patient,
            "appointment": self.appointment, "branch": self.first, "assignment": self.assistant_role,
            "primary_clinician": self.member, "invited_by": self.doctor} | changes))

    def test_pending_invitation_preserves_scope_and_does_not_grant_doctor_basis(self):
        item = self.invitation()
        item.full_clean()
        item.save()
        self.assertEqual((item.state, item.accepted_at, item.revision), ("pending", None, 1))
        from rest_framework.exceptions import PermissionDenied
        from .appointment_access import assert_appointment_medical_basis
        with self.assertRaises(PermissionDenied):
            assert_appointment_medical_basis(actor=self.assistant, business=self.business,
                patient_id=self.patient.pk, appointment_id=self.appointment.pk)

    def test_original_scope_cannot_be_retargeted(self):
        item = self.invitation()
        item.save()
        item.branch = self.second
        with self.assertRaises(ValidationError):
            item.full_clean()

    def test_invitation_must_match_current_appointment_branch_and_clinician(self):
        for changes in ({"branch": self.second}, {"primary_clinician": self.assistant_member},
                        {"assignment": self.assignment}):
            with self.subTest(changes=list(changes)), self.assertRaises(ValidationError):
                self.invitation(**changes).full_clean()

    def test_active_requires_acceptance_and_declined_requires_actor(self):
        for changes in ({"state": "active"}, {"state": "declined", "closed_at": timezone.now()},
                        {"state": "revoked", "closed_at": timezone.now()}):
            with self.subTest(changes=changes), self.assertRaises(IntegrityError), transaction.atomic():
                self.invitation(**changes).save()

    def test_one_open_invitation_and_fresh_invitation_after_closure(self):
        first = self.invitation()
        first.save()
        with self.assertRaises(IntegrityError), transaction.atomic():
            self.invitation().save()
        first.state, first.closed_at, first.closed_by = "revoked", timezone.now(), self.doctor
        first.revision += 1
        first.full_clean()
        first.save()
        replacement = self.invitation()
        replacement.full_clean()
        replacement.save()
        self.assertNotEqual(first.pk, replacement.pk)
        self.assertIsNone(replacement.accepted_at)

    def test_reassignment_allows_closing_history_without_rewriting_original_doctor(self):
        item = self.invitation()
        item.save()
        Appointment.objects.filter(pk=self.appointment.pk).update(resource=None)
        item.state, item.closed_at = "ended", timezone.now()
        item.revision += 1
        item.full_clean()
        item.save()
        item.refresh_from_db()
        self.assertEqual(item.primary_clinician_id, self.member.pk)
