from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied

from apps.businesses.models import Business, BusinessMember, RolePermission
from apps.scheduling.models import Appointment
from .assistant_access import assert_assistant_appointment_basis
from .models import MedicalRoleAssignment
from . import tests_assistant_acceptance as fixtures
from .tests_patient_services import key


@override_settings(MEDICAL_DATA_KEYS={"test": key(7)}, MEDICAL_DATA_ACTIVE_KEY_ID="test",
                   MEDICAL_IDENTITY_INDEX_KEY=key(8))
class AssistantAccessTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        fixtures.AssistantAcceptanceTests.setUpTestData.__func__(cls)

    setUp = fixtures.AssistantAcceptanceTests.setUp
    invite = fixtures.AssistantAcceptanceTests.invite
    accept = fixtures.AssistantAcceptanceTests.accept

    def basis(self, **changes):
        return assert_assistant_appointment_basis(**({"actor": self.assistant, "business": self.business,
            "patient_id": self.patient.pk, "appointment_id": self.appointment.pk,
            "invitation_id": self.invitation.pk} | changes))

    def test_only_accepted_invitation_is_a_basis_for_exact_appointment(self):
        with self.assertRaises(PermissionDenied):
            self.basis()
        self.accept()
        basis = self.basis()
        self.assertEqual((basis.patient_id, basis.appointment_id), (self.patient.pk, self.appointment.pk))
        for changes in ({"appointment_id": self.appointment.pk + 1}, {"patient_id": self.patient.pk + 1},
                        {"invitation_id": True}, {"actor": self.owner}, {"actor": self.doctor}):
            with self.subTest(changes=list(changes)), self.assertRaises(PermissionDenied):
                self.basis(**changes)

    def test_foreign_business_and_branch_revocation_do_not_use_loaded_context(self):
        self.accept()
        foreign = Business.objects.create(owner=self.owner, name="Foreign", slug="assistant-basis-foreign")
        with self.assertRaises(PermissionDenied):
            self.basis(business=foreign)
        self.assistant_role.branches.clear()
        with self.assertRaises(PermissionDenied):
            self.basis()

    def test_exact_role_membership_and_permission_remain_required(self):
        self.accept()
        BusinessMember.objects.filter(pk=self.assistant_member.pk).update(is_active=False)
        with self.assertRaises(PermissionDenied):
            self.basis()
        BusinessMember.objects.filter(pk=self.assistant_member.pk).update(is_active=True)
        RolePermission.objects.filter(business_role=self.assistant_role.business_role).update(is_allowed=False)
        with self.assertRaises(PermissionDenied):
            self.basis()

    def test_changed_kind_or_revoked_primary_cannot_keep_assistant_basis(self):
        self.accept()
        MedicalRoleAssignment.objects.filter(pk=self.assistant_role.pk).update(kind="doctor")
        with self.assertRaises(PermissionDenied):
            self.basis()
        MedicalRoleAssignment.objects.filter(pk=self.assistant_role.pk).update(kind="assistant")
        MedicalRoleAssignment.objects.filter(pk=self.assignment.pk).update(revoked_at=timezone.now())
        with self.assertRaises(PermissionDenied):
            self.basis()

    def test_sign_issue_export_and_approval_are_denied_even_with_erroneous_rules(self):
        self.accept()
        for action in ("sign", "issue", "export", "approve"):
            RolePermission.objects.create(business_role=self.assistant_role.business_role,
                resource="medical_documents", action=action, scope="business", is_allowed=True)
            with self.subTest(action=action), self.assertRaises(PermissionDenied):
                self.basis(resource="medical_documents", action=action)

    def test_current_invalid_calendar_state_is_denied_even_without_signal(self):
        self.accept()
        Appointment.objects.filter(pk=self.appointment.pk).update(status="cancelled")
        with self.assertRaises(PermissionDenied):
            self.basis()
