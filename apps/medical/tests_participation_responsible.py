from unittest.mock import patch

from django.db import DatabaseError
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.test import APIClient

from apps.businesses.models import Business, BusinessMember, RolePermission
from apps.core.domain_errors import InvalidTransition
from . import tests_participation_closure as fixtures
from .audit import MedicalAuditUnavailable
from .models import MedicalAuditEvent, MedicalRoleAssignment
from .participation_candidates import read_responsible_candidates
from .tests_patient_services import key


@override_settings(MEDICAL_DATA_KEYS={"test": key(7)}, MEDICAL_DATA_ACTIVE_KEY_ID="test",
                   MEDICAL_IDENTITY_INDEX_KEY=key(8))
class ParticipationResponsibleTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        fixtures.ParticipationClosureTests.setUpTestData.__func__(cls)

    propose = fixtures.ParticipationClosureTests.propose
    respond = fixtures.ParticipationClosureTests.respond
    active = fixtures.ParticipationClosureTests.active
    close = fixtures.ParticipationClosureTests.close

    def read(self, item, **overrides):
        return read_responsible_candidates(**(dict(actor=self.doctor, business_id=self.business.pk,
            patient_id=self.patient.pk, participation_id=item.pk) | overrides))

    def test_active_member_selection_matches_closure_and_does_not_require_medical_role(self):
        item = self.active()
        MedicalRoleAssignment.objects.filter(pk=self.target_role.pk).update(revoked_at=timezone.now())
        before = MedicalAuditEvent.objects.count()
        page = self.read(item)
        self.assertIn(self.target.pk, [row["member_id"] for row in page["results"]])
        self.assertEqual(page["participation_revision"], 2)
        self.assertEqual(MedicalAuditEvent.objects.count(), before + 1)
        self.assertEqual(MedicalAuditEvent.objects.latest("pk").participation_revision, 2)
        self.assertEqual(set(page["results"][0]), {"member_id", "name"})
        closed, _ = self.close(item, responsible_member_id=self.target.pk)
        self.assertEqual(closed.remaining_responsible_id, self.target.pk)
        self.target_role.refresh_from_db()
        self.assertIsNotNone(self.target_role.revoked_at)

    def test_inactive_and_platform_members_are_excluded(self):
        item = self.active()
        BusinessMember.objects.filter(pk=self.target.pk).update(is_active=False)
        self.assertNotIn(self.target.pk, [row["member_id"] for row in self.read(item)["results"]])
        BusinessMember.objects.filter(pk=self.target.pk).update(is_active=True)
        for changes in ({"is_active": False}, {"is_active": True, "is_superuser": True},
                        {"is_superuser": False, "role": "platform_manager"}):
            type(self.recipient).objects.filter(pk=self.recipient.pk).update(**changes)
            self.assertNotIn(self.target.pk, [row["member_id"] for row in self.read(item)["results"]])

    def test_owner_doctor_wrong_branch_and_revoked_head_are_denied(self):
        item = self.active()
        for actor in (self.owner, self.recipient):
            with self.subTest(actor=actor.pk), self.assertRaises(PermissionDenied):
                self.read(item, actor=actor)
        self.assignment.branches.clear()
        with self.assertRaises(PermissionDenied):
            self.read(item)
        self.assignment.branches.add(self.first)
        RolePermission.objects.filter(business_role=self.role, resource="medical_participation", action="manage").update(is_allowed=False)
        with self.assertRaises(PermissionDenied):
            self.read(item)

    def test_foreign_business_and_mismatched_participation_do_not_leak_candidates(self):
        item = self.active()
        foreign = Business.objects.create(owner=self.owner, name="Other", slug="responsible-other")
        for changes in ({"business_id": foreign.pk}, {"participation_id": item.pk + 1000}):
            with self.subTest(changes=changes), self.assertRaises(PermissionDenied):
                self.read(item, **changes)

    def test_pending_and_closed_do_not_offer_closure_candidates(self):
        item, _ = self.propose()
        with self.assertRaises(InvalidTransition):
            self.read(item)
        self.respond(item)
        self.first.is_active = False
        self.first.save(update_fields=["is_active"])
        self.assertTrue(self.read(item)["results"])
        self.close(item)
        with self.assertRaises(InvalidTransition):
            self.read(item)

    def test_bounded_cursor_search_and_invalid_input(self):
        item = self.active()
        page = self.read(item, limit=1)
        self.assertEqual(len(page["results"]), 1)
        self.assertIsNotNone(page["next_after_member_id"])
        following = self.read(item, limit=1, after_member_id=page["next_after_member_id"])
        self.assertNotEqual(page["results"], following["results"])
        self.assertEqual(self.read(item, query="no-such-synthetic-member")["results"], [])
        for changes in ({"limit": 51}, {"after_member_id": 0}, {"query": "x" * 101}):
            with self.subTest(changes=changes), self.assertRaises(ValidationError):
                self.read(item, **changes)

    def test_audit_failure_and_recipient_disable_between_selection_and_command(self):
        item = self.active()
        before = MedicalAuditEvent.objects.count()
        with patch("apps.medical.participation_candidates.write_patient_audit", side_effect=MedicalAuditUnavailable):
            with self.assertRaises(MedicalAuditUnavailable):
                self.read(item)
        self.assertEqual(MedicalAuditEvent.objects.count(), before)
        self.read(item)
        BusinessMember.objects.filter(pk=self.target.pk).update(is_active=False)
        with self.assertRaises(ValidationError):
            self.close(item, responsible_member_id=self.target.pk)
        item.refresh_from_db()
        self.assertEqual(item.state, "active")

    def test_strict_authenticated_private_http(self):
        item = self.active()
        client = APIClient()
        url = f"/api/medical/participations/{item.pk}/responsible-candidates/"
        scope = {"business_id": self.business.pk, "patient_id": self.patient.pk}
        self.assertIn(client.get(url, scope).status_code, (401, 403))
        client.force_authenticate(self.doctor)
        response = client.get(url, scope)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Cache-Control"], "no-store, private")
        self.assertEqual(response.data["participation_revision"], 2)
        self.assertEqual(client.get(url, scope | {"unknown": 1}).status_code, 400)
        with patch("apps.medical.audit.MedicalAuditEvent.objects.create", side_effect=DatabaseError("synthetic")):
            self.assertEqual(client.get(url, scope).status_code, 503)
