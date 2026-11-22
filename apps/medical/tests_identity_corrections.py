import copy
import json
from unittest.mock import patch

from django.db import DatabaseError, connection
from django.test import TestCase, override_settings
from django.test.utils import CaptureQueriesContext
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied, ValidationError

from apps.businesses.models import RolePermission
from apps.clients.models import Client
from apps.core.domain_errors import IdempotencyConflict, InvalidTransition
from apps.core.models import CRMCommandIdempotency
from .audit import MedicalAuditUnavailable
from .identity_corrections import correct_patient_administrative_identity
from .identity_crypto import decrypt_medical_value
from .identity_policy import IdentityVerificationUnavailable
from .models import MedicalAuditEvent, PatientIdentityRevision, PatientProfile
from . import tests_identity_verification as verification_fixtures
from . import tests_patient_services as patient_fixtures


@override_settings(MEDICAL_DATA_KEYS={"test": patient_fixtures.key(7)}, MEDICAL_DATA_ACTIVE_KEY_ID="test",
                   MEDICAL_IDENTITY_INDEX_KEY=patient_fixtures.key(8))
class AdministrativeIdentityCorrectionTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        verification_fixtures.IdentityVerificationTests.setUpTestData.__func__(cls)
        RolePermission.objects.create(business_role=cls.assignment.business_role, resource="medical_patients",
                                      action="update", scope="business")

    def setUp(self):
        verification_fixtures.IdentityVerificationTests.setUp(self)
        self.patient, _ = verification_fixtures.IdentityVerificationTests.verify(self)

    def correct(self, **overrides):
        return correct_patient_administrative_identity(**{
            "actor": self.reception, "business_id": self.business.pk, "patient_id": self.patient.pk,
            "branch_id": self.branch.pk, "expected_revision": 2,
            "expected_client_updated_at": self.patient_client.updated_at,
            "full_name": "Corrected synthetic name", "demographics": {"date_of_birth": "2001-02-03", "address": "Corrected private address"},
            "reason": "Private correction reason", "protocol_reference": "synthetic-v1", "method": "synthetic_document",
            "fields": {"check_reference": "Private repeat check"}, "idempotency_key": "administrative-correction", **overrides})

    def test_correction_rechecks_identity_and_preserves_prior_evidence(self):
        old_evidence = self.patient.verification_evidence_encrypted
        old_iin = self.patient.iin_encrypted
        with CaptureQueriesContext(connection) as queries:
            patient, replay = self.correct()
        self.assertFalse(replay)
        self.assertEqual((patient.revision, patient.identity_status, patient.client_id), (3, "verified", self.patient_client.pk))
        self.assertEqual(patient.iin_encrypted, old_iin)
        self.patient_client.refresh_from_db()
        self.assertEqual(self.patient_client.full_name, "Corrected synthetic name")
        history = PatientIdentityRevision.objects.get(patient=patient, revision=2)
        snapshot = json.loads(decrypt_medical_value(history.snapshot_encrypted, business_id=self.business.pk,
            subject_id=patient.pk, purpose="identity_revision_2"))
        self.assertEqual(snapshot["verification_evidence_encrypted"], old_evidence)
        self.assertEqual(snapshot["full_name"], "Synthetic patient")
        self.assertEqual(snapshot["reason"], "Private correction reason")
        evidence = json.loads(decrypt_medical_value(patient.verification_evidence_encrypted,
            business_id=self.business.pk, subject_id=patient.pk, purpose="verification_evidence"))
        self.assertEqual(evidence["fields"]["check_reference"], "Private repeat check")
        self.assertEqual(evidence["full_name"], self.patient_client.full_name)
        self.assertEqual(evidence["client_updated_at"], self.patient_client.updated_at.isoformat())
        sql = "\n".join(row["sql"] for row in queries.captured_queries)
        for value in ("Private repeat check", "Private correction reason", "Corrected private address", "2001-02-03"):
            self.assertNotIn(value, sql)
        self.assertEqual(MedicalAuditEvent.objects.get(action="patient_updated").patient_revision, 3)
        self.assertEqual(CRMCommandIdempotency.objects.get(action="medical.patient.correct_administrative").response_json, {})

    def test_replay_does_not_duplicate_history_and_changed_reason_conflicts(self):
        self.correct()
        patient, replay = self.correct()
        self.assertTrue(replay)
        self.assertEqual(patient.revision, 3)
        self.assertEqual(PatientIdentityRevision.objects.count(), 2)
        with self.assertRaises(IdempotencyConflict):
            self.correct(reason="Different reason")

    def test_reason_recheck_and_valid_name_required(self):
        for values in ({"reason": ""}, {"fields": {}}, {"full_name": " "}, {"full_name": "x" * 256}):
            with self.subTest(values=list(values)), self.assertRaises(ValidationError):
                self.correct(**values)
        self.patient.refresh_from_db()
        self.assertEqual(self.patient.revision, 2)

    def test_stale_patient_and_client_versions_rejected(self):
        with self.assertRaises(InvalidTransition):
            self.correct(expected_revision=1)
        Client.objects.filter(pk=self.patient_client.pk).update(updated_at=timezone.now())
        with self.assertRaises(InvalidTransition):
            self.correct()

    def test_owner_and_reception_without_update_permission_denied(self):
        with self.assertRaises(PermissionDenied):
            self.correct(actor=self.owner)
        RolePermission.objects.filter(business_role=self.assignment.business_role, action="update").delete()
        with self.assertRaises(PermissionDenied):
            self.correct()

    def test_training_revocation_blocks_replay(self):
        self.correct()
        policy = copy.deepcopy(self.policies)
        policy[str(self.business.pk)]["trained_member_ids"] = []
        with override_settings(MEDICAL_IDENTITY_VERIFICATION_POLICIES=policy), self.assertRaises(PermissionDenied):
            self.correct()

    def test_missing_protocol_prevents_correction(self):
        with override_settings(MEDICAL_IDENTITY_VERIFICATION_POLICIES=""), self.assertRaises(IdentityVerificationUnavailable):
            self.correct()

    def test_audit_failure_rolls_back_client_patient_history_and_command(self):
        with patch("apps.medical.audit.MedicalAuditEvent.objects.create", side_effect=DatabaseError("synthetic")):
            with self.assertRaises(MedicalAuditUnavailable):
                self.correct()
        self.patient.refresh_from_db()
        self.patient_client.refresh_from_db()
        self.assertEqual(self.patient.revision, 2)
        self.assertEqual(self.patient_client.full_name, "Synthetic patient")
        self.assertEqual(PatientIdentityRevision.objects.count(), 1)
        self.assertFalse(CRMCommandIdempotency.objects.filter(action="medical.patient.correct_administrative").exists())

    def test_unverified_profile_uses_preliminary_workflow(self):
        PatientProfile.objects.filter(pk=self.patient.pk).update(identity_status="unverified", verified_by=None, verified_at=None)
        with self.assertRaises(InvalidTransition):
            self.correct()

    def test_identifier_fields_cannot_be_smuggled_into_demographics(self):
        for value in ({"iin": "000000000003"}, {"client_id": self.relative.pk}):
            with self.subTest(value=value), self.assertRaises(ValidationError):
                self.correct(demographics=value)

    def test_ordinary_writer_stays_blocked_after_controlled_correction(self):
        self.correct()
        self.patient_client.refresh_from_db()
        self.patient_client.full_name = "Uncontrolled name"
        with self.assertRaises(InvalidTransition):
            self.patient_client.save(update_fields=["full_name"])
