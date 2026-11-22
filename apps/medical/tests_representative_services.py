import copy
import json
from datetime import timedelta, timezone as datetime_timezone
from unittest.mock import patch

from django.db import DatabaseError, connection
from django.test import TestCase, override_settings
from django.test.utils import CaptureQueriesContext
from django.utils import timezone
from rest_framework.exceptions import NotFound, PermissionDenied, ValidationError

from apps.businesses.models import Business, RolePermission
from apps.clients.models import Client
from apps.core.domain_errors import IdempotencyConflict, InvalidTransition
from apps.core.models import CRMCommandIdempotency
from .audit import MedicalAuditUnavailable
from .identity_crypto import MedicalDataUnavailable, MedicalKeyUnavailable, decrypt_medical_value
from .identity_policy import IdentityVerificationUnavailable
from .models import MedicalAuditEvent, PatientRepresentative
from .representative_services import verify_patient_representative, revoke_patient_representative
from .representative_access import assert_representative_authority
from . import tests_patient_services as fixtures


@override_settings(MEDICAL_DATA_KEYS={"test": fixtures.key(7)}, MEDICAL_DATA_ACTIVE_KEY_ID="test",
                   MEDICAL_IDENTITY_INDEX_KEY=fixtures.key(8))
class RepresentativeServiceTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        fixtures.PatientCreationTests.setUpTestData.__func__(cls)
        RolePermission.objects.create(business_role=cls.assignment.business_role, resource="medical_patients",
                                      action="approve", scope="business")

    def setUp(self):
        self.patient, _ = fixtures.PatientCreationTests.create(self)
        self.start = timezone.now()
        self.policies = {str(self.business.pk): {"reference": "synthetic-representation-v1",
            "approval_reference": "synthetic-not-real-approval", "trained_member_ids": [self.member.pk],
            "methods": {"synthetic": {"required_fields": ["basis"], "optional_fields": []}},
            "permissions": ["receive_documents", "give_consent"], "requires_expiry": True}}
        setting = override_settings(MEDICAL_REPRESENTATIVE_POLICIES=self.policies)
        setting.enable()
        self.addCleanup(setting.disable)

    def verify(self, **overrides):
        return verify_patient_representative(**{
            "actor": self.reception, "business_id": self.business.pk, "branch_id": self.branch.pk,
            "patient_id": self.patient.pk, "representative_client_id": self.relative.pk,
            "expected_patient_revision": 1, "expected_client_updated_at": self.relative.updated_at,
            "protocol_reference": "synthetic-representation-v1", "method": "synthetic",
            "fields": {"basis": "Private synthetic authority evidence"}, "permissions": ["receive_documents"],
            "valid_from": self.start, "valid_until": self.start + timedelta(days=1),
            "idempotency_key": "representative-verify", **overrides})

    def revoke(self, relation, **overrides):
        return revoke_patient_representative(**{
            "actor": self.reception, "business_id": self.business.pk, "branch_id": self.branch.pk,
            "patient_id": self.patient.pk, "representative_client_id": self.relative.pk,
            "representative_id": relation.pk, "expected_revision": 1,
            "reason": "Private synthetic revocation", "idempotency_key": "representative-revoke", **overrides})

    def test_verification_encrypts_evidence_without_general_command_or_audit_leak(self):
        with CaptureQueriesContext(connection) as queries:
            relation, replayed = self.verify(idempotency_key="Private synthetic authority evidence")
        self.assertFalse(replayed)
        data = json.loads(decrypt_medical_value(relation.authority_encrypted, business_id=self.business.pk,
                                              subject_id=relation.pk, purpose="representative_authority"))
        self.assertEqual(data["representative_client_id"], self.relative.pk)
        self.assertEqual(data["permissions"], ["receive_documents"])
        self.assertEqual(data["fields"]["basis"], "Private synthetic authority evidence")
        self.assertNotIn("Private synthetic authority evidence", "\n".join(row["sql"] for row in queries))
        event = MedicalAuditEvent.objects.get(action="representative_verified")
        self.assertEqual((event.representative_id, event.representative_revision), (relation.pk, 1))
        self.assertEqual(event.patient_id, self.patient.pk)
        command = CRMCommandIdempotency.objects.get(action="medical.representative.verify")
        self.assertEqual(command.response_json, {})
        self.assertNotEqual(command.idempotency_key, "Private synthetic authority evidence")

    def test_repeat_reuses_link_and_payload_change_conflicts(self):
        relation, _ = self.verify()
        repeated, replayed = self.verify()
        self.assertTrue(replayed)
        self.assertEqual(relation.pk, repeated.pk)
        self.assertEqual(PatientRepresentative.objects.count(), 1)
        with self.assertRaises(IdempotencyConflict):
            self.verify(permissions=["give_consent"])
        self.assertEqual(MedicalAuditEvent.objects.filter(action="representative_verified").count(), 1)

    def test_current_role_and_training_checked_before_replay(self):
        self.verify()
        self.assignment.revoked_at = timezone.now()
        self.assignment.save(update_fields=["revoked_at"])
        with self.assertRaises(PermissionDenied):
            self.verify()
        self.assignment.revoked_at = None
        self.assignment.save(update_fields=["revoked_at"])
        self.policies[str(self.business.pk)]["trained_member_ids"] = []
        with self.assertRaises(PermissionDenied):
            self.verify()

    def test_owner_and_wrong_branch_do_not_gain_authority(self):
        with self.assertRaises(PermissionDenied):
            self.verify(actor=self.owner)
        self.assignment.branches.clear()
        with self.assertRaises(PermissionDenied):
            self.verify()
        self.assertFalse(PatientRepresentative.objects.exists())

    def test_self_and_foreign_person_are_rejected(self):
        with self.assertRaises(ValidationError):
            self.verify(representative_client_id=self.patient_client.pk)
        with self.assertRaises(NotFound):
            self.verify(representative_client_id=self.relative.pk + 9999)

    def test_stale_identity_and_invalid_period_do_not_create_link(self):
        for values in ({"expected_patient_revision": 2},
                       {"expected_client_updated_at": self.relative.updated_at - timedelta(seconds=1)},
                       {"valid_from": self.start - timedelta(days=2), "valid_until": self.start - timedelta(days=1)}):
            with self.subTest(values=values), self.assertRaises(InvalidTransition):
                self.verify(**values)
        with self.assertRaises(ValidationError):
            self.verify(valid_until=self.start)
        self.assertFalse(PatientRepresentative.objects.exists())

    def test_protocol_is_separate_and_missing_or_malformed_is_closed(self):
        with override_settings(MEDICAL_REPRESENTATIVE_POLICIES=""):
            with self.assertRaises(IdentityVerificationUnavailable):
                self.verify()
        for changes in ({"requires_expiry": "yes"}, {"permissions": ["*"]}, {"permissions": []}):
            policies = copy.deepcopy(self.policies)
            policies[str(self.business.pk)].update(changes)
            with override_settings(MEDICAL_REPRESENTATIVE_POLICIES=policies):
                with self.assertRaises(IdentityVerificationUnavailable):
                    self.verify()

    def test_explicit_authority_and_evidence_required(self):
        for values in ({"fields": {}}, {"permissions": []}, {"permissions": ["all_records"]},
                       {"permissions": ["receive_documents", "receive_documents"]}, {"valid_until": None}):
            with self.subTest(values=values), self.assertRaises(ValidationError):
                self.verify(**values)
        with self.assertRaises(InvalidTransition):
            self.verify(protocol_reference="old-protocol")

    def test_audit_failure_rolls_back_verification_and_command(self):
        with patch("apps.medical.audit.MedicalAuditEvent.objects.create", side_effect=DatabaseError):
            with self.assertRaises(MedicalAuditUnavailable):
                self.verify()
        self.assertFalse(PatientRepresentative.objects.exists())
        self.assertFalse(CRMCommandIdempotency.objects.filter(action="medical.representative.verify").exists())

    def test_revocation_preserves_authority_and_is_idempotent_without_old_protocol(self):
        relation, _ = self.verify()
        original = relation.authority_encrypted
        with override_settings(MEDICAL_REPRESENTATIVE_POLICIES=""):
            revoked, replayed = self.revoke(relation)
            repeated, repeated_flag = self.revoke(relation)
        self.assertFalse(replayed)
        self.assertTrue(repeated_flag)
        self.assertEqual((revoked.revision, repeated.revision), (2, 2))
        self.assertEqual(revoked.authority_encrypted, original)
        self.assertIsNotNone(revoked.revoked_at)
        reason = json.loads(decrypt_medical_value(revoked.revocation_encrypted,
            business_id=self.business.pk, subject_id=relation.pk, purpose="representative_revocation"))
        self.assertEqual(reason["reason"], "Private synthetic revocation")
        self.assertEqual(MedicalAuditEvent.objects.get(action="representative_revoked").representative_revision, 2)
        with self.assertRaises(InvalidTransition):
            self.revoke(relation, idempotency_key="new-key", expected_revision=2)

    def test_revocation_works_after_archive_but_not_after_actor_role_revocation(self):
        relation, _ = self.verify()
        self.relative.is_archived = True
        self.relative.save(update_fields=["is_archived"])
        self.revoke(relation)
        self.assignment.revoked_at = timezone.now()
        self.assignment.save(update_fields=["revoked_at"])
        with self.assertRaises(PermissionDenied):
            self.revoke(relation)

    def test_revocation_audit_failure_and_stale_revision_preserve_authority(self):
        relation, _ = self.verify()
        with self.assertRaises(InvalidTransition):
            self.revoke(relation, expected_revision=2)
        with patch("apps.medical.audit.MedicalAuditEvent.objects.create", side_effect=DatabaseError):
            with self.assertRaises(MedicalAuditUnavailable):
                self.revoke(relation)
        relation.refresh_from_db()
        self.assertEqual(relation.revision, 1)
        self.assertIsNone(relation.revoked_at)
        self.assertFalse(CRMCommandIdempotency.objects.filter(action="medical.representative.revoke").exists())

    def authority(self, relation, **overrides):
        return assert_representative_authority(**{"business_id": self.business.pk, "patient_id": self.patient.pk,
            "representative_client_id": self.relative.pk, "representative_id": relation.pk,
            "permission": "receive_documents", **overrides})

    def test_authority_checks_exact_person_patient_business_and_permission(self):
        relation, _ = self.verify()
        self.authority(relation)
        for values in ({"business_id": self.business.pk + 999}, {"patient_id": self.patient.pk + 999},
                       {"representative_client_id": self.patient_client.pk}, {"permission": "give_consent"}):
            with self.subTest(values=values), self.assertRaises(PermissionDenied):
                self.authority(relation, **values)

    def test_authority_closes_at_expiry_and_immediately_after_revocation(self):
        relation, _ = self.verify()
        with patch("apps.medical.representative_access.timezone.now", return_value=relation.valid_until - timedelta(microseconds=1)):
            self.authority(relation)
        with patch("apps.medical.representative_access.timezone.now", return_value=relation.valid_until):
            with self.assertRaises(PermissionDenied):
                self.authority(relation)
        self.revoke(relation)
        with self.assertRaises(PermissionDenied):
            self.authority(relation)

    def test_future_authority_opens_only_at_its_start(self):
        starts = self.start + timedelta(hours=1)
        relation, _ = self.verify(valid_from=starts)
        with self.assertRaises(PermissionDenied):
            self.authority(relation)
        with patch("apps.medical.representative_access.timezone.now", return_value=starts):
            self.authority(relation)

    def test_ciphertext_cannot_be_moved_to_another_relationship(self):
        first, _ = self.verify()
        second, _ = self.verify(idempotency_key="separate-authority", permissions=["give_consent"])
        PatientRepresentative.objects.filter(pk=second.pk).update(authority_encrypted=first.authority_encrypted)
        with self.assertRaises(MedicalDataUnavailable):
            self.authority(second)

    def test_storage_period_cannot_extend_the_authenticated_evidence(self):
        relation, _ = self.verify()
        PatientRepresentative.objects.filter(pk=relation.pk).update(valid_until=relation.valid_until + timedelta(days=1))
        with self.assertRaises(MedicalDataUnavailable):
            self.authority(relation)

    def test_local_offset_dates_preserve_authority_after_database_reload(self):
        local = datetime_timezone(timedelta(hours=5))
        relation, _ = self.verify(valid_from=self.start.astimezone(local),
            valid_until=(self.start + timedelta(days=1)).astimezone(local))
        self.authority(relation)

    def test_existing_foreign_client_and_representation_cannot_cross_business(self):
        other = Business.objects.create(owner=self.owner, name="Other synthetic clinic", slug="rep-other")
        foreign = Client.objects.create(business=other, full_name="Foreign synthetic person")
        with self.assertRaises(NotFound):
            self.verify(representative_client_id=foreign.pk)
        relation, _ = self.verify()
        with self.assertRaises(NotFound):
            self.revoke(relation, representative_client_id=foreign.pk)
        relation.refresh_from_db()
        self.assertIsNone(relation.revoked_at)

    def test_creation_replay_after_revocation_does_not_restore_access(self):
        relation, _ = self.verify()
        self.revoke(relation)
        repeated, replayed = self.verify()
        self.assertTrue(replayed)
        self.assertEqual(repeated.revision, 2)
        self.assertIsNotNone(repeated.revoked_at)
        self.assertEqual(PatientRepresentative.objects.count(), 1)
        with self.assertRaises(PermissionDenied):
            self.authority(repeated)

    def test_unavailable_keys_never_leave_partial_verification_or_revocation(self):
        with override_settings(MEDICAL_DATA_KEYS={}):
            with self.assertRaises(MedicalKeyUnavailable):
                self.verify()
        self.assertFalse(PatientRepresentative.objects.exists())
        relation, _ = self.verify()
        with override_settings(MEDICAL_DATA_KEYS={}):
            with self.assertRaises(MedicalKeyUnavailable):
                self.revoke(relation)
        relation.refresh_from_db()
        self.assertIsNone(relation.revoked_at)
        self.assertEqual(relation.revision, 1)
