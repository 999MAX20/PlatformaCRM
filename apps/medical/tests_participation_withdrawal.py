from unittest.mock import patch

from django.db import DatabaseError
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied

from apps.businesses.models import RolePermission
from apps.core.domain_errors import InvalidTransition
from . import tests_participation_services as fixtures
from . import tests_patient_services as crypto_fixtures
from .audit import MedicalAuditUnavailable
from .models import MedicalAuditEvent, MedicalRoleAssignment
from .participation_services import withdraw_treatment_participation


@override_settings(MEDICAL_DATA_KEYS={"test": crypto_fixtures.key(7)}, MEDICAL_DATA_ACTIVE_KEY_ID="test",
                   MEDICAL_IDENTITY_INDEX_KEY=crypto_fixtures.key(8))
class ParticipationWithdrawalTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        fixtures.ParticipationCommandTests.setUpTestData.__func__(cls)

    propose = fixtures.ParticipationCommandTests.propose
    respond = fixtures.ParticipationCommandTests.respond

    def withdraw(self, item, **overrides):
        return withdraw_treatment_participation(**(dict(actor=self.doctor, business_id=self.business.pk,
            patient_id=self.patient.pk, participation_id=item.pk, expected_revision=1,
            idempotency_key="withdrawal") | overrides))

    def test_proposer_withdraws_and_replays_without_erasing_reason(self):
        item, _ = self.propose()
        encrypted_reason = item.reason_encrypted
        closed, replayed = self.withdraw(item)
        self.assertEqual((closed.state, closed.revision, closed.closed_by_id, replayed),
                         ("withdrawn", 2, self.doctor.pk, False))
        self.assertEqual(closed.reason_encrypted, encrypted_reason)
        self.assertIsNone(closed.accepted_at)
        self.assertTrue(self.withdraw(item)[1])
        self.assertEqual(MedicalAuditEvent.objects.filter(action="participation_withdrawn").count(), 1)
        with self.assertRaises(InvalidTransition):
            self.respond(item, expected_revision=2)

    def test_acceptance_wins_before_withdrawal_without_ending_active_care(self):
        item, _ = self.propose()
        self.respond(item)
        for revision in (1, 2):
            with self.subTest(revision=revision), self.assertRaises(InvalidTransition):
                self.withdraw(item, expected_revision=revision)
        item.refresh_from_db()
        self.assertEqual(item.state, "active")
        self.assertFalse(MedicalAuditEvent.objects.filter(action="participation_withdrawn").exists())

    def test_stale_revision_does_not_withdraw_pending_proposal(self):
        item, _ = self.propose()
        with self.assertRaises(InvalidTransition):
            self.withdraw(item, expected_revision=2)
        item.refresh_from_db()
        self.assertEqual(item.state, "pending")

    def test_recipient_and_owner_have_no_proposer_override(self):
        item, _ = self.propose()
        for actor in (self.recipient, self.owner):
            with self.subTest(actor=actor.pk), self.assertRaises(PermissionDenied):
                self.withdraw(item, actor=actor)

    def test_scoped_head_can_withdraw_other_proposal_only_with_manage(self):
        item, _ = self.propose()
        MedicalRoleAssignment.objects.filter(pk=self.target_role.pk).update(kind="head")
        with self.assertRaises(PermissionDenied):
            self.withdraw(item, actor=self.recipient)
        RolePermission.objects.create(business_role=self.role, resource="medical_participation", action="manage", scope="business")
        self.target_role.branches.clear()
        with self.assertRaises(PermissionDenied):
            self.withdraw(item, actor=self.recipient)
        self.target_role.branches.add(self.first)
        closed, _ = self.withdraw(item, actor=self.recipient)
        self.assertEqual(closed.closed_by_id, self.recipient.pk)

    def test_target_revocation_does_not_block_pending_request_cleanup(self):
        item, _ = self.propose()
        MedicalRoleAssignment.objects.filter(pk=self.target_role.pk).update(revoked_at=timezone.now())
        self.withdraw(item)

    def test_actor_revocation_blocks_replay(self):
        item, _ = self.propose()
        self.withdraw(item)
        MedicalRoleAssignment.objects.filter(pk=self.assignment.pk).update(revoked_at=timezone.now())
        with self.assertRaises(PermissionDenied):
            self.withdraw(item)

    def test_audit_failure_rolls_back_withdrawal(self):
        item, _ = self.propose()
        with patch("apps.medical.audit.MedicalAuditEvent.objects.create", side_effect=DatabaseError("synthetic")):
            with self.assertRaises(MedicalAuditUnavailable):
                self.withdraw(item)
        item.refresh_from_db()
        self.assertEqual((item.state, item.revision, item.closed_at), ("pending", 1, None))
        self.assertEqual(MedicalAuditEvent.objects.count(), 1)
