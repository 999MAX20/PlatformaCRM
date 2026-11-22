from unittest.mock import patch

from django.test import TestCase, override_settings
from rest_framework.exceptions import PermissionDenied, ValidationError

from apps.core.domain_errors import IdempotencyConflict
from apps.core.idempotency import canonical_request_hash
from apps.core.models import AuditLog, CRMCommandIdempotency
from . import tests_role_services as fixtures
from .identity_crypto import MedicalDataUnavailable, MedicalKeyUnavailable
from .models import MedicalRoleAssignment, MedicalRoleRevision
from .role_reads import read_medical_role_history
from .tests_patient_services import key


@override_settings(MEDICAL_DATA_KEYS={"test": key(7)}, MEDICAL_DATA_ACTIVE_KEY_ID="test",
                   MEDICAL_IDENTITY_INDEX_KEY=key(8))
class MedicalRoleBasisTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        fixtures.MedicalRoleServiceTests.setUpTestData.__func__(cls)

    define = fixtures.MedicalRoleServiceTests.define
    assign = fixtures.MedicalRoleServiceTests.assign
    revoke = fixtures.MedicalRoleServiceTests.revoke

    def history(self, **kwargs):
        return read_medical_role_history(**({"actor": self.owner, "business_id": self.business.pk,
            "member_id": self.member.pk} | kwargs))

    def test_new_assignment_and_revocation_require_reason(self):
        role, _ = self.define()
        for reason in ("", " \n", None, 1, "x" * 2001):
            with self.subTest(reason=reason), self.assertRaises(ValidationError):
                self.assign(role, reason=reason)
        self.assertFalse(MedicalRoleAssignment.objects.exists())
        assignment, _ = self.assign(role)
        for reason in ("", " \n", None, 1, "x" * 2001):
            with self.subTest(reason=reason), self.assertRaises(ValidationError):
                self.revoke(assignment, reason=reason)
        assignment.refresh_from_db()
        self.assertIsNone(assignment.revoked_at)
        self.assertEqual(MedicalRoleRevision.objects.count(), 1)

    def test_reasons_are_encrypted_and_history_retains_grant_revoke_regrant(self):
        role, _ = self.define()
        assignment, _ = self.assign(role, reason="  Synthetic private grant\n")
        self.revoke(assignment, reason="Synthetic private revoke")
        self.assign(role, expected_revision=2, idempotency_key="again", reason="Synthetic private regrant")
        rows = self.history()["results"]
        self.assertEqual([r["revision"] for r in rows], [1, 2, 3])
        self.assertEqual([r["action"] for r in rows], ["grant", "revoke", "grant"])
        self.assertEqual(rows[0]["reason"], "  Synthetic private grant\n")
        self.assertEqual(rows[1]["reason"], "Synthetic private revoke")
        for model in (MedicalRoleRevision, AuditLog, CRMCommandIdempotency):
            self.assertNotIn("Synthetic private", str(list(model.objects.values())))
        first = self.history(limit=1)
        self.assertEqual(self.history(limit=1, after_id=first["next_after_id"])["results"][0]["revision"], 2)

    def test_replay_binds_reason_without_repeating_history(self):
        role, _ = self.define()
        assignment, _ = self.assign(role)
        self.assertTrue(self.assign(role)[1])
        with self.assertRaises(IdempotencyConflict):
            self.assign(role, reason="Changed")
        self.revoke(assignment)
        self.assertTrue(self.revoke(assignment)[1])
        with self.assertRaises(IdempotencyConflict):
            self.revoke(assignment, reason="Changed")
        self.assertEqual(MedicalRoleRevision.objects.count(), 2)

    def test_old_receipts_replay_without_inventing_reason(self):
        role, _ = self.define()
        assignment, _ = self.assign(role)
        old = {"member": self.member.pk, "role": role.pk, "branches": [self.branch.pk],
               "all_branches": False, "expected_revision": 0}
        CRMCommandIdempotency.objects.filter(action="medical.role.assign").update(request_hash=canonical_request_hash(old))
        MedicalRoleRevision.objects.all().delete()
        self.assertTrue(self.assign(role, reason="")[1])
        self.assertEqual(self.history()["results"], [])
        self.revoke(assignment)
        CRMCommandIdempotency.objects.filter(action="medical.role.revoke").update(
            request_hash=canonical_request_hash({"member": self.member.pk, "expected_revision": 1}))
        MedicalRoleRevision.objects.all().delete()
        self.assertTrue(self.revoke(assignment, expected_revision=1, reason="")[1])
        self.assertEqual(self.history()["results"], [])

    def test_crypto_failure_rolls_back_assignment_and_revocation(self):
        role, _ = self.define()
        with patch("apps.medical.role_basis.encrypt_medical_value", side_effect=MedicalKeyUnavailable()):
            with self.assertRaises(MedicalKeyUnavailable):
                self.assign(role)
        self.assertFalse(MedicalRoleAssignment.objects.exists())
        self.assertFalse(CRMCommandIdempotency.objects.filter(action="medical.role.assign").exists())
        assignment, _ = self.assign(role)
        with patch("apps.medical.role_basis.encrypt_medical_value", side_effect=MedicalKeyUnavailable()):
            with self.assertRaises(MedicalKeyUnavailable):
                self.revoke(assignment)
        assignment.refresh_from_db()
        self.assertIsNone(assignment.revoked_at)
        self.assertEqual(MedicalRoleRevision.objects.count(), 1)
        self.assertFalse(AuditLog.objects.filter(metadata__kind="medical_role_revoked").exists())

    def test_history_requires_current_owner_and_fails_closed_for_corruption(self):
        role, _ = self.define()
        self.assign(role)
        with self.assertRaises(PermissionDenied):
            self.history(actor=self.employee)
        MedicalRoleRevision.objects.update(reason_encrypted="invalid")
        with self.assertRaises(MedicalDataUnavailable):
            self.history()
