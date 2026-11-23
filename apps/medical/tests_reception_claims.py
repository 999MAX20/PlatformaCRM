from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied

from apps.branches.models import BranchAccess
from apps.businesses.models import Business, BusinessMember, BusinessRole, RolePermission
from apps.core.domain_errors import InvalidTransition
from apps.core.models import AuditLog
from .models import MedicalRoleAssignment
from .reception_claims import claim_reception_request
from . import tests_reception_requests as fixtures
from .tests_patient_services import key


def reception_member(business, owner, branch, suffix):
    user = get_user_model().objects.create_user(username=f"synthetic-reception-{suffix}",
        email=f"synthetic-reception-{suffix}@example.test")
    role = BusinessRole.objects.create(business=business, name=f"Synthetic reception {suffix}")
    member = BusinessMember.objects.create(business=business, user=user, role="operator", business_role=role)
    assignment = MedicalRoleAssignment.objects.create(member=member, business_role=role,
        kind="reception", granted_by=owner)
    assignment.branches.add(branch)
    BranchAccess.objects.create(member=member, all_branches=True)
    for resource, action in (("medical_patients", "view"), ("medical_patients", "update"), ("clients", "view")):
        RolePermission.objects.create(business_role=role, resource=resource, action=action,
            scope="business", is_allowed=True)
    return user, member, assignment


@override_settings(MEDICAL_DATA_KEYS={"test": key(7)}, MEDICAL_DATA_ACTIVE_KEY_ID="test",
                   MEDICAL_IDENTITY_INDEX_KEY=key(8))
class ReceptionClaimTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        fixtures.ReceptionCreationTests.setUpTestData.__func__(cls)
        cls.reception, cls.reception_member, cls.reception_assignment = reception_member(
            cls.business, cls.owner, cls.first, "first")
        cls.colleague, cls.colleague_member, cls.colleague_assignment = reception_member(
            cls.business, cls.owner, cls.first, "second")

    request = fixtures.ReceptionCreationTests.request

    def setUp(self):
        self.item, _ = self.request()

    def claim(self, **changes):
        return claim_reception_request(**({"actor": self.reception, "business_id": self.business.pk,
            "request_id": self.item.pk, "expected_revision": 1, "idempotency_key": "claim"} | changes))

    def test_accept_once_and_replay_without_changing_owner_or_audit(self):
        item, replayed = self.claim()
        same, repeated = self.claim()
        self.assertFalse(replayed)
        self.assertTrue(repeated)
        self.assertEqual((item.pk, item.assignee_id, item.state, item.revision),
            (same.pk, self.reception_member.pk, "pending", 2))
        self.assertIsNotNone(item.claimed_at)
        self.assertEqual(AuditLog.objects.filter(entity_type="ReceptionBookingRequest", action="update").count(), 1)
        with self.assertRaises(InvalidTransition):
            self.claim(actor=self.colleague, expected_revision=2)
        item.refresh_from_db()
        self.assertEqual(item.assignee_id, self.reception_member.pk)

    def test_owner_doctor_and_foreign_request_are_denied(self):
        for actor in (self.owner, self.doctor):
            with self.subTest(actor=actor.pk), self.assertRaises(PermissionDenied):
                self.claim(actor=actor)
        foreign = Business.objects.create(owner=self.owner, name="Foreign queue", slug="foreign-queue")
        with self.assertRaises(PermissionDenied):
            self.claim(business_id=foreign.pk)

    def test_medical_and_crm_branch_and_client_scope_are_required(self):
        self.reception_assignment.branches.set([self.second])
        with self.assertRaises(PermissionDenied):
            self.claim()
        self.reception_assignment.branches.set([self.first])
        BranchAccess.objects.filter(member=self.reception_member).update(all_branches=False)
        with self.assertRaises(PermissionDenied):
            self.claim()
        BranchAccess.objects.filter(member=self.reception_member).update(all_branches=True)
        RolePermission.objects.filter(business_role=self.reception_member.business_role,
            resource="clients", action="view").update(scope="own")
        with self.assertRaises(PermissionDenied):
            self.claim()

    def test_revoked_reception_denies_replay(self):
        self.claim()
        self.reception_assignment.revoked_at = timezone.now()
        self.reception_assignment.save(update_fields=["revoked_at"])
        with self.assertRaises(PermissionDenied):
            self.claim()

    def test_audit_error_rolls_back_claim_and_retry_succeeds(self):
        with patch("apps.medical.reception_claims.write_actor_audit_log", side_effect=RuntimeError("synthetic")):
            with self.assertRaises(RuntimeError):
                self.claim()
        self.item.refresh_from_db()
        self.assertIsNone(self.item.assignee_id)
        self.assertEqual(self.item.revision, 1)
        self.assertFalse(self.claim()[1])

    def test_closed_request_cannot_be_claimed(self):
        self.item.state, self.item.closed_at, self.item.closure_reason = "cancelled", timezone.now(), "Synthetic"
        self.item.save()
        with self.assertRaises(InvalidTransition):
            self.claim()
