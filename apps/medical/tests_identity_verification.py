import copy
import json
from unittest.mock import patch

from django.db import DatabaseError, connection
from django.test import TestCase, override_settings
from django.test.utils import CaptureQueriesContext
from django.utils import timezone
from rest_framework.exceptions import NotFound, PermissionDenied, ValidationError

from apps.businesses.models import RolePermission
from apps.core.domain_errors import IdempotencyConflict, InvalidTransition
from apps.core.models import CRMCommandIdempotency
from .audit import MedicalAuditUnavailable
from .identity_crypto import MedicalDataUnavailable, MedicalKeyUnavailable, decrypt_medical_value
from .identity_policy import IdentityVerificationUnavailable
from .identity_verification import verify_patient_identity
from .models import MedicalAuditEvent, PatientIdentityRevision, PatientProfile
from . import tests_patient_services as fixtures


@override_settings(MEDICAL_DATA_KEYS={"test": fixtures.key(7)}, MEDICAL_DATA_ACTIVE_KEY_ID="test",
                   MEDICAL_IDENTITY_INDEX_KEY=fixtures.key(8))
class IdentityVerificationTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        fixtures.PatientCreationTests.setUpTestData.__func__(cls)
        RolePermission.objects.create(business_role=cls.assignment.business_role, resource="medical_patients",
                                      action="approve", scope="business")

    def setUp(self):
        self.patient, _ = fixtures.PatientCreationTests.create(self)
        self.policies = {str(self.business.pk): {"reference": "synthetic-v1", "approval_reference": "synthetic-only",
            "trained_member_ids": [self.member.pk], "methods": {
                "synthetic_document": {"required_fields": ["check_reference"], "optional_fields": []}}}}
        setting = override_settings(MEDICAL_IDENTITY_VERIFICATION_POLICIES=self.policies)
        setting.enable()
        self.addCleanup(setting.disable)

    def verify(self, **overrides):
        return verify_patient_identity(**{
            "actor": self.reception, "business_id": self.business.pk, "patient_id": self.patient.pk,
            "branch_id": self.branch.pk, "expected_revision": 1, "protocol_reference": "synthetic-v1",
            "expected_client_updated_at": self.patient_client.updated_at,
            "method": "synthetic_document", "fields": {"check_reference": "Private verification record"},
            "idempotency_key": "identity-verify", **overrides})

    def test_verification_is_encrypted_versioned_and_audited(self):
        with CaptureQueriesContext(connection) as queries:
            patient, replay = self.verify(idempotency_key="Private verification record")
        self.assertFalse(replay)
        self.assertEqual((patient.identity_status, patient.revision, patient.verified_by_id), ("verified", 2, self.reception.pk))
        self.assertIsNotNone(patient.verified_at)
        evidence = json.loads(decrypt_medical_value(patient.verification_evidence_encrypted,
            business_id=self.business.pk, subject_id=patient.pk, purpose="verification_evidence"))
        self.assertEqual(evidence["fields"]["check_reference"], "Private verification record")
        self.assertEqual(evidence["source_revision"], 1)
        self.assertEqual(evidence["full_name"], self.patient_client.full_name)
        sql = "\n".join(row["sql"] for row in queries.captured_queries)
        self.assertNotIn("Private verification record", sql)
        self.assertNotIn("000000000001", sql)
        self.assertEqual(PatientIdentityRevision.objects.get(patient=patient).revision, 1)
        self.assertEqual(MedicalAuditEvent.objects.get(action="identity_verified").patient_revision, 2)
        self.assertEqual(CRMCommandIdempotency.objects.get(action="medical.patient.verify").response_json, {})
        self.patient_client.full_name = "Uncontrolled correction"
        with self.assertRaises(InvalidTransition):
            self.patient_client.save(update_fields=["full_name"])

    def test_replay_and_payload_conflict(self):
        self.verify()
        patient, replay = self.verify()
        self.assertTrue(replay)
        self.assertEqual(patient.revision, 2)
        self.assertEqual(PatientIdentityRevision.objects.count(), 1)
        with self.assertRaises(IdempotencyConflict):
            self.verify(fields={"check_reference": "Different evidence"})

    def test_absent_or_invalid_protocol_fails_closed(self):
        for value in ("", "invalid-json", {}, {str(self.business.pk): {}}, {str(self.business.pk): None}):
            with self.subTest(value=value), override_settings(MEDICAL_IDENTITY_VERIFICATION_POLICIES=value):
                with self.assertRaises(IdentityVerificationUnavailable):
                    self.verify()
        self.patient.refresh_from_db()
        self.assertEqual(self.patient.identity_status, "unverified")

    def test_training_removal_blocks_replay(self):
        self.verify()
        policy = copy.deepcopy(self.policies)
        policy[str(self.business.pk)]["trained_member_ids"] = []
        with override_settings(MEDICAL_IDENTITY_VERIFICATION_POLICIES=policy), self.assertRaises(PermissionDenied):
            self.verify()

    def test_protocol_revision_change_requires_reload(self):
        with self.assertRaises(InvalidTransition):
            self.verify(protocol_reference="old-v0")

    def test_protocol_rejects_unapproved_method_or_fields(self):
        for values in ({"method": "telephone"}, {"fields": {}}, {"fields": {"check_reference": " "}},
                       {"fields": {"check_reference": "ok", "extra": "Private"}},
                       {"fields": {"check_reference": "x" * 2001}}):
            with self.subTest(values=list(values)), self.assertRaises(ValidationError):
                self.verify(**values)

    def test_owner_without_medical_assignment_cannot_verify(self):
        with self.assertRaises(PermissionDenied):
            self.verify(actor=self.owner)

    def test_reception_assignment_and_explicit_approve_required(self):
        self.assignment.kind = "doctor"
        self.assignment.save(update_fields=["kind"])
        with self.assertRaises(PermissionDenied):
            self.verify()
        self.assignment.kind = "reception"
        self.assignment.save(update_fields=["kind"])
        RolePermission.objects.filter(business_role=self.assignment.business_role, action="approve").delete()
        with self.assertRaises(PermissionDenied):
            self.verify()

    def test_revoked_role_blocks_replay(self):
        self.verify()
        self.assignment.revoked_at = timezone.now()
        self.assignment.save(update_fields=["revoked_at"])
        with self.assertRaises(PermissionDenied):
            self.verify()

    def test_duplicate_verified_iin_rejected_without_overwrite(self):
        duplicate, _ = fixtures.PatientCreationTests.create(self, client_id=self.relative.pk, idempotency_key="relative")
        self.verify()
        with self.assertRaises(InvalidTransition):
            self.verify(patient_id=duplicate.pk, expected_client_updated_at=self.relative.updated_at, idempotency_key="relative-verify")
        duplicate.refresh_from_db()
        self.assertEqual(duplicate.identity_status, "unverified")

    def test_alternative_protocol_can_verify_without_iin(self):
        patient, _ = fixtures.PatientCreationTests.create(self, client_id=self.relative.pk, iin=None, idempotency_key="relative")
        patient, _ = self.verify(patient_id=patient.pk, expected_client_updated_at=self.relative.updated_at, idempotency_key="relative-verify")
        self.assertEqual(patient.identity_status, "verified")
        self.assertIsNone(patient.iin_digest)

    def test_stale_or_already_verified_identity_rejected(self):
        with self.assertRaises(InvalidTransition):
            self.verify(expected_revision=2)
        self.verify()
        with self.assertRaises(InvalidTransition):
            self.verify(expected_revision=2, idempotency_key="another")

    def test_corrupted_encrypted_identity_or_digest_cannot_be_verified(self):
        original = self.patient.demographics_encrypted
        PatientProfile.objects.filter(pk=self.patient.pk).update(demographics_encrypted="corrupted")
        with self.assertRaises(MedicalDataUnavailable):
            self.verify()
        PatientProfile.objects.filter(pk=self.patient.pk).update(demographics_encrypted=original, iin_digest="b" * 64)
        with self.assertRaises(MedicalDataUnavailable):
            self.verify()
        self.assertFalse(PatientIdentityRevision.objects.exists())

    def test_audit_failure_rolls_back_verification_and_history(self):
        with patch("apps.medical.audit.MedicalAuditEvent.objects.create", side_effect=DatabaseError("synthetic")):
            with self.assertRaises(MedicalAuditUnavailable):
                self.verify()
        self.patient.refresh_from_db()
        self.assertEqual(self.patient.identity_status, "unverified")
        self.assertEqual(self.patient.revision, 1)
        self.assertFalse(PatientIdentityRevision.objects.exists())
        self.assertFalse(CRMCommandIdempotency.objects.filter(action="medical.patient.verify").exists())

    def test_changed_client_cannot_verify_stale_identity(self):
        from apps.clients.models import Client
        newer = Client.objects.get(pk=self.patient_client.pk)
        newer.full_name = "Changed preliminary name"
        newer.save(update_fields=["full_name"])
        self.assertNotEqual(newer.updated_at, self.patient_client.updated_at)
        with self.assertRaises(InvalidTransition):
            self.verify()
        self.patient.refresh_from_db()
        self.assertEqual(self.patient.identity_status, "unverified")
        patient, _ = self.verify(expected_client_updated_at=newer.updated_at)
        self.assertEqual(patient.identity_status, "verified")

    def test_client_snapshot_is_required(self):
        for value in (None, "old", timezone.now().replace(tzinfo=None)):
            with self.subTest(value=value), self.assertRaises(ValidationError):
                self.verify(expected_client_updated_at=value)

    def test_json_environment_configuration_is_supported(self):
        with override_settings(MEDICAL_IDENTITY_VERIFICATION_POLICIES=json.dumps(self.policies)):
            patient, _ = self.verify()
        self.assertEqual(patient.identity_status, "verified")

    def test_foreign_patient_and_branch_are_not_accessible(self):
        from apps.branches.models import Branch
        from apps.businesses.models import Business
        from apps.clients.models import Client
        foreign = Business.objects.create(owner=self.owner, name="Foreign", slug="foreign-verification")
        client = Client.objects.create(business=foreign, full_name="Foreign synthetic patient")
        patient = PatientProfile.objects.create(business=foreign, client=client, created_by=self.owner)
        with self.assertRaises(NotFound):
            self.verify(patient_id=patient.pk, expected_client_updated_at=client.updated_at)
        branch = Branch.objects.create(business=foreign, name="Foreign branch")
        with self.assertRaises(PermissionDenied):
            self.verify(branch_id=branch.pk)
        self.assertFalse(PatientIdentityRevision.objects.exists())

    def test_missing_crypto_key_does_not_verify_or_create_history(self):
        with override_settings(MEDICAL_DATA_KEYS={}), self.assertRaises(MedicalKeyUnavailable):
            self.verify()
        self.patient.refresh_from_db()
        self.assertEqual(self.patient.identity_status, "unverified")
        self.assertFalse(PatientIdentityRevision.objects.exists())

    def test_invalid_protocol_schema_and_training_types_fail_closed(self):
        for key, value in (("trained_member_ids", [True]),
                           ("methods", {"bad-method": {"required_fields": [], "optional_fields": []}}),
                           ("methods", {"synthetic_document": {"required_fields": ["same"], "optional_fields": ["same"]}})):
            policy = copy.deepcopy(self.policies)
            policy[str(self.business.pk)][key] = value
            with self.subTest(key=key), override_settings(MEDICAL_IDENTITY_VERIFICATION_POLICIES=policy):
                with self.assertRaises(IdentityVerificationUnavailable):
                    self.verify()
