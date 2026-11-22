import base64
import json
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.db import DatabaseError, IntegrityError, connection, transaction
from django.test import TestCase, override_settings
from django.test.utils import CaptureQueriesContext
from django.utils import timezone
from rest_framework.exceptions import NotFound, PermissionDenied, ValidationError

from apps.branches.models import Branch, BranchAccess
from apps.businesses.models import Business, BusinessCapability, BusinessMember, BusinessRole, RolePermission
from apps.clients.models import Client
from apps.core.domain_errors import IdempotencyConflict, InvalidTransition
from apps.core.models import CRMCommandIdempotency
from .audit import MedicalAuditUnavailable
from .identity_crypto import MedicalKeyUnavailable, decrypt_medical_value, iin_digest
from .models import MedicalAuditEvent, MedicalRoleAssignment, PatientProfile
from .patient_services import create_patient_profile


def key(byte):
    return base64.urlsafe_b64encode(bytes([byte]) * 32).decode("ascii")


@override_settings(MEDICAL_DATA_KEYS={"test": key(7)}, MEDICAL_DATA_ACTIVE_KEY_ID="test", MEDICAL_IDENTITY_INDEX_KEY=key(8))
class PatientCreationTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        users = get_user_model()
        cls.owner = users.objects.create_user(username="patient-owner", email="patient-owner@example.test")
        cls.reception = users.objects.create_user(username="patient-reception", email="patient-reception@example.test")
        cls.business = Business.objects.create(owner=cls.owner, name="Synthetic clinic", slug="patient-creation",
            business_type="dentistry", profile_key="dentistry", profile_version=2, profile_assigned_at=timezone.now())
        for module in ("medical_records", "clients", "appointments"):
            BusinessCapability.objects.create(business=cls.business, module_key=module, is_enabled=True)
        cls.member = BusinessMember.objects.create(business=cls.business, user=cls.reception, role="specialist")
        role = BusinessRole.objects.create(business=cls.business, name="Medical reception")
        RolePermission.objects.create(business_role=role, resource="medical_patients", action="create", scope="business")
        cls.assignment = MedicalRoleAssignment.objects.create(member=cls.member, business_role=role,
            kind="reception", granted_by=cls.owner)
        cls.branch = Branch.objects.create(business=cls.business, name="First")
        cls.assignment.branches.add(cls.branch)
        cls.crm_branch = BranchAccess.objects.create(member=cls.member)
        cls.crm_branch.branches.add(cls.branch)
        cls.patient_client = Client.objects.create(business=cls.business, full_name="Synthetic patient", phone="+77000000001")
        cls.relative = Client.objects.create(business=cls.business, full_name="Synthetic relative", phone="+77000000001")

    def create(self, **overrides):
        return create_patient_profile(**{"actor": self.reception, "business_id": self.business.pk,
            "client_id": self.patient_client.pk, "branch_id": self.branch.pk,
            "demographics": {"date_of_birth": "2000-01-02", "sex": "unspecified", "address": "Synthetic private address"},
            "iin": "000000000001", "idempotency_key": "patient-create", **overrides})

    def test_profile_is_unverified_encrypted_and_does_not_duplicate_client(self):
        with CaptureQueriesContext(connection) as queries:
            patient, replayed = self.create(idempotency_key="000000000001")
        self.assertFalse(replayed)
        self.assertEqual(patient.client_id, self.patient_client.pk)
        self.assertEqual(patient.identity_status, "unverified")
        self.assertIsNone(patient.verified_at)
        self.assertIsNone(patient.verified_by_id)
        self.assertEqual(Client.objects.filter(business=self.business).count(), 2)
        fields = {"business_id": self.business.pk, "subject_id": self.patient_client.pk}
        self.assertEqual(decrypt_medical_value(patient.iin_encrypted, purpose="iin", **fields), "000000000001")
        demographics = json.loads(decrypt_medical_value(patient.demographics_encrypted, purpose="demographics", **fields))
        self.assertEqual(demographics["address"], "Synthetic private address")
        sql = "\n".join(row["sql"] for row in queries.captured_queries)
        for plaintext in ("000000000001", "Synthetic private address", "2000-01-02"):
            self.assertNotIn(plaintext, sql)
        command = CRMCommandIdempotency.objects.get(action="medical.patient.create")
        self.assertEqual(command.response_json, {})
        self.assertNotEqual(command.idempotency_key, "000000000001")
        event = MedicalAuditEvent.objects.get(patient=patient)
        self.assertEqual((event.action, event.patient_revision, event.actor_id), ("patient_created", 1, self.reception.pk))

    def test_repeat_is_idempotent_and_changed_payload_conflicts(self):
        first, _ = self.create()
        second, replayed = self.create()
        self.assertTrue(replayed)
        self.assertEqual(first.pk, second.pk)
        self.assertEqual(MedicalAuditEvent.objects.count(), 1)
        with self.assertRaises(IdempotencyConflict):
            self.create(demographics={"address": "Changed address"})
        self.assertEqual(PatientProfile.objects.count(), 1)

    def test_new_key_does_not_overwrite_existing_profile(self):
        patient, _ = self.create()
        with self.assertRaises(InvalidTransition):
            self.create(idempotency_key="another", demographics={})
        patient.refresh_from_db()
        self.assertEqual(patient.revision, 1)
        self.assertEqual(MedicalAuditEvent.objects.count(), 1)

    def test_owner_does_not_get_implicit_patient_creation(self):
        with self.assertRaises(PermissionDenied):
            self.create(actor=self.owner)
        self.assertFalse(PatientProfile.objects.exists())

    def test_revocation_is_checked_before_idempotent_replay(self):
        self.create()
        MedicalRoleAssignment.objects.filter(pk=self.assignment.pk).update(revoked_at=timezone.now())
        with self.assertRaises(PermissionDenied):
            self.create()
        self.assertEqual(MedicalAuditEvent.objects.count(), 1)

    def test_medical_or_crm_branch_revocation_denies_creation(self):
        self.assignment.branches.clear()
        with self.assertRaises(PermissionDenied):
            self.create()
        self.assignment.branches.add(self.branch)
        self.crm_branch.branches.clear()
        with self.assertRaises(PermissionDenied):
            self.create()

    def test_foreign_client_and_branch_are_not_resolved(self):
        foreign = Business.objects.create(owner=self.owner, name="Foreign", slug="patient-foreign")
        client = Client.objects.create(business=foreign, full_name="Foreign synthetic person")
        branch = Branch.objects.create(business=foreign, name="Foreign")
        with self.assertRaises(NotFound):
            self.create(client_id=client.pk)
        with self.assertRaises(PermissionDenied):
            self.create(branch_id=branch.pk)
        self.assertFalse(PatientProfile.objects.exists())

    def test_archived_client_does_not_receive_profile(self):
        Client.objects.filter(pk=self.patient_client.pk).update(is_archived=True)
        with self.assertRaises(NotFound):
            self.create()

    def test_same_family_phone_allows_separate_patients_and_missing_iin(self):
        first, _ = self.create(iin=None, demographics={})
        second, _ = self.create(client_id=self.relative.pk, iin=None, demographics={}, idempotency_key="relative")
        self.assertNotEqual(first.pk, second.pk)
        self.assertIsNone(first.iin_digest)
        self.assertEqual(second.iin_encrypted, "")

    def test_known_verified_iin_blocks_second_profile_without_identity_disclosure(self):
        PatientProfile.objects.create(business=self.business, client=self.relative, created_by=self.reception,
            identity_status="verified", verified_at=timezone.now(), verified_by=self.reception,
            verification_evidence_encrypted="synthetic-ciphertext", iin_encrypted="synthetic-ciphertext",
            iin_digest=iin_digest("000000000001", business_id=self.business.pk))
        with self.assertRaises(InvalidTransition) as raised:
            self.create()
        self.assertNotIn(self.relative.full_name, str(raised.exception))
        self.assertNotIn("000000000001", str(raised.exception))
        self.assertFalse(PatientProfile.objects.filter(client=self.patient_client).exists())

    def test_audit_failure_rolls_back_patient_and_command(self):
        with patch("apps.medical.audit.MedicalAuditEvent.objects.create", side_effect=DatabaseError("Synthetic unavailable journal")):
            with self.assertRaises(MedicalAuditUnavailable):
                self.create()
        self.assertFalse(PatientProfile.objects.exists())
        self.assertFalse(CRMCommandIdempotency.objects.filter(action="medical.patient.create").exists())
        self.assertFalse(MedicalAuditEvent.objects.exists())
        self.assertTrue(Client.objects.filter(pk=self.patient_client.pk).exists())

    def test_missing_key_fails_closed_without_patient_or_command(self):
        with override_settings(MEDICAL_DATA_KEYS=""):
            with self.assertRaises(MedicalKeyUnavailable):
                self.create()
        self.assertFalse(PatientProfile.objects.exists())
        self.assertFalse(CRMCommandIdempotency.objects.filter(action="medical.patient.create").exists())

    def test_invalid_demographics_do_not_leak_input(self):
        for demographics in ({"clinical_notes": "Synthetic secret"}, {"date_of_birth": "9999-12-31"},
                             {"date_of_birth": "2000-99-99"}, {"sex": []}):
            with self.subTest(fields=list(demographics)), self.assertRaises(ValidationError) as raised:
                self.create(demographics=demographics)
            self.assertNotIn("Synthetic secret", str(raised.exception))
        self.assertFalse(PatientProfile.objects.exists())

    def test_medical_permission_does_not_bypass_crm_client_denial(self):
        role = BusinessRole.objects.create(business=self.business, name="No client reads")
        RolePermission.objects.create(business_role=role, resource="clients", action="view", is_allowed=False)
        BusinessMember.objects.filter(pk=self.member.pk).update(business_role=role)
        self.reception.is_superuser = True
        with self.assertRaises(PermissionDenied):
            self.create()
        self.assertFalse(PatientProfile.objects.exists())

    def test_verified_identity_in_other_business_does_not_block_creation(self):
        foreign = Business.objects.create(owner=self.owner, name="Foreign", slug="patient-identity-foreign")
        client = Client.objects.create(business=foreign, full_name="Foreign synthetic person")
        PatientProfile.objects.create(business=foreign, client=client, created_by=self.owner,
            identity_status="verified", verified_at=timezone.now(), verified_by=self.owner,
            verification_evidence_encrypted="synthetic-ciphertext", iin_encrypted="synthetic-ciphertext",
            iin_digest=iin_digest("000000000001", business_id=foreign.pk))
        patient, _ = self.create()
        self.assertEqual(patient.business_id, self.business.pk)

    def test_missing_index_key_cannot_fall_back_to_plain_request_hash(self):
        with override_settings(MEDICAL_IDENTITY_INDEX_KEY=""):
            with self.assertRaises(MedicalKeyUnavailable):
                self.create(iin=None)
        self.assertFalse(PatientProfile.objects.exists())
        self.assertFalse(CRMCommandIdempotency.objects.filter(action="medical.patient.create").exists())

    def test_audit_database_rejects_invalid_action_result_and_version(self):
        patient, _ = self.create()
        base = {"business": self.business, "actor": self.reception, "patient": patient,
                "patient_revision": 1, "action": "patient_created", "result": "success"}
        for override in ({"result": "denied"}, {"action": "arbitrary-text"},
                         {"patient_revision": None}, {"patient_revision": 0}, {"patient": None}):
            with self.subTest(override=override), self.assertRaises(IntegrityError), transaction.atomic():
                MedicalAuditEvent.objects.create(**{**base, **override})
