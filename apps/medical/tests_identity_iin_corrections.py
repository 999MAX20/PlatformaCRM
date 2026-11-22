import json
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.db import DatabaseError, IntegrityError, connection, transaction
from django.test import TestCase, override_settings
from django.test.utils import CaptureQueriesContext
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied, ValidationError

from apps.branches.models import BranchAccess
from apps.businesses.models import BusinessMember, BusinessRole, RolePermission
from apps.core.domain_errors import IdempotencyConflict, InvalidTransition
from .audit import MedicalAuditUnavailable
from .identity_crypto import decrypt_medical_value
from .identity_iin_corrections import request_iin_correction, decide_iin_correction
from .identity_verification import verify_patient_identity
from .patient_services import create_patient_profile
from .models import DentalMedicalRecord, MedicalRoleAssignment, PatientIdentityCorrection, PatientIdentityRevision
from . import tests_identity_corrections as corrections
from . import tests_patient_services as fixtures


@override_settings(MEDICAL_DATA_KEYS={"test": fixtures.key(7)}, MEDICAL_DATA_ACTIVE_KEY_ID="test",
                   MEDICAL_IDENTITY_INDEX_KEY=fixtures.key(8))
class IINCorrectionTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        corrections.AdministrativeIdentityCorrectionTests.setUpTestData.__func__(cls)
        cls.head = get_user_model().objects.create_user(username="iin-head", email="iin-head@example.test")
        member = BusinessMember.objects.create(business=cls.business, user=cls.head, role="admin")
        BranchAccess.objects.create(member=member, all_branches=True)
        role = BusinessRole.objects.create(business=cls.business, name="Synthetic identity reviewer")
        RolePermission.objects.create(business_role=role, resource="medical_patients", action="approve", scope="business")
        RolePermission.objects.create(business_role=role, resource="medical_patients", action="view", scope="business")
        cls.head_assignment = MedicalRoleAssignment.objects.create(member=member, business_role=role,
            kind="head", all_branches=True, granted_by=cls.owner)

    def setUp(self):
        corrections.AdministrativeIdentityCorrectionTests.setUp(self)

    def request(self, **overrides):
        return request_iin_correction(**dict({"actor": self.reception, "business_id": self.business.pk,
            "patient_id": self.patient.pk, "branch_id": self.branch.pk, "expected_revision": 2,
            "expected_client_updated_at": self.patient_client.updated_at, "iin": "000000000002",
            "reason": "Synthetic private IIN correction", "protocol_reference": "synthetic-v1",
            "method": "synthetic_document", "fields": {"check_reference": "Private repeated check"},
            "idempotency_key": "request-correction"}, **overrides))

    def history(self):
        return DentalMedicalRecord.objects.create(business=self.business, patient=self.patient,
                                                  number="SYNTHETIC-IIN", opened_by=self.head)

    def decide(self, correction, **overrides):
        return decide_iin_correction(**dict({"actor": self.head, "business_id": self.business.pk,
            "correction_id": correction.pk, "approve": True, "reason": "Private clinical review",
            "idempotency_key": "review-correction"}, **overrides))

    def test_without_history_applies_with_repeat_check_and_encrypted_history(self):
        with CaptureQueriesContext(connection) as queries:
            correction, replayed = self.request()
        self.assertFalse(replayed)
        self.assertEqual((correction.state, correction.medical_review_required, correction.applied_revision), ("applied", False, 3))
        self.patient.refresh_from_db()
        self.assertEqual(decrypt_medical_value(self.patient.iin_encrypted, business_id=self.business.pk,
            subject_id=self.patient_client.pk, purpose="iin"), "000000000002")
        self.assertTrue(PatientIdentityRevision.objects.filter(patient=self.patient, revision=2).exists())
        for value in ("000000000002", "Synthetic private IIN correction", "Private repeated check"):
            self.assertNotIn(value, str(list(queries)))
        repeated, replayed = self.request()
        self.assertTrue(replayed)
        self.assertEqual(repeated.pk, correction.pk)
        with self.assertRaises(IdempotencyConflict):
            self.request(reason="Different reason")

    def test_history_requires_head_and_preserves_record_links(self):
        record = self.history()
        correction, _ = self.request()
        self.patient.refresh_from_db()
        self.assertEqual((correction.state, self.patient.revision), ("pending", 2))
        for actor in (self.reception, self.owner):
            with self.subTest(actor=actor.pk), self.assertRaises(PermissionDenied):
                self.decide(correction, actor=actor)
        decided, replayed = self.decide(correction)
        self.assertFalse(replayed)
        self.assertEqual((decided.state, decided.applied_revision), ("applied", 3))
        record.refresh_from_db()
        self.assertEqual(record.patient_id, self.patient.pk)
        self.patient.refresh_from_db()
        evidence = json.loads(decrypt_medical_value(self.patient.verification_evidence_encrypted,
            business_id=self.business.pk, subject_id=self.patient.pk, purpose="verification_evidence"))
        self.assertEqual(evidence["medical_approver_id"], self.head.pk)
        self.assertEqual(evidence["rechecked_by_id"], self.reception.pk)
        _, replayed = self.decide(correction)
        self.assertTrue(replayed)
        self.assertEqual(decided.audit_events.count(), 2)

    def test_rejection_keeps_identity_and_cannot_be_overwritten(self):
        self.history()
        correction, _ = self.request()
        self.decide(correction, approve=False)
        self.patient.refresh_from_db()
        self.assertEqual(self.patient.revision, 2)
        with self.assertRaises(InvalidTransition):
            self.decide(correction, idempotency_key="second-review")

    def test_stale_identity_requires_new_proposal(self):
        self.history()
        correction, _ = self.request()
        corrections.AdministrativeIdentityCorrectionTests.correct(self)
        with self.assertRaises(InvalidTransition):
            self.decide(correction)
        correction.refresh_from_db()
        self.assertEqual(correction.state, "pending")

    def test_request_and_review_require_current_permissions(self):
        self.history()
        correction, _ = self.request()
        self.assignment.revoked_at = timezone.now()
        self.assignment.save(update_fields=["revoked_at"])
        with self.assertRaises(PermissionDenied):
            self.decide(correction)
        self.assertEqual(PatientIdentityCorrection.objects.get(pk=correction.pk).state, "pending")

    def test_invalid_iin_reason_and_unchanged_identity_do_not_write(self):
        for data in ({"iin": "invalid"}, {"reason": ""}, {"fields": {}}):
            with self.subTest(data=list(data)), self.assertRaises(ValidationError):
                self.request(**data)
        with self.assertRaises(InvalidTransition):
            self.request(iin="000000000001")
        self.assertEqual(PatientIdentityCorrection.objects.count(), 0)

    def test_failed_audit_rolls_back_identity_and_proposal(self):
        with patch("apps.medical.audit.MedicalAuditEvent.objects.create", side_effect=DatabaseError("synthetic")):
            with self.assertRaises(MedicalAuditUnavailable):
                self.request()
        self.patient.refresh_from_db()
        self.assertEqual(self.patient.revision, 2)
        self.assertEqual(PatientIdentityCorrection.objects.count(), 0)

    def test_failed_review_audit_preserves_pending_state(self):
        self.history()
        correction, _ = self.request()
        with patch("apps.medical.audit.MedicalAuditEvent.objects.create", side_effect=DatabaseError("synthetic")):
            with self.assertRaises(MedicalAuditUnavailable):
                self.decide(correction)
        self.patient.refresh_from_db(); correction.refresh_from_db()
        self.assertEqual((self.patient.revision, correction.state), (2, "pending"))

    def test_revoked_head_and_missing_branch_scope_cannot_decide(self):
        self.history(); correction, _ = self.request()
        self.head_assignment.all_branches = False
        self.head_assignment.save(update_fields=["all_branches"])
        with self.assertRaises(PermissionDenied):
            self.decide(correction)
        self.head_assignment.all_branches = True
        self.head_assignment.revoked_at = timezone.now()
        self.head_assignment.save(update_fields=["all_branches", "revoked_at"])
        with self.assertRaises(PermissionDenied):
            self.decide(correction)

    def test_changed_verification_protocol_requires_new_recheck(self):
        self.history(); correction, _ = self.request()
        self.policies[str(self.business.pk)]["reference"] = "synthetic-v2"
        with override_settings(MEDICAL_IDENTITY_VERIFICATION_POLICIES=self.policies):
            with self.assertRaises(InvalidTransition):
                self.decide(correction)

    def test_identity_claimed_while_pending_cannot_be_duplicated(self):
        self.history(); correction, _ = self.request()
        other, _ = create_patient_profile(actor=self.reception, business_id=self.business.pk,
            branch_id=self.branch.pk, client_id=self.relative.pk, demographics={},
            iin="000000000002", idempotency_key="other-identity")
        verify_patient_identity(actor=self.reception, business_id=self.business.pk, branch_id=self.branch.pk,
            patient_id=other.pk, expected_revision=1, expected_client_updated_at=self.relative.updated_at,
            protocol_reference="synthetic-v1", method="synthetic_document",
            fields={"check_reference": "Synthetic other identity"}, idempotency_key="verify-other")
        with self.assertRaises(InvalidTransition):
            self.decide(correction)
        self.patient.refresh_from_db()
        self.assertEqual(self.patient.revision, 2)

    def test_applied_state_cannot_omit_applied_revision(self):
        correction, _ = self.request()
        with self.assertRaises(IntegrityError), transaction.atomic():
            PatientIdentityCorrection.objects.filter(pk=correction.pk).update(applied_revision=None)
