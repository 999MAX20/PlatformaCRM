from unittest.mock import patch

from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied

from apps.businesses.models import BusinessMember
from apps.core.domain_errors import InvalidTransition
from apps.scheduling.models import Appointment, Resource
from .assistant_invitations import accept_appointment_assistant
from .models import AppointmentAssistant, MedicalRoleAssignment
from . import tests_assistant_invitations as fixtures
from .tests_patient_services import key


@override_settings(MEDICAL_DATA_KEYS={"test": key(7)}, MEDICAL_DATA_ACTIVE_KEY_ID="test",
                   MEDICAL_IDENTITY_INDEX_KEY=key(8))
class AssistantAcceptanceTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        fixtures.AssistantInvitationTests.setUpTestData.__func__(cls)

    invite = fixtures.AssistantInvitationTests.invite

    def setUp(self):
        self.invitation, _ = self.invite()

    def accept(self, **changes):
        return accept_appointment_assistant(**({"actor": self.assistant, "business_id": self.business.pk,
            "invitation_id": self.invitation.pk, "expected_revision": 1,
            "idempotency_key": "synthetic-acceptance"} | changes))

    def test_acceptance_is_personal_versioned_and_idempotent(self):
        for actor in (self.doctor, self.owner):
            with self.subTest(actor=actor.pk), self.assertRaises(PermissionDenied):
                self.accept(actor=actor)
        accepted, replayed = self.accept()
        self.assertFalse(replayed)
        self.assertEqual((accepted.state, accepted.revision), ("active", 2))
        self.assertIsNotNone(accepted.accepted_at)
        self.assertTrue(self.accept()[1])
        with self.assertRaises(InvalidTransition):
            self.accept(idempotency_key="new-accept")

    def test_stale_revision_and_audit_failure_do_not_accept(self):
        with self.assertRaises(InvalidTransition):
            self.accept(expected_revision=2)
        with patch("apps.medical.assistant_invitations.write_actor_audit_log", side_effect=RuntimeError("synthetic failure")):
            with self.assertRaises(RuntimeError):
                self.accept()
        self.invitation.refresh_from_db()
        self.assertEqual((self.invitation.state, self.invitation.revision, self.invitation.accepted_at), ("pending", 1, None))
        self.assertFalse(self.accept()[1])

    def test_terminal_and_reassigned_appointment_block_acceptance(self):
        for status in ("completed", "cancelled", "no_show"):
            Appointment.objects.filter(pk=self.appointment.pk).update(status=status)
            with self.subTest(status=status), self.assertRaises(PermissionDenied):
                self.accept()
        other = Resource.objects.create(business=self.business, name="Other clinician")
        Appointment.objects.filter(pk=self.appointment.pk).update(status="created", resource=other)
        with self.assertRaises(PermissionDenied):
            self.accept()

    def test_role_branch_and_membership_revocation_block_replay(self):
        self.accept()
        self.assistant_role.branches.clear()
        with self.assertRaises(PermissionDenied):
            self.accept()
        self.assistant_role.branches.add(self.first)
        BusinessMember.objects.filter(pk=self.assistant_member.pk).update(is_active=False)
        with self.assertRaises(PermissionDenied):
            self.accept()
        BusinessMember.objects.filter(pk=self.assistant_member.pk).update(is_active=True)
        MedicalRoleAssignment.objects.filter(pk=self.assistant_role.pk).update(revoked_at=timezone.now())
        with self.assertRaises(PermissionDenied):
            self.accept()

    def test_closed_invitation_and_other_business_are_denied(self):
        from apps.businesses.models import Business
        foreign = Business.objects.create(owner=self.owner, name="Synthetic foreign", slug="assistant-accept-foreign")
        with self.assertRaises(PermissionDenied):
            self.accept(business_id=foreign.pk)
        AppointmentAssistant.objects.filter(pk=self.invitation.pk).update(
            state="revoked", closed_at=timezone.now(), closed_by=self.doctor, revision=2)
        with self.assertRaises(PermissionDenied):
            self.accept()
