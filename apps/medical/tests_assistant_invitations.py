from datetime import timedelta
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied

from apps.branches.models import BranchAccess
from apps.businesses.models import Business, BusinessMember, RolePermission
from apps.core.domain_errors import InvalidTransition
from apps.core.models import AuditLog
from apps.scheduling.models import Appointment
from .assistant_invitations import invite_appointment_assistant
from .models import AppointmentAssistant, MedicalRoleAssignment
from . import tests_assistant_models as fixtures
from .tests_patient_services import key


@override_settings(MEDICAL_DATA_KEYS={"test": key(7)}, MEDICAL_DATA_ACTIVE_KEY_ID="test",
                   MEDICAL_IDENTITY_INDEX_KEY=key(8))
class AssistantInvitationTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        fixtures.AssistantInvitationIntegrityTests.setUpTestData.__func__(cls)
        RolePermission.objects.create(business_role=cls.role, resource="medical_participation",
            action="create", scope="own", is_allowed=True)
        RolePermission.objects.create(business_role=cls.assistant_role.business_role, resource="medical_records",
            action="view", scope="team", is_allowed=True)
        cls.assistant_role.branches.add(cls.first)
        BranchAccess.objects.create(member=cls.assistant_member, all_branches=True)

    def invite(self, **changes):
        return invite_appointment_assistant(**({"actor": self.doctor, "business_id": self.business.pk,
            "patient_id": self.patient.pk, "appointment_id": self.appointment.pk,
            "target_member_id": self.assistant_member.pk, "expected_updated_at": self.appointment.updated_at,
            "idempotency_key": "synthetic-invitation"} | changes))

    def test_primary_invites_once_and_replay_does_not_duplicate_audit(self):
        item, replayed = self.invite()
        same, repeated = self.invite()
        self.assertFalse(replayed)
        self.assertTrue(repeated)
        self.assertEqual(item.pk, same.pk)
        self.assertEqual((item.state, item.primary_clinician_id, item.assignment_id),
                         ("pending", self.member.pk, self.assistant_role.pk))
        self.assertEqual(AuditLog.objects.filter(entity_type="AppointmentAssistant", entity_id=str(item.pk)).count(), 1)
        with self.assertRaises(InvalidTransition):
            self.invite(idempotency_key="another-invitation")

    def test_head_can_invite_for_appointment_in_own_branch(self):
        head = get_user_model().objects.create_user(username="synthetic-separate-head", email="separate-head@example.test")
        member = BusinessMember.objects.create(business=self.business, user=head, role="specialist")
        assignment = MedicalRoleAssignment.objects.create(member=member, business_role=self.role,
            kind="doctor", granted_by=self.owner)
        assignment.branches.add(self.first)
        BranchAccess.objects.create(member=member, all_branches=True)
        with self.assertRaises(PermissionDenied):
            self.invite(actor=head)
        MedicalRoleAssignment.objects.filter(pk=assignment.pk).update(kind="head")
        item, _ = self.invite(actor=head)
        self.assertEqual(item.branch_id, self.first.pk)
        self.assertEqual(item.primary_clinician_id, self.member.pk)
        self.assertEqual(item.invited_by_id, head.pk)
        assignment.branches.set([self.second])
        with self.assertRaises(PermissionDenied):
            self.invite(actor=head)

    def test_owner_and_assistant_cannot_invite(self):
        for actor in (self.owner, self.assistant):
            with self.subTest(actor=actor.pk), self.assertRaises(PermissionDenied):
                self.invite(actor=actor)
        self.assertFalse(AppointmentAssistant.objects.exists())

    def test_source_denial_for_wrong_patient_branch_terminal_and_stale_timestamp(self):
        with self.assertRaises(PermissionDenied):
            self.invite(patient_id=self.patient.pk + 1000)
        with self.assertRaises(InvalidTransition):
            self.invite(expected_updated_at=self.appointment.updated_at - timedelta(seconds=1))
        self.assignment.branches.clear()
        with self.assertRaises(PermissionDenied):
            self.invite()
        self.assignment.branches.add(self.first)
        Appointment.objects.filter(pk=self.appointment.pk).update(status="completed")
        with self.assertRaises(PermissionDenied):
            self.invite()
        self.assertFalse(AppointmentAssistant.objects.exists())

    def test_replay_rechecks_target_role_membership_and_branch(self):
        self.invite()
        self.assistant_role.branches.clear()
        with self.assertRaises(PermissionDenied):
            self.invite()
        self.assistant_role.branches.add(self.first)
        BusinessMember.objects.filter(pk=self.assistant_member.pk).update(is_active=False)
        with self.assertRaises(PermissionDenied):
            self.invite()
        BusinessMember.objects.filter(pk=self.assistant_member.pk).update(is_active=True)
        MedicalRoleAssignment.objects.filter(pk=self.assistant_role.pk).update(revoked_at=timezone.now())
        with self.assertRaises(PermissionDenied):
            self.invite()

    def test_audit_failure_rolls_back_invitation_and_allows_retry(self):
        with patch("apps.medical.assistant_invitations.write_actor_audit_log", side_effect=RuntimeError("synthetic audit failure")):
            with self.assertRaises(RuntimeError):
                self.invite()
        self.assertFalse(AppointmentAssistant.objects.exists())
        self.assertFalse(self.invite()[1])

    def test_foreign_business_or_target_and_revoked_inviter_cannot_use_command(self):
        foreign = Business.objects.create(owner=self.owner, name="Synthetic foreign", slug="assistant-foreign")
        member = BusinessMember.objects.create(business=foreign, user=self.assistant, role="specialist")
        for changes in ({"business_id": foreign.pk}, {"target_member_id": member.pk}):
            with self.subTest(changes=changes), self.assertRaises(PermissionDenied):
                self.invite(**changes)
        self.invite()
        MedicalRoleAssignment.objects.filter(pk=self.assignment.pk).update(revoked_at=timezone.now())
        with self.assertRaises(PermissionDenied):
            self.invite()
