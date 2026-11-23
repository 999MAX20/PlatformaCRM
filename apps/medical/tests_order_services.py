from unittest.mock import patch

from django.db import DatabaseError
from django.test import TestCase, override_settings
from rest_framework.exceptions import PermissionDenied

from apps.businesses.models import RolePermission
from apps.core.domain_errors import InvalidTransition
from apps.core.idempotency import CRMCommandConflict
from apps.core.models import CRMCommandIdempotency
from . import tests_encounter_services as fixtures
from . import tests_patient_services as crypto_fixtures
from .audit import MedicalAuditUnavailable
from .identity_crypto import MedicalDataUnavailable
from .models import MedicalAuditEvent, MedicalOrder, MedicalOrderRevision
from .order_services import read_order_version, save_order_draft


@override_settings(MEDICAL_DATA_KEYS={"test": crypto_fixtures.key(7)}, MEDICAL_DATA_ACTIVE_KEY_ID="test",
                   MEDICAL_IDENTITY_INDEX_KEY=crypto_fixtures.key(8))
class OrderServiceTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        fixtures.PrimaryEncounterDraftTests.setUpTestData.__func__(cls)
        for action in ("view", "create", "update"):
            RolePermission.objects.create(business_role=cls.role, resource="medical_prescriptions",
                                          action=action, scope="own", is_allowed=True)

    def setUp(self):
        fixtures.PrimaryEncounterDraftTests.setUp(self)

    def save(self, **overrides):
        return save_order_draft(**(dict(actor=self.doctor, business_id=self.business.pk,
            patient_id=self.patient.pk, encounter_id=self.encounter_record.pk, expected_encounter_revision=1,
            expected_patient_revision=self.patient.revision, idempotency_key="synthetic-order",
            content={"kind": "medication", "text": "Synthetic clinical text", "medication": {"name": "Synthetic name"}},
            reason="Synthetic reason") | overrides))

    def read(self, version, **overrides):
        return read_order_version(**(dict(actor=self.doctor, business_id=self.business.pk,
            patient_id=self.patient.pk, version_id=version.pk, appointment_id=self.appointment.pk) | overrides))

    def test_create_read_replay_and_update_preserve_exact_history(self):
        first, replayed = self.save()
        self.assertFalse(replayed)
        original = self.read(first)["content"]
        self.assertEqual(original["medication"]["name"], "Synthetic name")
        self.assertNotIn("Synthetic", first.content_encrypted)
        self.assertNotIn("Synthetic", str(CRMCommandIdempotency.objects.get().__dict__))
        replay, replayed = self.save()
        self.assertTrue(replayed)
        self.assertEqual(replay.pk, first.pk)
        second, _ = self.save(order_id=first.order_id, expected_order_revision=1, idempotency_key="update",
            content={"kind": "other", "text": "Synthetic corrected", "medication": {}})
        self.assertEqual(second.revision, 2)
        self.assertEqual(self.read(first)["content"], original)
        self.assertEqual(self.read(second)["content"]["text"], "Synthetic corrected")
        self.assertEqual(self.save()[0].pk, first.pk)
        self.assertEqual(MedicalAuditEvent.objects.filter(action="order_draft_created").count(), 1)
        self.assertEqual(MedicalAuditEvent.objects.filter(action="order_draft_saved").count(), 1)
        self.appointment.refresh_from_db()
        self.assertEqual((self.appointment.status, self.appointment.notes), ("created", ""))

    def test_stale_and_conflicting_retries_do_not_create_versions(self):
        with self.assertRaises(InvalidTransition):
            self.save(expected_patient_revision=999)
        with self.assertRaises(InvalidTransition):
            self.save(expected_encounter_revision=999)
        first, _ = self.save()
        with self.assertRaises(InvalidTransition):
            self.save(order_id=first.order_id, expected_order_revision=999, idempotency_key="stale")
        with self.assertRaises(CRMCommandConflict):
            self.save(reason="Changed")
        self.assertEqual(MedicalOrderRevision.objects.count(), 1)
        self.assertEqual(CRMCommandIdempotency.objects.count(), 1)

    def test_records_permission_does_not_grant_prescription_write_or_read(self):
        first, _ = self.save()
        RolePermission.objects.filter(business_role=self.role, resource="medical_prescriptions").delete()
        with self.assertRaises(PermissionDenied):
            self.save()
        with self.assertRaises(PermissionDenied):
            self.read(first)

    def test_revoked_branch_blocks_existing_command_replay_and_read(self):
        first, _ = self.save()
        self.assignment.branches.clear()
        with self.assertRaises(PermissionDenied):
            self.save()
        with self.assertRaises(PermissionDenied):
            self.read(first)

    def test_audit_failure_rolls_back_order_version_and_command(self):
        with patch("apps.medical.audit.MedicalAuditEvent.objects.create", side_effect=DatabaseError), self.assertRaises(MedicalAuditUnavailable):
            self.save()
        self.assertEqual(MedicalOrder.objects.count(), 0)
        self.assertEqual(MedicalOrderRevision.objects.count(), 0)
        self.assertEqual(CRMCommandIdempotency.objects.count(), 0)

    def test_ciphertext_cannot_be_swapped_between_versions(self):
        first, _ = self.save()
        second, _ = self.save(order_id=first.order_id, expected_order_revision=1, idempotency_key="update")
        MedicalOrderRevision.objects.filter(pk=second.pk).update(content_encrypted=first.content_encrypted)
        before = MedicalAuditEvent.objects.count()
        with self.assertRaises(MedicalDataUnavailable):
            self.read(second)
        self.assertEqual(MedicalAuditEvent.objects.count(), before)
