from datetime import timedelta
from unittest.mock import patch

from django.db import DatabaseError
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.test import APIClient

from apps.businesses.models import Business, RolePermission
from apps.clients.models import Client
from . import tests_participation_closure as fixtures
from .tests_patient_services import key
from .audit import MedicalAuditUnavailable
from .models import MedicalAuditEvent, MedicalRoleAssignment, PatientProfile, TreatmentParticipation
from .participation_access import assert_treatment_medical_basis
from .participation_reads import (read_participation_invitations, read_managed_participations,
                                 read_own_participations, read_participation_workspace_access,
                                 read_participation_patient_context)


@override_settings(MEDICAL_DATA_KEYS={"test": key(7)}, MEDICAL_DATA_ACTIVE_KEY_ID="test",
                   MEDICAL_IDENTITY_INDEX_KEY=key(8))
class ParticipationReadTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        fixtures.ParticipationClosureTests.setUpTestData.__func__(cls)
        RolePermission.objects.create(business_role=cls.role, resource="medical_participation", action="view", scope="business")

    propose = fixtures.ParticipationClosureTests.propose
    respond = fixtures.ParticipationClosureTests.respond
    close = fixtures.ParticipationClosureTests.close

    def invitations(self, **overrides):
        return read_participation_invitations(**(dict(actor=self.recipient, business_id=self.business.pk) | overrides))

    def managed(self, **overrides):
        return read_managed_participations(**(dict(actor=self.doctor, business_id=self.business.pk, branch_id=self.first.pk) | overrides))

    def test_patient_context_is_head_only_and_resolves_client_without_demographics(self):
        from apps.businesses.models import BusinessMember
        BusinessMember.objects.filter(pk=self.member.pk).update(role="admin")
        scope = dict(actor=self.doctor, business_id=self.business.pk, client_id=self.patient_client.pk, branch_id=self.first.pk)
        self.assertEqual(read_participation_patient_context(**scope), {
            "business_id": self.business.pk, "branch_id": self.first.pk, "patient_id": self.patient.pk})
        self.assertEqual(MedicalAuditEvent.objects.latest("pk").patient_id, self.patient.pk)
        for changes in ({"actor": self.recipient}, {"actor": self.owner}, {"branch_id": self.second.pk}):
            with self.subTest(changes=changes), self.assertRaises(PermissionDenied):
                read_participation_patient_context(**(scope | changes))
        with patch("apps.medical.participation_reads.write_patient_audit", side_effect=MedicalAuditUnavailable):
            with self.assertRaises(MedicalAuditUnavailable):
                read_participation_patient_context(**scope)
        with patch("apps.medical.participation_reads.assert_can", side_effect=PermissionDenied):
            with self.assertRaises(PermissionDenied):
                read_participation_patient_context(**scope)
        client = APIClient()
        client.force_authenticate(self.doctor)
        query = {key: value for key, value in scope.items() if key != "actor"}
        response = client.get("/api/medical/participations/patient-context/", query)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Cache-Control"], "no-store, private")
        self.assertEqual(client.get("/api/medical/participations/patient-context/", query | {"unknown": 1}).status_code, 400)

    def test_patient_context_rejects_foreign_client_and_missing_profile(self):
        from rest_framework.exceptions import NotFound
        from apps.businesses.models import BusinessMember
        BusinessMember.objects.filter(pk=self.member.pk).update(role="admin")
        foreign = Business.objects.create(owner=self.owner, name="Other", slug="participation-context-other")
        for business in (self.business, foreign):
            client = Client.objects.create(business=business, full_name="Synthetic unmapped client")
            with self.assertRaises(NotFound):
                read_participation_patient_context(actor=self.doctor, business_id=self.business.pk,
                    client_id=client.pk, branch_id=self.first.pk)

    def test_workspace_access_uses_current_medical_role_and_branch_permissions(self):
        scope = dict(actor=self.doctor, business_id=self.business.pk)
        result = read_participation_workspace_access(**scope)
        self.assertEqual((result["kind"], result["member_id"]), ("head", self.member.pk))
        self.assertEqual([row["id"] for row in result["branches"]], [self.first.pk])
        self.assertTrue(result["branches"][0]["actions"]["manage"])
        doctor = read_participation_workspace_access(actor=self.recipient, business_id=self.business.pk)
        self.assertFalse(doctor["branches"][0]["actions"]["manage"])
        RolePermission.objects.filter(business_role=self.role, resource="medical_participation", action="approve").update(is_allowed=False)
        self.assertFalse(read_participation_workspace_access(**scope)["branches"][0]["actions"]["approve"])
        MedicalRoleAssignment.objects.filter(pk=self.assignment.pk).update(revoked_at=timezone.now())
        with self.assertRaises(PermissionDenied):
            read_participation_workspace_access(**scope)
        with self.assertRaises(PermissionDenied):
            read_participation_workspace_access(actor=self.owner, business_id=self.business.pk)

    def test_own_list_retains_accepted_and_ended_without_exposing_another_doctors_participation(self):
        item, _ = self.propose()
        scope = dict(actor=self.recipient, business_id=self.business.pk)
        self.assertEqual(read_own_participations(**scope)["results"][0]["state"], "pending")
        self.respond(item)
        self.assertEqual(read_own_participations(**scope)["results"][0]["state"], "active")
        self.assertEqual(read_own_participations(actor=self.doctor, business_id=self.business.pk)["results"], [])
        self.close(item)
        self.assertEqual(read_own_participations(**scope)["results"][0]["state"], "ended")
        self.target_role.branches.clear()
        self.assertEqual(read_own_participations(**scope)["results"], [])

    def test_own_list_audit_failure_rejects_read_and_access_has_no_patient_data(self):
        self.propose()
        with patch("apps.medical.participation_reads.write_patient_audit", side_effect=MedicalAuditUnavailable):
            with self.assertRaises(MedicalAuditUnavailable):
                read_own_participations(actor=self.recipient, business_id=self.business.pk)
        context = read_participation_workspace_access(actor=self.recipient, business_id=self.business.pk)
        self.assertEqual(set(context), {"business_id", "member_id", "kind", "branches"})

    def test_workspace_and_mine_http_are_strict_private_and_deny_owner(self):
        self.propose()
        client = APIClient()
        client.force_authenticate(self.recipient)
        for action in ("workspace-access", "mine"):
            url = f"/api/medical/participations/{action}/"
            response = client.get(url, {"business_id": self.business.pk})
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response["Cache-Control"], "no-store, private")
            self.assertEqual(client.get(url, {"business_id": self.business.pk, "unknown": 1}).status_code, 400)
        client.force_authenticate(self.owner)
        self.assertEqual(client.get("/api/medical/participations/workspace-access/", {"business_id": self.business.pk}).status_code, 403)

    def test_recipient_sees_pending_metadata_without_clinical_basis_or_reasons(self):
        item, _ = self.propose()
        before = MedicalAuditEvent.objects.count()
        page = self.invitations()
        self.assertEqual([row["id"] for row in page["results"]], [item.pk])
        row = page["results"][0]
        self.assertEqual(row["patient_name"], self.patient_client.full_name)
        for field in ("reason", "reason_encrypted", "iin", "demographics", "closure_reason_encrypted"):
            self.assertNotIn(field, row)
        self.assertEqual(MedicalAuditEvent.objects.count(), before + 2)
        self.assertEqual(MedicalAuditEvent.objects.latest("pk").participation_revision, 1)
        with self.assertRaises(PermissionDenied):
            assert_treatment_medical_basis(actor=self.recipient, business=self.business, patient_id=self.patient.pk, participation_id=item.pk)
        self.assertEqual(self.invitations(actor=self.doctor)["results"], [])

    def test_acceptance_removes_invitation_and_head_filters_current_state(self):
        item, _ = self.propose()
        self.respond(item)
        self.assertEqual(self.invitations()["results"], [])
        self.assertEqual(self.managed(state="active")["results"][0]["revision"], 2)
        self.close(item)
        self.assertEqual(self.managed(state="active")["results"], [])
        self.assertEqual(self.managed(state="ended", patient_id=self.patient.pk)["results"][0]["remaining_responsible_id"], self.member.pk)

    def test_incoming_branch_intersection_and_effective_time(self):
        item, _ = self.propose()
        self.target_role.branches.clear()
        self.assertEqual(self.invitations()["results"], [])
        self.target_role.branches.add(self.first)
        from apps.branches.models import BranchAccess
        BranchAccess.objects.filter(member=self.target).update(all_branches=False)
        self.assertEqual(self.invitations()["results"], [])
        BranchAccess.objects.filter(member=self.target).update(all_branches=True)
        TreatmentParticipation.objects.filter(pk=item.pk).update(proposed_at=timezone.now() + timedelta(days=1))
        self.assertEqual(self.invitations()["results"], [])

    def test_head_is_branch_scoped_and_doctor_owner_are_not_head(self):
        self.propose()
        for actor in (self.recipient, self.owner):
            with self.subTest(actor=actor.pk), self.assertRaises(PermissionDenied):
                self.managed(actor=actor)
        with self.assertRaises(PermissionDenied):
            self.managed(branch_id=self.second.pk)
        self.assignment.branches.clear()
        with self.assertRaises(PermissionDenied):
            self.managed()

    def test_role_revocation_and_missing_view_deny_including_empty_list(self):
        self.propose()
        MedicalRoleAssignment.objects.filter(pk=self.target_role.pk).update(revoked_at=timezone.now())
        with self.assertRaises(PermissionDenied):
            self.invitations()
        RolePermission.objects.filter(business_role=self.role, resource="medical_participation", action="view").update(is_allowed=False)
        with self.assertRaises(PermissionDenied):
            self.managed()

    def test_foreign_business_and_corrupt_links_never_expose_patient_name(self):
        item, _ = self.propose()
        foreign = Business.objects.create(owner=self.owner, name="Other", slug="participation-read-other")
        with self.assertRaises(PermissionDenied):
            self.invitations(business_id=foreign.pk)
        client = Client.objects.create(business=foreign, full_name="Foreign patient")
        patient = PatientProfile.objects.create(business=foreign, client=client, created_by=self.owner)
        TreatmentParticipation.objects.filter(pk=item.pk).update(patient=patient)
        self.assertEqual(self.invitations()["results"], [])
        self.assertEqual(self.managed()["results"], [])

    def test_cursor_is_bounded_and_empty_read_is_audited(self):
        first, _ = self.propose()
        self.respond(first, decision="decline", reason="Synthetic decline reason")
        second, _ = self.propose(idempotency_key="second")
        page = self.managed(limit=1)
        self.assertEqual([row["id"] for row in page["results"]], [second.pk])
        self.assertEqual(page["next_before_id"], second.pk)
        older = self.managed(limit=1, before_id=page["next_before_id"])
        self.assertEqual([row["id"] for row in older["results"]], [first.pk])
        self.assertIsNone(older["next_before_id"])
        before = MedicalAuditEvent.objects.count()
        self.assertEqual(self.managed(before_id=first.pk)["results"], [])
        self.assertEqual(MedicalAuditEvent.objects.count(), before + 1)
        for params in ({"limit": 51}, {"limit": True}, {"before_id": 0}, {"state": "unknown"}):
            with self.subTest(params=params), self.assertRaises(ValidationError):
                self.managed(**params)

    def test_audit_outage_returns_no_data_and_rolls_back_collection_event(self):
        self.propose()
        before = MedicalAuditEvent.objects.count()
        with patch("apps.medical.participation_reads.write_patient_audit", side_effect=MedicalAuditUnavailable()):
            with self.assertRaises(MedicalAuditUnavailable):
                self.invitations()
        self.assertEqual(MedicalAuditEvent.objects.count(), before)
        with patch("apps.medical.participation_reads.MedicalAuditEvent.objects.create", side_effect=DatabaseError("synthetic")):
            with self.assertRaises(MedicalAuditUnavailable):
                self.managed(before_id=1)

    def test_http_strict_scope_private_headers_and_role_boundaries(self):
        self.propose()
        api = APIClient()
        root = "/api/medical/participations/"
        api.force_authenticate(self.recipient)
        response = api.get(root + "invitations/", {"business_id": self.business.pk})
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(len(response.data["results"]), 1)
        cases = [("invitations/", {"business_id": self.business.pk, "member_id": self.member.pk}, 400),
                 ("managed/", {"business_id": self.business.pk, "branch_id": self.first.pk}, 403),
                 ("invitations/", {"business_id": self.business.pk, "limit": 51}, 400)]
        for path, scope, status in cases:
            result = api.get(root + path, scope)
            self.assertEqual(result.status_code, status, result.data)
            self.assertEqual(result["Cache-Control"], "no-store, private")
        self.assertEqual(response["Cache-Control"], "no-store, private")
        self.assertEqual(response["Pragma"], "no-cache")
        api.force_authenticate(None)
        response = api.get(root + "invitations/", {"business_id": self.business.pk})
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response["Cache-Control"], "no-store, private")
