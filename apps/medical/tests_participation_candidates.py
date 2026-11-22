from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.db import DatabaseError
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.test import APIClient

from apps.branches.models import BranchAccess
from apps.businesses.models import Business, BusinessMember, RolePermission
from . import tests_participation_services as fixtures
from .tests_patient_services import key
from .audit import MedicalAuditUnavailable
from .models import MedicalAuditEvent, MedicalRoleAssignment
from .participation_candidates import read_proposal_candidates


@override_settings(MEDICAL_DATA_KEYS={"test": key(7)}, MEDICAL_DATA_ACTIVE_KEY_ID="test",
                   MEDICAL_IDENTITY_INDEX_KEY=key(8))
class ParticipationCandidateTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        fixtures.ParticipationCommandTests.setUpTestData.__func__(cls)
        cls.recipient.full_name = "Synthetic recipient"
        cls.recipient.save(update_fields=["full_name"])

    propose = fixtures.ParticipationCommandTests.propose
    respond = fixtures.ParticipationCommandTests.respond

    def read(self, **overrides):
        return read_proposal_candidates(**(dict(actor=self.doctor, business_id=self.business.pk,
            patient_id=self.patient.pk, branch_id=self.first.pk, source_appointment_id=self.appointment.pk) | overrides))

    def test_candidates_match_command_and_exclude_self_open_and_inactive(self):
        result = self.read()
        self.assertEqual(result, {"results": [{"member_id": self.target.pk, "name": "Synthetic recipient"}],
            "patient_revision": 1, "next_after_member_id": None})
        self.assertEqual(MedicalAuditEvent.objects.filter(action="read").count(), 1)
        item, _ = self.propose()
        self.assertEqual(self.read()["results"], [])
        self.respond(item, decision="decline")
        self.assertEqual(len(self.read()["results"]), 1)
        BusinessMember.objects.filter(pk=self.target.pk).update(is_active=False)
        self.assertEqual(self.read()["results"], [])

    def test_recipient_current_role_approve_and_branch_are_rechecked(self):
        self.target_role.branches.clear()
        self.assertEqual(self.read()["results"], [])
        self.target_role.branches.add(self.first)
        BranchAccess.objects.filter(member=self.target).update(all_branches=False)
        self.assertEqual(self.read()["results"], [])
        BranchAccess.objects.filter(member=self.target).update(all_branches=True)
        RolePermission.objects.filter(business_role=self.role, resource="medical_participation", action="approve").update(is_allowed=False)
        self.assertEqual(self.read()["results"], [])
        RolePermission.objects.filter(business_role=self.role, resource="medical_participation", action="approve").update(is_allowed=True)
        self.assertEqual(len(self.read()["results"]), 1)
        MedicalRoleAssignment.objects.filter(pk=self.target_role.pk).update(revoked_at=timezone.now())
        self.assertEqual(self.read()["results"], [])
        with self.assertRaises(PermissionDenied):
            self.propose()

    def test_doctor_cross_branch_uses_source_and_recipient_scope_not_extra_actor_grant(self):
        self.target_role.branches.add(self.second)
        self.assertEqual(self.read(branch_id=self.second.pk)["results"][0]["member_id"], self.target.pk)
        self.propose(branch_id=self.second.pk)
        self.assertFalse(self.assignment.branches.filter(pk=self.second.pk).exists())
        with self.assertRaises(PermissionDenied):
            self.read(source_appointment_id=None)

    def test_head_without_source_is_limited_to_its_branch_and_owner_is_denied(self):
        MedicalRoleAssignment.objects.filter(pk=self.assignment.pk).update(kind="head")
        self.assertEqual(len(self.read(source_appointment_id=None)["results"]), 1)
        with self.assertRaises(PermissionDenied):
            self.read(source_appointment_id=None, branch_id=self.second.pk)
        with self.assertRaises(PermissionDenied):
            self.read(actor=self.owner)

    def test_cancellation_and_current_create_permission_block_lookup(self):
        from apps.scheduling.models import Appointment
        Appointment.objects.filter(pk=self.appointment.pk).update(status="cancelled")
        with self.assertRaises(PermissionDenied):
            self.read()
        Appointment.objects.filter(pk=self.appointment.pk).update(status="created")
        RolePermission.objects.filter(business_role=self.role, resource="medical_participation", action="create").update(is_allowed=False)
        with self.assertRaises(PermissionDenied):
            self.read()

    def test_empty_scanned_page_retains_cursor_and_search_is_applied_before_pagination(self):
        user = get_user_model().objects.create_user(username="candidate-next", full_name="Next candidate")
        member = BusinessMember.objects.create(business=self.business, user=user, role="specialist")
        assignment = MedicalRoleAssignment.objects.create(member=member, business_role=self.role, kind="doctor", granted_by=self.owner)
        assignment.branches.add(self.first)
        BranchAccess.objects.create(member=member, all_branches=True)
        MedicalRoleAssignment.objects.filter(pk=self.target_role.pk).update(revoked_at=timezone.now())
        first = self.read(limit=1)
        self.assertEqual(first["results"], [])
        self.assertEqual(first["next_after_member_id"], self.target.pk)
        second = self.read(limit=1, after_member_id=first["next_after_member_id"])
        self.assertEqual(second["results"], [{"member_id": member.pk, "name": "Next candidate"}])
        self.assertIsNone(second["next_after_member_id"])
        self.assertEqual(self.read(query="next", limit=1)["results"], second["results"])

    def test_foreign_scope_and_invalid_parameters_are_rejected(self):
        foreign = Business.objects.create(owner=self.owner, name="Other", slug="candidate-other")
        BusinessMember.objects.create(business=foreign, user=self.recipient, role="specialist")
        self.assertEqual([row["member_id"] for row in self.read()["results"]], [self.target.pk])
        with self.assertRaises(PermissionDenied):
            self.read(business_id=foreign.pk)
        for values in ({"limit": 51}, {"after_member_id": 0}, {"query": "x" * 101},
                       {"source_participation_id": 1}):
            with self.subTest(values=values), self.assertRaises(ValidationError):
                self.read(**values)

    def test_audit_failure_does_not_return_results(self):
        with patch("apps.medical.audit.MedicalAuditEvent.objects.create", side_effect=DatabaseError("synthetic")):
            with self.assertRaises(MedicalAuditUnavailable):
                self.read()
        self.assertEqual(MedicalAuditEvent.objects.count(), 0)

    def test_http_private_strict_and_no_key_required_for_read(self):
        api = APIClient()
        api.force_authenticate(self.doctor)
        url = "/api/medical/participations/candidates/"
        scope = {"business_id": self.business.pk, "patient_id": self.patient.pk,
                 "branch_id": self.first.pk, "source_appointment_id": self.appointment.pk}
        response = api.get(url, scope)
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data["results"][0]["member_id"], self.target.pk)
        self.assertEqual(response["Cache-Control"], "no-store, private")
        self.assertEqual(response["Pragma"], "no-cache")
        response = api.get(url, scope | {"is_allowed": True})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response["Cache-Control"], "no-store, private")
        api.force_authenticate(None)
        self.assertEqual(api.get(url, scope).status_code, 401)
