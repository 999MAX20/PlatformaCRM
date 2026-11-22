from datetime import timedelta
from unittest.mock import patch

from django.db import DatabaseError
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied

from apps.branches.models import Branch
from apps.businesses.models import Business, BusinessMember, RolePermission
from apps.clients.models import Client
from apps.core.domain_errors import InvalidTransition
from apps.core.models import CRMCommandIdempotency
from apps.scheduling.models import Appointment, Resource
from .audit import MedicalAuditUnavailable
from .models import DentalMedicalRecord, MedicalEncounter, MedicalAuditEvent, MedicalRoleAssignment, PatientProfile, TreatmentParticipation
from .participation_closure import end_own_participation
from .tests_participation_closure import ParticipationClosureTests as fixtures
from .tests_patient_services import key


@override_settings(MEDICAL_DATA_KEYS={"test": key(7)}, MEDICAL_DATA_ACTIVE_KEY_ID="test",
                   MEDICAL_IDENTITY_INDEX_KEY=key(8))
class OwnParticipationEndTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        fixtures.setUpTestData.__func__(cls)
        RolePermission.objects.create(business_role=cls.role, resource="medical_participation", action="update", scope="own")

    propose = fixtures.propose
    respond = fixtures.respond
    active = fixtures.active

    def end(self, item, **overrides):
        return end_own_participation(**(dict(actor=self.recipient, business_id=self.business.pk,
            patient_id=self.patient.pk, participation_id=item.pk, expected_revision=2,
            idempotency_key="own-end") | overrides))

    def assign_booking(self):
        resource = Resource.objects.create(business=self.business, name="Synthetic recipient", linked_user=self.recipient)
        Appointment.objects.filter(pk=self.appointment.pk).update(resource=resource)

    def test_own_end_replay_preserves_other_doctor_booking(self):
        item = self.active()
        before = Appointment.objects.values().get(pk=self.appointment.pk)
        ended, replayed = self.end(item)
        self.assertEqual((ended.state, ended.revision, ended.closed_by_id, ended.remaining_responsible_id, replayed),
                         ("ended", 3, self.recipient.pk, None, False))
        self.assertTrue(self.end(item)[1])
        self.assertEqual(Appointment.objects.values().get(pk=self.appointment.pk), before)
        self.assertEqual(MedicalAuditEvent.objects.filter(action="participation_ended", participation=item).count(), 1)

    def test_nonterminal_assigned_booking_blocks_with_concrete_id_without_transition(self):
        item = self.active()
        self.assign_booking()
        with self.assertRaises(InvalidTransition) as caught:
            self.end(item)
        self.assertEqual(caught.exception.errors["obligations"]["appointments"], {"count": 1, "ids": [self.appointment.pk]})
        item.refresh_from_db()
        self.assertEqual((item.state, item.revision), ("active", 2))
        self.assertFalse(CRMCommandIdempotency.objects.filter(action="medical.participation.end_own").exists())
        Appointment.objects.filter(pk=self.appointment.pk).update(status="cancelled")
        self.end(item)

    def test_draft_encounter_remains_an_obligation_after_booking_is_terminal(self):
        item = self.active()
        self.assign_booking()
        record = DentalMedicalRecord.objects.create(business=self.business, patient=self.patient,
            number="SYNTHETIC-END", opened_by=self.recipient)
        encounter = MedicalEncounter.objects.create(business=self.business, patient=self.patient, record=record,
            appointment=self.appointment, branch=self.first, primary_clinician=self.target)
        Appointment.objects.filter(pk=self.appointment.pk).update(status="completed")
        with self.assertRaises(InvalidTransition) as caught:
            self.end(item)
        self.assertEqual(caught.exception.errors["obligations"]["encounters"], {"count": 1, "ids": [encounter.pk]})

    def test_role_branch_and_owner_denials_apply_also_to_replay(self):
        item = self.active()
        for actor in (self.owner, self.doctor):
            with self.subTest(actor=actor.pk), self.assertRaises(PermissionDenied):
                self.end(item, actor=actor)
        self.target_role.branches.clear()
        with self.assertRaises(PermissionDenied):
            self.end(item)
        self.target_role.branches.add(self.first)
        self.end(item)
        MedicalRoleAssignment.objects.filter(pk=self.target_role.pk).update(revoked_at=timezone.now())
        with self.assertRaises(PermissionDenied):
            self.end(item)

    def test_stale_revision_and_audit_failure_roll_back(self):
        item = self.active()
        with self.assertRaises(InvalidTransition):
            self.end(item, expected_revision=1)
        with patch("apps.medical.audit.MedicalAuditEvent.objects.create", side_effect=DatabaseError("synthetic")):
            with self.assertRaises(MedicalAuditUnavailable):
                self.end(item)
        item.refresh_from_db()
        self.assertEqual((item.state, item.revision, item.closed_at), ("active", 2, None))
        self.assertFalse(CRMCommandIdempotency.objects.filter(action="medical.participation.end_own").exists())

    def test_foreign_participation_cannot_be_closed_under_current_patient(self):
        foreign = Business.objects.create(owner=self.owner, name="Foreign", slug="own-end-foreign")
        patient = PatientProfile.objects.create(business=foreign,
            client=Client.objects.create(business=foreign, full_name="Synthetic foreign"), created_by=self.owner)
        member = BusinessMember.objects.create(business=foreign, user=self.recipient)
        accepted_at = timezone.now()
        item = TreatmentParticipation.objects.create(patient=patient, member=member,
            branch=Branch.objects.create(business=foreign, name="Foreign branch"), proposed_by=self.owner,
            state="active", proposed_at=accepted_at, accepted_at=accepted_at)
        with self.assertRaises(PermissionDenied):
            self.end(item, expected_revision=1)
        item.refresh_from_db()
        self.assertEqual(item.state, "active")

    def test_past_unresolved_booking_is_not_silently_completed_and_reassignment_removes_obligation(self):
        item = self.active()
        self.assign_booking()
        Appointment.objects.filter(pk=self.appointment.pk).update(start_at=timezone.now() - timedelta(days=2),
            end_at=timezone.now() - timedelta(days=1))
        with self.assertRaises(InvalidTransition):
            self.end(item)
        Appointment.objects.filter(pk=self.appointment.pk).update(resource=self.staff)
        self.end(item)

    def test_missing_update_and_inactive_member_do_not_end_participation(self):
        item = self.active()
        RolePermission.objects.filter(business_role=self.role, resource="medical_participation", action="update").update(is_allowed=False)
        with self.assertRaises(PermissionDenied):
            self.end(item)
        RolePermission.objects.filter(business_role=self.role, resource="medical_participation", action="update").update(is_allowed=True)
        BusinessMember.objects.filter(pk=self.target.pk).update(is_active=False)
        with self.assertRaises(PermissionDenied):
            self.end(item)
