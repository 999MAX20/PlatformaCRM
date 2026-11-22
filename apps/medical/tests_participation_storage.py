from datetime import timedelta

from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.db.models.deletion import ProtectedError
from django.test import TestCase
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied

from apps.branches.models import Branch
from apps.businesses.models import Business, BusinessMember
from apps.scheduling.models import Appointment
from . import tests_appointment_access as fixtures
from .models import MedicalRoleAssignment, TreatmentParticipation
from .participation_access import assert_treatment_medical_basis


class TreatmentParticipationStorageTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        fixtures.AppointmentMedicalBasisTests.setUpTestData.__func__(cls)

    def values(self, **overrides):
        return dict(patient=self.patient, member=self.member, branch=self.first, proposed_by=self.owner,
                    proposed_at=timezone.now() - timedelta(days=1)) | overrides

    def active(self, **overrides):
        return TreatmentParticipation.objects.create(**self.values(**({"state": "active", "accepted_at": timezone.now()} | overrides)))

    def basis(self, participation):
        return assert_treatment_medical_basis(actor=self.doctor, business=self.business,
            patient_id=self.patient.pk, participation_id=participation.pk)

    def test_pending_never_gives_access_but_accepted_participation_does(self):
        item = TreatmentParticipation.objects.create(**self.values())
        item.full_clean()
        with self.assertRaises(PermissionDenied):
            self.basis(item)
        item.state, item.accepted_at = "active", timezone.now()
        item.save(update_fields=["state", "accepted_at"])
        self.assertEqual(self.basis(item).participation_id, item.pk)

    def test_completed_appointment_does_not_end_separate_participation(self):
        item = self.active()
        Appointment.objects.filter(pk=self.appointment.pk).update(status="completed")
        self.basis(item)
        Appointment.objects.filter(pk=self.appointment.pk).update(status="cancelled")
        self.basis(item)

    def test_closed_states_preserve_history_without_authorizing_access(self):
        for state in ("declined", "withdrawn", "ended", "revoked"):
            with self.subTest(state=state):
                item = TreatmentParticipation.objects.create(**self.values(state=state,
                    accepted_at=timezone.now() if state in ("ended", "revoked") else None,
                    closed_at=timezone.now(), closed_by=self.owner))
                item.full_clean()
                with self.assertRaises(PermissionDenied):
                    self.basis(item)
        self.assertEqual(TreatmentParticipation.objects.count(), 4)

    def test_database_rejects_invalid_state_timestamp_combinations(self):
        now = timezone.now()
        malformed = [dict(state="unknown"), dict(state="active"), dict(state="pending", accepted_at=now),
            dict(state="ended", accepted_at=now), dict(state="declined", closed_at=now),
            dict(state="active", accepted_at=now, closed_by=self.owner), dict(revision=0),
            dict(state="active", accepted_at=now - timedelta(days=2)),
            dict(state="ended", accepted_at=now, closed_at=now - timedelta(hours=1), closed_by=self.owner)]
        for values in malformed:
            with self.subTest(values=values), self.assertRaises(IntegrityError), transaction.atomic():
                TreatmentParticipation.objects.create(**self.values(**values))

    def test_duplicate_open_cycle_blocked_but_new_cycle_after_close_allowed(self):
        first = self.active()
        with self.assertRaises(IntegrityError), transaction.atomic():
            TreatmentParticipation.objects.create(**self.values())
        TreatmentParticipation.objects.filter(pk=first.pk).update(state="ended", closed_at=timezone.now(), closed_by=self.owner)
        second = TreatmentParticipation.objects.create(**self.values())
        self.assertNotEqual(first.pk, second.pk)
        with self.assertRaises(PermissionDenied):
            self.basis(first)
        with self.assertRaises(PermissionDenied):
            self.basis(second)

    def test_current_role_and_branch_limits_override_accepted_participation(self):
        item = self.active()
        self.assignment.branches.clear()
        with self.assertRaises(PermissionDenied):
            self.basis(item)
        self.assignment.branches.add(self.first)
        for changes in ({"kind": "assistant"}, {"kind": "doctor", "revoked_at": timezone.now()}):
            MedicalRoleAssignment.objects.filter(pk=self.assignment.pk).update(**changes)
            with self.subTest(changes=changes), self.assertRaises(PermissionDenied):
                self.basis(item)

    def test_future_acceptance_does_not_authorize(self):
        item = self.active(accepted_at=timezone.now() + timedelta(hours=1))
        with self.assertRaises(PermissionDenied):
            self.basis(item)

    def test_foreign_links_rejected_by_validation_and_reader(self):
        foreign = Business.objects.create(owner=self.owner, name="Foreign", slug="participation-foreign")
        foreign_branch = Branch.objects.create(business=foreign, name="Other branch")
        foreign_member = BusinessMember.objects.create(business=foreign, user=self.doctor, role="specialist")
        for changes in ({"branch": foreign_branch}, {"member": foreign_member}):
            with self.subTest(changes=changes):
                item = TreatmentParticipation(**self.values(state="active", accepted_at=timezone.now(), **changes))
                with self.assertRaises(ValidationError):
                    item.full_clean()
                item.save()
                with self.assertRaises(PermissionDenied):
                    self.basis(item)
                item.delete()

    def test_parent_history_cannot_be_deleted(self):
        self.active()
        for parent in (self.patient, self.member, self.first):
            with self.subTest(parent=type(parent).__name__), self.assertRaises(ProtectedError):
                parent.delete()
