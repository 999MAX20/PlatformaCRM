from unittest.mock import patch

from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied

from apps.core.domain_errors import InvalidTransition
from apps.core.models import AuditLog
from .assistant_invitations import revoke_appointment_assistant
from .models import MedicalRoleAssignment
from . import tests_assistant_acceptance as fixtures
from .tests_patient_services import key


@override_settings(MEDICAL_DATA_KEYS={"test": key(7)}, MEDICAL_DATA_ACTIVE_KEY_ID="test",
                   MEDICAL_IDENTITY_INDEX_KEY=key(8))
class AssistantRevokeTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        fixtures.AssistantAcceptanceTests.setUpTestData.__func__(cls)

    setUp = fixtures.AssistantAcceptanceTests.setUp
    invite = fixtures.AssistantAcceptanceTests.invite
    accept = fixtures.AssistantAcceptanceTests.accept

    def revoke(self, **changes):
        return revoke_appointment_assistant(**({"actor": self.doctor, "business_id": self.business.pk,
            "invitation_id": self.invitation.pk, "expected_revision": 1,
            "idempotency_key": "synthetic-revoke"} | changes))

    def test_primary_revokes_pending_once_and_acceptance_is_denied(self):
        item, replayed = self.revoke()
        self.assertFalse(replayed)
        self.assertEqual((item.state, item.closed_by_id, item.revision), ("revoked", self.doctor.pk, 2))
        self.assertTrue(self.revoke()[1])
        self.assertEqual(AuditLog.objects.filter(entity_type="AppointmentAssistant", entity_id=str(item.pk),
            metadata__kind="medical_assistant_revoked").count(), 1)
        with self.assertRaises(PermissionDenied):
            self.accept()

    def test_head_revokes_accepted_without_erasing_acceptance(self):
        accepted, _ = self.accept()
        MedicalRoleAssignment.objects.filter(pk=self.assignment.pk).update(kind="head")
        item, _ = self.revoke(expected_revision=2)
        self.assertEqual(item.accepted_at, accepted.accepted_at)
        self.assertEqual(item.state, "revoked")
        with self.assertRaises(PermissionDenied):
            self.accept()

    def test_owner_assistant_foreign_business_and_branch_are_denied(self):
        for actor in (self.owner, self.assistant):
            with self.subTest(actor=actor.pk), self.assertRaises(PermissionDenied):
                self.revoke(actor=actor)
        with self.assertRaises(PermissionDenied):
            self.revoke(business_id=self.business.pk + 1000)
        self.assignment.branches.clear()
        with self.assertRaises(PermissionDenied):
            self.revoke()

    def test_stale_revision_and_failed_audit_leave_pending(self):
        with self.assertRaises(InvalidTransition):
            self.revoke(expected_revision=2)
        with patch("apps.medical.assistant_invitations.write_actor_audit_log", side_effect=RuntimeError("synthetic failure")):
            with self.assertRaises(RuntimeError):
                self.revoke()
        self.invitation.refresh_from_db()
        self.assertEqual((self.invitation.state, self.invitation.revision), ("pending", 1))

    def test_replay_rechecks_inviter_role(self):
        self.revoke()
        MedicalRoleAssignment.objects.filter(pk=self.assignment.pk).update(revoked_at=timezone.now())
        with self.assertRaises(PermissionDenied):
            self.revoke()
