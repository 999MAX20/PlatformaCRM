from unittest.mock import patch

from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied, ValidationError

from apps.businesses.models import Business
from apps.scheduling.models import Appointment
from .assistant_invitations import accept_appointment_assistant
from .assistant_selectors import list_assistant_candidates, list_appointment_assistants, list_my_assistant_invitations
from .models import MedicalRoleAssignment
from . import tests_assistant_invitations as fixtures
from .tests_patient_services import key


@override_settings(MEDICAL_DATA_KEYS={"test": key(7)}, MEDICAL_DATA_ACTIVE_KEY_ID="test",
                   MEDICAL_IDENTITY_INDEX_KEY=key(8))
class AssistantSelectorTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        fixtures.AssistantInvitationTests.setUpTestData.__func__(cls)

    invite = fixtures.AssistantInvitationTests.invite

    def managed(self, service=list_appointment_assistants, **changes):
        return service(**({"actor": self.doctor, "business_id": self.business.pk, "patient_id": self.patient.pk,
                          "appointment_id": self.appointment.pk} | changes))

    def inbox(self, **changes):
        return list_my_assistant_invitations(**({"actor": self.assistant, "business_id": self.business.pk} | changes))

    def test_candidates_reuse_command_eligibility_and_exclude_existing_invitation(self):
        candidates = self.managed(list_assistant_candidates)
        self.assertEqual([row["member_id"] for row in candidates["results"]], [self.assistant_member.pk])
        self.assertEqual(candidates["appointment_updated_at"], self.appointment.updated_at)
        item, _ = self.invite()
        self.assertEqual(self.managed(list_assistant_candidates)["results"], [])
        self.assertEqual([row["id"] for row in self.managed()["results"]], [item.pk])

    def test_candidate_branch_and_role_revocations_are_observed(self):
        self.assistant_role.branches.clear()
        self.assertEqual(self.managed(list_assistant_candidates)["results"], [])
        self.assistant_role.branches.add(self.first)
        MedicalRoleAssignment.objects.filter(pk=self.assistant_role.pk).update(revoked_at=timezone.now())
        self.assertEqual(self.managed(list_assistant_candidates)["results"], [])

    def test_management_requires_primary_or_head_and_current_branch(self):
        for actor in (self.owner, self.assistant):
            with self.subTest(actor=actor.pk), self.assertRaises(PermissionDenied):
                self.managed(actor=actor)
        self.assignment.branches.clear()
        with self.assertRaises(PermissionDenied):
            self.managed()

    def test_inbox_has_no_patient_or_clinical_fields_before_or_after_acceptance(self):
        item, _ = self.invite()
        before = self.inbox()["results"][0]
        self.assertTrue(before["can_accept"])
        self.assertFalse(before["can_open"])
        accept_appointment_assistant(actor=self.assistant, business_id=self.business.pk,
            invitation_id=item.pk, expected_revision=1, idempotency_key="selector-accept")
        after = self.inbox()["results"][0]
        self.assertTrue(after["can_open"])
        self.assertFalse(after["can_accept"])
        allowed = {"id", "state", "revision", "branch_name", "clinician_name", "inviter_name", "start_at",
                   "invited_at", "can_accept", "can_open"}
        self.assertEqual(set(before), allowed)
        self.assertEqual(set(after), allowed)
        self.assertNotIn(self.patient_client.full_name, str(after))

    def test_inbox_is_scoped_to_current_assignment_business_and_branches(self):
        self.invite()
        with self.assertRaises(PermissionDenied):
            self.inbox(actor=self.doctor)
        foreign = Business.objects.create(owner=self.owner, name="Foreign", slug="assistant-selector-foreign")
        with self.assertRaises(PermissionDenied):
            self.inbox(business_id=foreign.pk)
        self.assistant_role.branches.clear()
        self.assertEqual(self.inbox()["results"], [])
        self.assistant_role.branches.add(self.first)
        MedicalRoleAssignment.objects.filter(pk=self.assistant_role.pk).update(revoked_at=timezone.now())
        with self.assertRaises(PermissionDenied):
            self.inbox()

    def test_inbox_pagination_and_closed_invitation_actions(self):
        first, _ = self.invite()
        second_appointment = Appointment.objects.create(business=self.business, client=self.patient_client,
            service=self.service, resource=self.staff, branch=self.first,
            start_at=self.appointment.start_at, end_at=self.appointment.end_at)
        second, _ = self.invite(appointment_id=second_appointment.pk,
            expected_updated_at=second_appointment.updated_at, idempotency_key="second-appointment-invite")
        page = self.inbox(limit=1)
        self.assertEqual(page["results"][0]["id"], second.pk)
        self.assertEqual(self.inbox(before_id=page["next_before_id"], limit=1)["results"][0]["id"], first.pk)
        second_appointment.status = "cancelled"
        second_appointment.save(update_fields=["status"])
        closed = self.inbox(limit=1)["results"][0]
        self.assertEqual((closed["state"], closed["can_accept"], closed["can_open"]), ("ended", False, False))

    def test_invalid_pagination_and_audit_failure_do_not_return_management_data(self):
        for changes in ({"limit": True}, {"limit": 51}, {"before_id": 0}):
            with self.subTest(changes=changes), self.assertRaises(ValidationError):
                self.inbox(**changes)
        with patch("apps.medical.assistant_selectors.write_patient_audit", side_effect=RuntimeError("synthetic failure")):
            with self.assertRaises(RuntimeError):
                self.managed(list_assistant_candidates)
