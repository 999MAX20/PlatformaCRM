from unittest.mock import patch

from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied

from apps.businesses.models import RolePermission
from apps.core.file_scanning import FileQuarantined, scan_attachment
from apps.core.domain_errors import InvalidTransition
from apps.core.tests_file_scanning import clean_result
from . import tests_file_upload as fixtures
from . import tests_patient_services as crypto
from .audit import MedicalAuditUnavailable
from .file_content import read_file_metadata
from .file_reads import list_medical_files, read_medical_file_version
from .file_services import update_medical_file_metadata
from .models import MedicalAuditEvent


@override_settings(MEDICAL_DATA_KEYS={"test": crypto.key(7)}, MEDICAL_DATA_ACTIVE_KEY_ID="test",
                   MEDICAL_IDENTITY_INDEX_KEY=crypto.key(8), USE_S3=False)
class MedicalFileReadTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        fixtures.MedicalFileUploadTests.setUpTestData.__func__(cls)

    setUp = fixtures.MedicalFileUploadTests.setUp
    upload = fixtures.MedicalFileUploadTests.upload

    def scope(self):
        return dict(actor=self.doctor, business_id=self.business.pk, patient_id=self.patient.pk,
                    appointment_id=self.appointment.pk)

    def read(self, item, **options):
        return read_medical_file_version(**(self.scope() | {"file_id": item.medical_file_id} | options))

    def clean(self, item):
        with patch("apps.core.file_scanning.scan_stream", side_effect=clean_result):
            self.assertEqual(scan_attachment(item.medical_file.attachment_id, self.business.pk), "clean")

    def test_list_filters_fdi_and_audits_metadata_without_storage_url(self):
        version, _ = self.upload()
        rows = list_medical_files(**self.scope(), tooth=11)
        self.assertEqual(rows["results"][0]["id"], version.medical_file_id)
        self.assertEqual(rows["results"][0]["scan_status"], "pending")
        self.assertNotIn("private/attachments", str(rows))
        self.assertEqual(list_medical_files(**self.scope(), tooth=21)["results"], [])
        self.assertTrue(MedicalAuditEvent.objects.filter(action="read", file_version=version).exists())

    def test_pending_and_infected_files_cannot_be_previewed_or_downloaded(self):
        version, _ = self.upload()
        for state in ("pending", "scanning", "infected", "error"):
            type(version.medical_file.attachment).objects.filter(pk=version.medical_file.attachment_id).update(scan_status=state)
            for operation in ("download", "preview"):
                with self.subTest(state=state, operation=operation), self.assertRaises(FileQuarantined):
                    self.read(version, **{operation: True})
        self.assertFalse(MedicalAuditEvent.objects.filter(action="file_downloaded").exists())

    def test_clean_preview_and_download_are_verified_in_memory_and_export_has_own_permission(self):
        version, _ = self.upload()
        self.clean(version)
        for operation in ("preview", "download"):
            metadata, source = self.read(version, **{operation: True})
            with source:
                self.assertEqual(source.read(), b"%PDF-1.4\nSynthetic")
                self.assertFalse(hasattr(source, "_rolled"))
            self.assertEqual(metadata["name"], "Private-patient-name.pdf")
        RolePermission.objects.filter(business_role=self.role, resource="medical_files", action="export").update(is_allowed=False)
        with self.assertRaises(PermissionDenied):
            self.read(version, download=True)
        _, source = self.read(version, preview=True)
        source.close()

    def test_audit_failure_never_releases_bytes_or_list_metadata(self):
        version, _ = self.upload()
        self.clean(version)
        with patch("apps.medical.file_reads.write_patient_audit", side_effect=MedicalAuditUnavailable()):
            with self.assertRaises(MedicalAuditUnavailable):
                self.read(version, download=True)
            with self.assertRaises(MedicalAuditUnavailable):
                list_medical_files(**self.scope())

    def test_reserve_read_allows_preview_but_never_export_and_preserves_permission_checks(self):
        from .audit_reserve import ReserveReceipt, ReserveUnavailable
        version, _ = self.upload()
        self.clean(version)
        receipt = ReserveReceipt(event_id="synthetic", version_id="synthetic-version")
        with patch("apps.medical.audit.MedicalAuditEvent.objects.create", return_value=None), \
                patch("apps.medical.audit_reserve.write_reserved_read", return_value=receipt) as reserve:
            payload, source = self.read(version, preview=True)
            with source:
                self.assertEqual(source.read(), b"%PDF-1.4\nSynthetic")
            self.assertEqual(payload["version_id"], version.pk)
            self.assertEqual(reserve.call_args.args[0]["file_version"].pk, version.pk)
            reserve.reset_mock()
            with self.assertRaises(MedicalAuditUnavailable):
                self.read(version, download=True)
            reserve.assert_not_called()
            RolePermission.objects.filter(business_role=self.role, resource="medical_files", action="view").update(is_allowed=False)
            with self.assertRaises(PermissionDenied):
                self.read(version, preview=True)
            reserve.assert_not_called()
        RolePermission.objects.filter(business_role=self.role, resource="medical_files", action="view").update(is_allowed=True)
        with patch("apps.medical.audit.MedicalAuditEvent.objects.create", return_value=None), \
                patch("apps.medical.audit_reserve.write_reserved_read", side_effect=ReserveUnavailable()):
            with self.assertRaises(MedicalAuditUnavailable):
                self.read(version, preview=True)

    def test_changed_storage_bytes_stay_quarantined_after_read_denial(self):
        version, _ = self.upload()
        self.clean(version)
        blob = version.medical_file.attachment
        with blob.file.storage.open(blob.file.name, "wb") as source:
            source.write(b"%PDF-1.4\nReplaced")
        with self.assertRaises(FileQuarantined):
            self.read(version, preview=True)
        blob.refresh_from_db()
        self.assertEqual((blob.scan_status, blob.scan_sha256), ("error", ""))
        self.assertEqual(blob.scan_error_code, "file_integrity_unavailable")
        self.assertFalse(MedicalAuditEvent.objects.filter(action="read", file_version=version).exists())

    def test_metadata_revision_preserves_old_version_and_updates_fdi_filter_without_changing_bytes(self):
        first, _ = self.upload()
        self.assertTrue(self.read(first)[0]["actions"]["edit_metadata"])
        second, replayed = update_medical_file_metadata(**self.scope(), file_id=first.medical_file_id,
            expected_revision=1, description="New description", teeth=[21], reason="Synthetic correction",
            idempotency_key="metadata")
        self.assertFalse(replayed)
        self.assertEqual(read_file_metadata(first)["teeth"], [11])
        self.assertEqual(read_file_metadata(second)["teeth"], [21])
        self.assertEqual(list_medical_files(**self.scope(), tooth=11)["results"], [])
        self.assertEqual(len(list_medical_files(**self.scope(), tooth=21)["results"]), 1)
        self.assertEqual(self.read(first, version_id=first.pk)[0]["teeth"], [11])
        self.assertFalse(self.read(first, version_id=first.pk)[0]["actions"]["edit_metadata"])
        self.assertTrue(self.read(second)[0]["actions"]["edit_metadata"])
        self.assertEqual(second.medical_file.attachment_id, first.medical_file.attachment_id)

    def test_metadata_action_tracks_write_permission_without_removing_read_access(self):
        version, _ = self.upload()
        RolePermission.objects.filter(business_role=self.role, resource="medical_files", action="create").update(is_allowed=False)
        self.assertFalse(self.read(version)[0]["actions"]["edit_metadata"])
        with self.assertRaises(PermissionDenied):
            update_medical_file_metadata(**self.scope(), file_id=version.medical_file_id,
                expected_revision=1, description="Denied", teeth=[], reason="Synthetic correction",
                idempotency_key="denied-metadata")

    def test_metadata_action_denies_other_authors_and_finalized_encounter(self):
        version, _ = self.upload()
        item = version.medical_file
        type(item).objects.filter(pk=item.pk).update(created_by=self.owner)
        self.assertFalse(self.read(version)[0]["actions"]["edit_metadata"])
        command = {**self.scope(), "file_id": item.pk, "expected_revision": 1,
                   "description": "Denied", "teeth": [], "reason": "Synthetic", "idempotency_key": "denied"}
        with self.assertRaises(PermissionDenied):
            update_medical_file_metadata(**command)
        type(item).objects.filter(pk=item.pk).update(created_by=self.doctor)
        now = timezone.now()
        type(self.encounter_record).objects.filter(pk=self.encounter_record.pk).update(
            state="finalized", ended_at=now, finalized_at=now, finalized_by=self.doctor)
        self.assertFalse(self.read(version)[0]["actions"]["edit_metadata"])
        with self.assertRaises(InvalidTransition):
            update_medical_file_metadata(**command)
