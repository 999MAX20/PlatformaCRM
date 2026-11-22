from unittest.mock import patch

from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied, ValidationError
from apps.businesses.models import RolePermission

from . import tests_document_services as fixtures
from . import tests_patient_services as crypto_fixtures
from .audit import MedicalAuditUnavailable
from .document_reads import document_workspace_access, list_document_revisions, list_patient_documents
from .identity_crypto import MedicalDataUnavailable
from .models import MedicalAuditEvent, MedicalDocumentRevision


@override_settings(MEDICAL_DATA_KEYS={"test": crypto_fixtures.key(7)}, MEDICAL_DATA_ACTIVE_KEY_ID="test",
                   MEDICAL_IDENTITY_INDEX_KEY=crypto_fixtures.key(8))
class DocumentReadTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        fixtures.DocumentServiceTests.setUpTestData.__func__(cls)

    def setUp(self):
        fixtures.DocumentServiceTests.setUp(self)

    def save(self, **overrides):
        return fixtures.DocumentServiceTests.save(self, **overrides)[0]

    def list(self, **overrides):
        return list_patient_documents(**(dict(actor=self.doctor, business_id=self.business.pk,
            patient_id=self.patient.pk, appointment_id=self.appointment.pk) | overrides))

    def history(self, version, **overrides):
        return list_document_revisions(**(dict(actor=self.doctor, business_id=self.business.pk,
            patient_id=self.patient.pk, appointment_id=self.appointment.pk, document_id=version.document_id) | overrides))

    def access(self, **overrides):
        return document_workspace_access(**(dict(actor=self.doctor, business_id=self.business.pk,
            patient_id=self.patient.pk, appointment_id=self.appointment.pk, encounter_id=self.encounter_record.pk) | overrides))

    def test_document_actions_are_independent_of_clinical_edit_permissions(self):
        RolePermission.objects.filter(business_role=self.role, resource="medical_records").delete()
        access = self.access()
        self.assertEqual(access["actions"], {"view": True, "create": True, "update": True})
        self.assertEqual(access["patient_revision"], self.patient.revision)
        self.assertEqual(access["encounter_revision"], 1)
        self.assertNotIn("clinical", access)
        RolePermission.objects.filter(business_role=self.role, resource="medical_documents", action="create").delete()
        self.assertEqual(self.access()["actions"], {"view": True, "create": False, "update": True})

    def test_unverified_identity_disables_writes_but_not_permitted_reads(self):
        type(self.patient).objects.filter(pk=self.patient.pk).update(identity_status="unverified",
            verified_at=None, verified_by=None, verification_evidence_encrypted="")
        self.assertEqual(self.access()["actions"], {"view": True, "create": False, "update": False})

    def test_finalized_encounter_disables_writes(self):
        now = timezone.now()
        type(self.encounter_record).objects.filter(pk=self.encounter_record.pk).update(
            state="finalized", ended_at=now, finalized_at=now, finalized_by=self.doctor)
        self.assertEqual(self.access()["actions"], {"view": True, "create": False, "update": False})

    def test_metadata_denies_owner_other_encounter_and_lost_basis(self):
        with self.assertRaises(PermissionDenied):
            self.access(actor=self.owner)
        with self.assertRaises(PermissionDenied):
            self.access(encounter_id=999999)
        self.assignment.branches.clear()
        with self.assertRaises(PermissionDenied):
            self.access()

    def test_metadata_read_requires_audit(self):
        with patch("apps.medical.document_reads.write_patient_audit", side_effect=MedicalAuditUnavailable):
            with self.assertRaises(MedicalAuditUnavailable):
                self.access()

    def test_latest_documents_and_history_paginate_and_audit_exact_versions(self):
        first = self.save()
        latest = self.save(document_id=first.document_id, expected_document_revision=1, idempotency_key="edit")
        other = self.save(idempotency_key="other")
        before = MedicalAuditEvent.objects.count()
        page = self.list(limit=1, encounter_id=self.encounter_record.pk)
        self.assertEqual(page["results"][0]["version_id"], other.pk)
        self.assertEqual(MedicalAuditEvent.objects.count(), before + 1)
        page = self.list(limit=1, before_id=page["next_before_id"])
        self.assertEqual(page["results"][0]["version_id"], latest.pk)
        self.assertIsNone(page["next_before_id"])
        self.assertNotIn("snapshot", page["results"][0])
        history = self.history(first, limit=1)
        self.assertEqual(history["current_revision"], 2)
        self.assertEqual(history["results"][0]["version_id"], latest.pk)
        history = self.history(first, limit=1, before_revision=history["next_before_revision"])
        self.assertEqual(history["results"][0]["version_id"], first.pk)
        self.assertIsNone(history["next_before_revision"])
        self.assertTrue(MedicalAuditEvent.objects.filter(action="read", document_version=first).exists())

    def test_empty_list_still_requires_current_treatment_access(self):
        self.assertEqual(self.list()["results"], [])
        with self.assertRaises(PermissionDenied):
            self.list(actor=self.owner)
        self.assignment.branches.clear()
        with self.assertRaises(PermissionDenied):
            self.list()

    def test_invalid_scope_and_unbounded_pages(self):
        version = self.save()
        for invalid in ({"limit": 51}, {"limit": True}, {"before_id": 0}, {"appointment_id": None},
                        {"participation_id": 1}, {"encounter_id": True}):
            with self.assertRaises(ValidationError):
                self.list(**invalid)
        with self.assertRaises(PermissionDenied):
            self.list(encounter_id=999999)
        with self.assertRaises(PermissionDenied):
            self.history(version, document_id=999999)
        with self.assertRaises(ValidationError):
            self.history(version, before_revision=0)

    def test_audit_failure_and_corruption_return_no_partial_page(self):
        self.save()
        version = self.save(idempotency_key="second")
        before = MedicalAuditEvent.objects.count()
        with patch("apps.medical.document_services.write_patient_audit", side_effect=MedicalAuditUnavailable):
            with self.assertRaises(MedicalAuditUnavailable):
                self.list()
        with patch("apps.medical.document_reads.write_patient_audit", side_effect=MedicalAuditUnavailable):
            with self.assertRaises(MedicalAuditUnavailable):
                self.history(version)
        self.assertEqual(MedicalAuditEvent.objects.count(), before)
        MedicalDocumentRevision.objects.filter(pk=version.pk).update(snapshot_encrypted="corrupt")
        with self.assertRaises(MedicalDataUnavailable):
            self.list()
        self.assertEqual(MedicalAuditEvent.objects.count(), before)

    def test_missing_current_revision_fails_closed(self):
        version = self.save()
        version.document.revision = 2
        version.document.save(update_fields=["revision"])
        with self.assertRaises(MedicalDataUnavailable):
            self.list()
        with self.assertRaises(MedicalDataUnavailable):
            self.history(version)
