import json
from datetime import timedelta
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.db import DatabaseError
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied

from apps.businesses.models import Business, BusinessMember, RolePermission
from apps.core.domain_errors import IdempotencyConflict, InvalidTransition
from apps.core.models import CRMCommandIdempotency
from . import tests_appointment_access as fixtures
from . import tests_patient_services as crypto_fixtures
from .audit import MedicalAuditUnavailable
from .identity_crypto import decrypt_medical_value
from .models import MedicalAuditEvent, MedicalRoleAssignment, TreatmentParticipation
from .participation_access import assert_treatment_medical_basis
from .participation_services import propose_treatment_participation, respond_treatment_participation


@override_settings(MEDICAL_DATA_KEYS={"test": crypto_fixtures.key(7)}, MEDICAL_DATA_ACTIVE_KEY_ID="test",
                   MEDICAL_IDENTITY_INDEX_KEY=crypto_fixtures.key(8))
class ParticipationCommandTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        fixtures.AppointmentMedicalBasisTests.setUpTestData.__func__(cls)
        cls.recipient = get_user_model().objects.create_user(username="recipient", email="recipient@example.test")
        cls.target = BusinessMember.objects.create(business=cls.business, user=cls.recipient, role="specialist")
        cls.target_role = MedicalRoleAssignment.objects.create(member=cls.target, business_role=cls.role,
            kind="doctor", granted_by=cls.owner)
        cls.target_role.branches.add(cls.first)
        from apps.branches.models import BranchAccess
        BranchAccess.objects.create(member=cls.target, all_branches=True)
        for action in ("create", "approve"):
            RolePermission.objects.create(business_role=cls.role, resource="medical_participation", action=action, scope="own")

    def propose(self, **overrides):
        return propose_treatment_participation(**(dict(actor=self.doctor, business_id=self.business.pk,
            patient_id=self.patient.pk, branch_id=self.first.pk, target_member_id=self.target.pk,
            expected_patient_revision=1, idempotency_key="proposal", reason="Synthetic private reason",
            source_appointment_id=self.appointment.pk) | overrides))

    def respond(self, item, **overrides):
        return respond_treatment_participation(**(dict(actor=self.recipient, business_id=self.business.pk,
            patient_id=self.patient.pk, participation_id=item.pk, expected_revision=1,
            decision="accept", idempotency_key="response") | overrides))

    def test_invitation_acceptance_and_replays_preserve_versions_and_encrypted_reason(self):
        item, replayed = self.propose()
        self.assertFalse(replayed)
        self.assertEqual(item.state, "pending")
        with self.assertRaises(PermissionDenied):
            assert_treatment_medical_basis(actor=self.recipient, business=self.business,
                patient_id=self.patient.pk, participation_id=item.pk)
        self.assertNotIn("Synthetic private reason", item.reason_encrypted)
        decoded = decrypt_medical_value(item.reason_encrypted, business_id=self.business.pk,
            subject_id=item.pk, purpose="participation_proposal")
        self.assertEqual(json.loads(decoded)["reason"], "Synthetic private reason")
        self.assertTrue(self.propose()[1])
        accepted, replayed = self.respond(item)
        self.assertEqual((accepted.state, accepted.revision, replayed), ("active", 2, False))
        self.assertTrue(self.respond(item)[1])
        assert_treatment_medical_basis(actor=self.recipient, business=self.business,
            patient_id=self.patient.pk, participation_id=item.pk)
        self.assertEqual(list(MedicalAuditEvent.objects.order_by("pk").values_list("action", "participation_revision")),
                         [("participation_proposed", 1), ("participation_accepted", 2)])
        self.assertEqual(TreatmentParticipation.objects.count(), 1)
        for row in CRMCommandIdempotency.objects.all():
            self.assertEqual(row.response_json, {})
            self.assertNotIn(row.idempotency_key, ("proposal", "response"))

    def test_decline_is_terminal_and_cannot_be_accepted_with_new_key(self):
        item, _ = self.propose()
        result, _ = self.respond(item, decision="decline", reason="Synthetic decline reason")
        self.assertEqual((result.state, result.closed_by_id), ("declined", self.recipient.pk))
        with self.assertRaises(InvalidTransition):
            self.respond(item, expected_revision=2, idempotency_key="new-response")
        self.assertEqual(MedicalAuditEvent.objects.count(), 2)

    def test_only_recipient_can_accept_not_proposer_or_owner(self):
        item, _ = self.propose()
        for actor in (self.doctor, self.owner):
            with self.subTest(actor=actor.pk), self.assertRaises(PermissionDenied):
                self.respond(item, actor=actor)
        item.refresh_from_db()
        self.assertEqual(item.state, "pending")

    def test_unrelated_doctor_and_self_invitation_are_rejected(self):
        with self.assertRaises(PermissionDenied):
            self.propose(source_appointment_id=None)
        with self.assertRaises(PermissionDenied):
            self.propose(target_member_id=self.member.pk)
        self.assertEqual(TreatmentParticipation.objects.count(), 0)

    def test_head_may_propose_without_appointment_only_in_its_branch_scope(self):
        MedicalRoleAssignment.objects.filter(pk=self.assignment.pk).update(kind="head")
        self.propose(source_appointment_id=None)
        with self.assertRaises(PermissionDenied):
            self.propose(branch_id=self.second.pk, source_appointment_id=None, idempotency_key="other-branch")

    def test_current_participation_can_be_source_without_appointment(self):
        source = TreatmentParticipation.objects.create(patient=self.patient, member=self.member,
            branch=self.first, proposed_by=self.owner, state="active",
            proposed_at=timezone.now() - timedelta(seconds=1), accepted_at=timezone.now())
        self.propose(source_appointment_id=None, source_participation_id=source.pk)
        source.refresh_from_db()
        self.assertEqual(source.state, "active")

    def test_duplicate_and_stale_commands_do_not_overwrite(self):
        with self.assertRaises(InvalidTransition):
            self.propose(expected_patient_revision=2)
        item, _ = self.propose()
        with self.assertRaises(InvalidTransition):
            self.propose(idempotency_key="duplicate")
        with self.assertRaises(InvalidTransition):
            self.respond(item, expected_revision=2)
        with self.assertRaises(IdempotencyConflict):
            self.propose(reason="Changed reason")

    def test_revoked_recipient_cannot_accept_or_replay(self):
        item, _ = self.propose()
        self.respond(item)
        MedicalRoleAssignment.objects.filter(pk=self.target_role.pk).update(revoked_at=timezone.now())
        with self.assertRaises(PermissionDenied):
            self.respond(item)
        with self.assertRaises(PermissionDenied):
            self.propose()

    def test_audit_failure_rolls_back_proposal_and_idempotency(self):
        with patch("apps.medical.audit.MedicalAuditEvent.objects.create", side_effect=DatabaseError("synthetic")):
            with self.assertRaises(MedicalAuditUnavailable):
                self.propose()
        self.assertEqual(TreatmentParticipation.objects.count(), 0)
        self.assertEqual(CRMCommandIdempotency.objects.count(), 0)
        self.assertEqual(MedicalAuditEvent.objects.count(), 0)

    def test_audit_failure_rolls_back_acceptance(self):
        item, _ = self.propose()
        with patch("apps.medical.audit.MedicalAuditEvent.objects.create", side_effect=DatabaseError("synthetic")):
            with self.assertRaises(MedicalAuditUnavailable):
                self.respond(item)
        item.refresh_from_db()
        self.assertEqual((item.state, item.revision), ("pending", 1))
        self.assertEqual(CRMCommandIdempotency.objects.count(), 1)
        self.assertEqual(MedicalAuditEvent.objects.count(), 1)

    def test_cross_branch_proposal_uses_source_basis_and_recipient_branch_authority(self):
        self.target_role.branches.add(self.second)
        item, _ = self.propose(branch_id=self.second.pk)
        accepted, _ = self.respond(item)
        self.assertEqual((accepted.branch_id, accepted.state), (self.second.pk, "active"))
        self.assertFalse(self.assignment.branches.filter(pk=self.second.pk).exists())

    def test_foreign_business_or_target_cannot_receive_proposal(self):
        foreign = Business.objects.create(owner=self.owner, name="Foreign", slug="participation-command-foreign")
        foreign_member = BusinessMember.objects.create(business=foreign, user=self.recipient, role="specialist")
        with self.assertRaises(PermissionDenied):
            self.propose(target_member_id=foreign_member.pk)
        with self.assertRaises(PermissionDenied):
            self.propose(business_id=foreign.pk)
        self.assertEqual(TreatmentParticipation.objects.count(), 0)

    def test_proposal_replay_rechecks_source_booking_after_cancellation(self):
        self.propose()
        from apps.scheduling.models import Appointment
        Appointment.objects.filter(pk=self.appointment.pk).update(status="cancelled")
        with self.assertRaises(PermissionDenied):
            self.propose()
        self.assertEqual(MedicalAuditEvent.objects.count(), 1)
