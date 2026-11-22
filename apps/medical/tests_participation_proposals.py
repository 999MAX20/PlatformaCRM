from unittest.mock import patch

from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.exceptions import NotFound, PermissionDenied, ValidationError
from rest_framework.test import APIClient

from apps.branches.models import Branch, BranchAccess
from apps.businesses.models import Business, RolePermission
from apps.clients.models import Client
from apps.scheduling.models import Appointment
from .audit import MedicalAuditUnavailable
from .models import MedicalAuditEvent, MedicalRoleAssignment, PatientProfile, TreatmentParticipation
from .participation_proposals import read_proposal_branches, read_outgoing_proposals
from . import tests_participation_services as fixtures
from .tests_patient_services import key


@override_settings(MEDICAL_DATA_KEYS={"test": key(7)}, MEDICAL_DATA_ACTIVE_KEY_ID="test",
                   MEDICAL_IDENTITY_INDEX_KEY=key(8))
class ProposalWorkspaceTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        fixtures.ParticipationCommandTests.setUpTestData.__func__(cls)
        RolePermission.objects.create(business_role=cls.role, resource="medical_participation",
            action="view", scope="own")
        cls.target_role.branches.add(cls.second)

    propose = fixtures.ParticipationCommandTests.propose
    respond = fixtures.ParticipationCommandTests.respond

    def read(self, service=read_proposal_branches, **overrides):
        return service(**(dict(actor=self.doctor, business_id=self.business.pk, patient_id=self.patient.pk,
            source_appointment_id=self.appointment.pk) | overrides))

    def test_doctor_sees_destinations_without_gaining_target_branch_access(self):
        result = self.read()
        self.assertEqual([row["id"] for row in result["results"]], [self.first.pk, self.second.pk])
        self.assertFalse(self.assignment.branches.filter(pk=self.second.pk).exists())
        self.assertEqual(set(result["results"][0]), {"id", "name"})
        self.assertEqual(MedicalAuditEvent.objects.filter(patient=self.patient, action="read").count(), 1)
        self.propose(branch_id=self.second.pk)

    def test_destination_pagination_and_archived_inactive_foreign_exclusion(self):
        other = Business.objects.create(owner=self.owner, name="Other", slug="proposal-foreign")
        Branch.objects.create(business=other, name="Not a destination")
        Branch.objects.create(business=self.business, name="Archived", archived_at=timezone.now())
        Branch.objects.create(business=self.business, name="Inactive", is_active=False)
        first = self.read(limit=1)
        self.assertEqual(first["next_after_branch_id"], self.first.pk)
        second = self.read(limit=1, after_branch_id=first["next_after_branch_id"])
        self.assertEqual(second, {"results": [{"id": self.second.pk, "name": self.second.name}],
                                  "next_after_branch_id": None})

    def test_head_without_source_is_restricted_by_both_branch_grants(self):
        MedicalRoleAssignment.objects.filter(pk=self.assignment.pk).update(kind="head")
        BranchAccess.objects.filter(member=self.member).update(all_branches=False)
        self.crm_grant.branches.add(self.first)
        self.assertEqual([row["id"] for row in self.read(source_appointment_id=None)["results"]], [self.first.pk])
        self.assignment.branches.add(self.second)
        self.assertEqual([row["id"] for row in self.read(source_appointment_id=None)["results"]], [self.first.pk])
        BranchAccess.objects.filter(member=self.member).update(all_branches=True)
        self.assertEqual(len(self.read(source_appointment_id=None)["results"]), 2)

    def test_no_source_wrong_patient_owner_and_foreign_scope_fail(self):
        client = Client.objects.create(business=self.business, full_name="Another synthetic patient")
        patient = PatientProfile.objects.create(business=self.business, client=client, created_by=self.owner)
        for values in ({"source_appointment_id": None}, {"actor": self.owner}, {"patient_id": patient.pk}):
            with self.subTest(values=values), self.assertRaises(PermissionDenied):
                self.read(**values)
        other = Business.objects.create(owner=self.owner, name="Other", slug="proposal-denied")
        with self.assertRaises(PermissionDenied):
            self.read(business_id=other.pk)
        with self.assertRaises(NotFound):
            self.read(patient_id=patient.pk + 1000)

    def test_current_appointment_role_and_create_permission_are_required_for_both_reads(self):
        for service in (read_proposal_branches, read_outgoing_proposals):
            for state in ("cancelled", "completed"):
                Appointment.objects.filter(pk=self.appointment.pk).update(status=state)
                with self.subTest(service=service.__name__, state=state), self.assertRaises(PermissionDenied):
                    self.read(service)
            Appointment.objects.filter(pk=self.appointment.pk).update(status="created")
        MedicalRoleAssignment.objects.filter(pk=self.assignment.pk).update(revoked_at=timezone.now())
        with self.assertRaises(PermissionDenied):
            self.read()
        MedicalRoleAssignment.objects.filter(pk=self.assignment.pk).update(revoked_at=None)
        RolePermission.objects.filter(business_role=self.role, resource="medical_participation", action="create").update(is_allowed=False)
        with self.assertRaises(PermissionDenied):
            self.read()

    def test_active_participation_source_works_and_ended_source_fails(self):
        item, _ = self.propose()
        self.respond(item)
        values = dict(actor=self.recipient, source_appointment_id=None, source_participation_id=item.pk)
        self.assertEqual(len(self.read(**values)["results"]), 2)
        TreatmentParticipation.objects.filter(pk=item.pk).update(state="ended", closed_at=timezone.now(), closed_by=self.doctor)
        for service in (read_proposal_branches, read_outgoing_proposals):
            with self.assertRaises(PermissionDenied):
                self.read(service, **values)

    def test_outgoing_contains_only_own_patient_proposals_and_no_clinical_fields(self):
        first, _ = self.propose()
        second, _ = self.propose(branch_id=self.second.pk, idempotency_key="second")
        self.respond(first)
        result = self.read(read_outgoing_proposals, limit=1)
        self.assertEqual([row["id"] for row in result["results"]], [second.pk])
        self.assertEqual(result["next_before_id"], second.pk)
        older = self.read(read_outgoing_proposals, before_id=second.pk)
        self.assertEqual([row["state"] for row in older["results"]], ["active"])
        self.assertTrue({"iin", "reason", "content", "demographics"}.isdisjoint(older["results"][0]))
        received = self.read(read_outgoing_proposals, actor=self.recipient,
            source_appointment_id=None, source_participation_id=first.pk)
        self.assertEqual(received["results"], [])
        TreatmentParticipation.objects.filter(pk=second.pk).update(proposed_by=self.owner)
        self.assertEqual([row["id"] for row in self.read(read_outgoing_proposals)["results"]], [first.pk])

    def test_read_permission_and_audit_failure_are_fail_closed_including_empty_list(self):
        with patch("apps.medical.participation_proposals.write_patient_audit", side_effect=MedicalAuditUnavailable):
            with self.assertRaises(MedicalAuditUnavailable):
                self.read()
        self.propose()
        before = MedicalAuditEvent.objects.count()
        with patch("apps.medical.participation_reads.write_patient_audit", side_effect=MedicalAuditUnavailable):
            with self.assertRaises(MedicalAuditUnavailable):
                self.read(read_outgoing_proposals)
        self.assertEqual(MedicalAuditEvent.objects.count(), before)
        RolePermission.objects.filter(business_role=self.role, resource="medical_participation", action="view").update(is_allowed=False)
        with self.assertRaises(PermissionDenied):
            self.read(read_outgoing_proposals)

    def test_validation_and_private_strict_http_contract(self):
        for values in ({"source_participation_id": 1}, {"limit": 51}, {"after_branch_id": 0}):
            with self.subTest(values=values), self.assertRaises(ValidationError):
                self.read(**values)
        api = APIClient()
        api.force_authenticate(self.doctor)
        scope = {"business_id": self.business.pk, "patient_id": self.patient.pk,
                 "source_appointment_id": self.appointment.pk}
        for action in ("proposal-branches", "outgoing"):
            url = f"/api/medical/participations/{action}/"
            response = api.get(url, scope)
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response["Cache-Control"], "no-store, private")
            self.assertEqual(api.get(url, scope | {"actor": self.owner.pk}).status_code, 400)
            self.assertEqual(api.get(url, scope | {"source_participation_id": 1}).status_code, 400)
        api.force_authenticate(self.owner)
        self.assertEqual(api.get("/api/medical/participations/proposal-branches/", scope).status_code, 403)
