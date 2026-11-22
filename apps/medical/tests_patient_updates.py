import json
from unittest.mock import patch

from django.db import DatabaseError, connection
from django.test import TestCase, override_settings
from django.test.utils import CaptureQueriesContext
from django.utils import timezone
from rest_framework.exceptions import NotFound, PermissionDenied, ValidationError

from apps.businesses.models import BusinessCapability, RolePermission
from apps.businesses.models import Business
from apps.clients.models import Client
from apps.core.domain_errors import IdempotencyConflict, InvalidTransition
from apps.core.models import CRMCommandIdempotency
from .audit import MedicalAuditUnavailable
from .identity_crypto import MedicalKeyUnavailable, decrypt_medical_value
from .models import MedicalAuditEvent, PatientIdentityRevision, PatientProfile
from .patient_services import update_unverified_patient_profile
from . import tests_patient_services as fixtures


@override_settings(MEDICAL_DATA_KEYS={"test": fixtures.key(7)}, MEDICAL_DATA_ACTIVE_KEY_ID="test", MEDICAL_IDENTITY_INDEX_KEY=fixtures.key(8))
class PatientUpdateTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        fixtures.PatientCreationTests.setUpTestData.__func__(cls)
        RolePermission.objects.create(business_role=cls.assignment.business_role, resource="medical_patients",
                                      action="update", scope="business")

    def setUp(self):
        self.patient, _ = fixtures.PatientCreationTests.create(self)

    def update(self, **overrides):
        return update_unverified_patient_profile(**{
            "actor": self.reception, "business_id": self.business.pk, "patient_id": self.patient.pk,
            "branch_id": self.branch.pk, "expected_revision": 1,
            "demographics": {"address": "Corrected private address"}, "iin": "000000000002",
            "reason": "Private identity correction explanation", "idempotency_key": "patient-update", **overrides})

    def test_update_retains_encrypted_prior_revision_and_audits_new_version(self):
        old_cipher = self.patient.iin_encrypted
        with CaptureQueriesContext(connection) as queries:
            patient, replay = self.update(idempotency_key="000000000002")
        self.assertFalse(replay)
        self.assertEqual((patient.revision, patient.identity_status), (2, "unverified"))
        history = PatientIdentityRevision.objects.get(patient=patient)
        snapshot = json.loads(decrypt_medical_value(history.snapshot_encrypted, business_id=self.business.pk,
            subject_id=patient.pk, purpose="identity_revision_1"))
        self.assertEqual(snapshot["iin_encrypted"], old_cipher)
        self.assertEqual(snapshot["full_name"], self.patient_client.full_name)
        self.assertEqual(history.changed_by_id, self.reception.pk)
        sql = "\n".join(row["sql"] for row in queries.captured_queries)
        for value in ("000000000002", "Corrected private address", "Private identity correction explanation"):
            self.assertNotIn(value, sql)
        self.assertEqual(MedicalAuditEvent.objects.get(action="patient_updated").patient_revision, 2)
        self.assertEqual(CRMCommandIdempotency.objects.get(action="medical.patient.update_unverified").response_json, {})

    def test_replay_and_changed_payload(self):
        self.update()
        patient, replay = self.update()
        self.assertTrue(replay)
        self.assertEqual(patient.revision, 2)
        self.assertEqual(PatientIdentityRevision.objects.count(), 1)
        with self.assertRaises(IdempotencyConflict):
            self.update(reason="Different reason")

    def test_stale_revision_cannot_overwrite_newer_data(self):
        self.update()
        with self.assertRaises(InvalidTransition):
            self.update(idempotency_key="second")
        self.assertEqual(PatientIdentityRevision.objects.count(), 1)

    def test_verified_profile_requires_separate_workflow(self):
        PatientProfile.objects.filter(pk=self.patient.pk).update(identity_status="verified", verified_at=timezone.now(),
            verified_by=self.reception, verification_evidence_encrypted="synthetic-test-evidence")
        with self.assertRaises(InvalidTransition):
            self.update()
        self.assertFalse(PatientIdentityRevision.objects.exists())

    def test_owner_and_missing_update_permission_denied(self):
        with self.assertRaises(PermissionDenied):
            self.update(actor=self.owner)
        RolePermission.objects.filter(action="update", business_role=self.assignment.business_role).delete()
        with self.assertRaises(PermissionDenied):
            self.update()

    def test_role_revocation_denies_even_replay(self):
        self.update()
        self.assignment.revoked_at = timezone.now()
        self.assignment.save(update_fields=["revoked_at"])
        with self.assertRaises(PermissionDenied):
            self.update()

    def test_module_and_branch_revocation(self):
        capability = BusinessCapability.objects.get(business=self.business, module_key="medical_records")
        capability.is_enabled = False
        capability.save()
        from apps.core.domain_errors import ModuleDisabled
        with self.assertRaises(ModuleDisabled):
            self.update()
        capability.is_enabled = True
        capability.save()
        self.crm_branch.branches.clear()
        with self.assertRaises(PermissionDenied):
            self.update()

    def test_missing_or_archived_patient_is_not_found(self):
        with self.assertRaises(NotFound):
            self.update(patient_id=self.patient.pk + 9999)
        self.patient_client.is_archived = True
        self.patient_client.save(update_fields=["is_archived"])
        with self.assertRaises(NotFound):
            self.update()

    def test_reason_and_revision_are_required_without_echoing_private_input(self):
        for values in ({"reason": " "}, {"reason": "x" * 2001}, {"expected_revision": True}):
            with self.subTest(values=list(values)), self.assertRaises(ValidationError):
                self.update(**values)
        self.assertFalse(PatientIdentityRevision.objects.exists())

    def test_iin_can_be_cleared_without_verifying_identity(self):
        patient, _ = self.update(iin=None, demographics={})
        self.assertIsNone(patient.iin_digest)
        self.assertEqual(patient.iin_encrypted, "")
        self.assertEqual(patient.identity_status, "unverified")

    def test_known_verified_identifier_conflict(self):
        other, _ = fixtures.PatientCreationTests.create(self, client_id=self.relative.pk, iin="000000000002",
                                              idempotency_key="relative")
        PatientProfile.objects.filter(pk=other.pk).update(identity_status="verified", verified_at=timezone.now(),
            verified_by=self.reception, verification_evidence_encrypted="synthetic-test-evidence")
        with self.assertRaises(InvalidTransition):
            self.update()
        self.assertFalse(PatientIdentityRevision.objects.exists())

    def test_audit_failure_rolls_back_profile_history_and_command(self):
        with patch("apps.medical.audit.MedicalAuditEvent.objects.create", side_effect=DatabaseError("synthetic")):
            with self.assertRaises(MedicalAuditUnavailable):
                self.update()
        self.patient.refresh_from_db()
        self.assertEqual(self.patient.revision, 1)
        self.assertFalse(PatientIdentityRevision.objects.exists())
        self.assertFalse(CRMCommandIdempotency.objects.filter(action="medical.patient.update_unverified").exists())

    def test_foreign_patient_cannot_be_changed(self):
        foreign = Business.objects.create(owner=self.owner, name="Foreign", slug="foreign-update")
        client = Client.objects.create(business=foreign, full_name="Foreign synthetic patient")
        patient = PatientProfile.objects.create(business=foreign, client=client, created_by=self.owner)
        with self.assertRaises(NotFound):
            self.update(patient_id=patient.pk)
        patient.refresh_from_db()
        self.assertEqual(patient.revision, 1)

    def test_old_replay_returns_current_revision_without_reverting_later_update(self):
        self.update()
        self.update(expected_revision=2, idempotency_key="second", iin=None)
        patient, replay = self.update()
        self.assertTrue(replay)
        self.assertEqual(patient.revision, 3)
        self.assertIsNone(patient.iin_digest)
        self.assertEqual(list(patient.identity_revisions.order_by("revision").values_list("revision", flat=True)), [1, 2])

    @override_settings(MEDICAL_DATA_KEYS={})
    def test_missing_encryption_key_preserves_previous_identity(self):
        with self.assertRaises(MedicalKeyUnavailable):
            self.update()
        self.patient.refresh_from_db()
        self.assertEqual(self.patient.revision, 1)
        self.assertFalse(PatientIdentityRevision.objects.exists())
