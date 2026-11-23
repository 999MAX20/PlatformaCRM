from unittest.mock import patch

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from apps.businesses.models import Business, RolePermission
from apps.clients.models import Client
from apps.core.file_scanning import scan_attachment
from apps.core.models import FileAttachment
from apps.core.tests_file_scanning import clean_result
from . import tests_file_upload as fixtures
from . import tests_patient_services as crypto
from .audit import MedicalAuditUnavailable
from .models import MedicalAttachment, MedicalAuditEvent, PatientProfile


@override_settings(MEDICAL_DATA_KEYS={"test": crypto.key(7)}, MEDICAL_DATA_ACTIVE_KEY_ID="test",
                   MEDICAL_IDENTITY_INDEX_KEY=crypto.key(8), USE_S3=False)
class MedicalFileAPITests(TestCase):
    @classmethod
    def setUpTestData(cls):
        fixtures.MedicalFileUploadTests.setUpTestData.__func__(cls)

    def setUp(self):
        fixtures.MedicalFileUploadTests.setUp(self)
        self.api = APIClient()
        self.api.force_authenticate(self.doctor)

    def scope(self):
        return dict(business_id=self.business.pk, patient_id=self.patient.pk, appointment_id=self.appointment.pk)

    def upload(self, **overrides):
        data = {**self.scope(), "record_id": self.record.pk, "encounter_id": self.encounter_record.pk,
                "expected_patient_revision": self.patient.revision, "description": "Synthetic description",
                "teeth": [11, 12], "file": SimpleUploadedFile("Private.pdf", b"%PDF-1.4\nSynthetic", "application/pdf")}
        return self.api.post("/api/medical/files/", data | overrides, format="multipart", HTTP_IDEMPOTENCY_KEY="file-api")

    def clean(self, file_id):
        item = MedicalAttachment.objects.get(pk=file_id)
        with patch("apps.core.file_scanning.scan_stream", side_effect=clean_result):
            self.assertEqual(scan_attachment(item.attachment_id, self.business.pk), "clean")

    def test_workspace_actions_follow_current_permissions_and_upload_target(self):
        scope = self.scope() | {"record_id": self.record.pk, "encounter_id": self.encounter_record.pk}
        url = "/api/medical/files/workspace-access/"
        response = self.api.get(url, scope)
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data["actions"], {"upload": True, "export": True})
        self.assertEqual(response.data["patient_revision"], self.patient.revision)
        self.assertIn("pdf", response.data["allowed_extensions"])
        self.assertGreater(response.data["max_bytes"], 0)
        RolePermission.objects.filter(business_role=self.role, resource="medical_files", action="create").update(is_allowed=False)
        response = self.api.get(url, scope)
        self.assertEqual(response.data["actions"], {"upload": False, "export": True})
        RolePermission.objects.filter(business_role=self.role, resource="medical_files", action="create").update(is_allowed=True)
        type(self.patient).objects.filter(pk=self.patient.pk).update(identity_status="unverified", verified_at=None,
            verified_by=None, verification_evidence_encrypted="")
        response = self.api.get(url, scope)
        self.assertFalse(response.data["actions"]["upload"])
        self.assertTrue(response.data["actions"]["export"])
        self.assertEqual(self.upload().status_code, 409)

    def test_workspace_accepts_basis_without_preloaded_record_and_rejects_unknown_record(self):
        url = "/api/medical/files/workspace-access/"
        response = self.api.get(url, self.scope())
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data["record_id"], self.record.pk)
        self.assertTrue(response.data["actions"]["upload"])
        response = self.api.get(url, self.scope() | {"record_id": self.record.pk + 1000})
        self.assertEqual(response.status_code, 403)

    def test_upload_list_preview_download_and_replay(self):
        created = self.upload()
        self.assertEqual(created.status_code, 201, created.data)
        file_id = created.data["id"]
        replay = self.upload()
        self.assertEqual(replay.status_code, 200, replay.data)
        self.assertTrue(replay.data["replayed"])
        self.assertEqual(FileAttachment.objects.count(), 1)
        rows = self.api.get("/api/medical/files/", self.scope() | {"tooth": 11})
        self.assertEqual(rows.status_code, 200, rows.data)
        self.assertEqual(rows.data["results"][0]["teeth"], [11, 12])
        self.assertEqual(rows["Cache-Control"], "no-store, private")
        self.assertNotIn("url", str(rows.data))
        blocked = self.api.get(f"/api/medical/files/{file_id}/preview/", self.scope())
        self.assertEqual(blocked.status_code, 423)
        self.clean(file_id)
        for operation, disposition in (("preview", "inline"), ("download", "attachment")):
            response = self.api.get(f"/api/medical/files/{file_id}/{operation}/", self.scope())
            self.assertEqual(response.status_code, 200)
            self.assertEqual(b"".join(response.streaming_content), b"%PDF-1.4\nSynthetic")
            self.assertTrue(response["Content-Disposition"].startswith(disposition))
            self.assertEqual(response["X-Content-Type-Options"], "nosniff")
            self.assertIn("sandbox", response["Content-Security-Policy"])
            self.assertEqual(response["Cache-Control"], "no-store, private")

    def test_metadata_history_pagination_keeps_old_version_and_conflicts(self):
        created = self.upload()
        file_id = created.data["id"]
        body = self.scope() | {"expected_revision": 1, "description": "Changed", "teeth": [21], "reason": "Correction"}
        updated = self.api.post(f"/api/medical/files/{file_id}/metadata/", body, format="json", HTTP_IDEMPOTENCY_KEY="file-edit")
        self.assertEqual(updated.status_code, 200, updated.data)
        conflict = self.api.post(f"/api/medical/files/{file_id}/metadata/", body, format="json", HTTP_IDEMPOTENCY_KEY="file-edit-stale")
        self.assertEqual(conflict.status_code, 409)
        page = self.api.get(f"/api/medical/files/{file_id}/revisions/", self.scope() | {"limit": 1})
        self.assertEqual(page.status_code, 200, page.data)
        self.assertEqual(page.data["results"][0]["revision"], 2)
        self.assertEqual(page.data["next_before_revision"], 2)
        old = self.api.get(f"/api/medical/files/{file_id}/revisions/", self.scope() | {"before_revision": 2})
        self.assertEqual(old.data["results"][0]["teeth"], [11, 12])
        exact = self.api.get(f"/api/medical/files/{file_id}/", self.scope() | {"version_id": created.data["version_id"]})
        self.assertEqual(exact.data["description"], "Synthetic description")
        self.assertTrue(MedicalAuditEvent.objects.filter(action="read", file_version_id=created.data["version_id"]).exists())

    def test_owner_revoked_permission_and_foreign_patient_cannot_read_bytes(self):
        created = self.upload()
        file_id = created.data["id"]
        self.clean(file_id)
        self.api.force_authenticate(self.owner)
        self.assertEqual(self.api.get(f"/api/medical/files/{file_id}/preview/", self.scope()).status_code, 403)
        self.assertTrue(MedicalAuditEvent.objects.filter(actor=self.owner, business=self.business,
            action="access_denied", result="denied", patient__isnull=True, file_version__isnull=True).exists())
        self.api.force_authenticate(self.doctor)
        self.assertIn(self.api.get(f"/api/medical/files/{file_id}/preview/",
            self.scope() | {"patient_id": self.patient.pk + 1000}).status_code, (403, 404))
        RolePermission.objects.filter(business_role=self.role, resource="medical_files", action="export").update(is_allowed=False)
        self.assertEqual(self.api.get(f"/api/medical/files/{file_id}/download/", self.scope()).status_code, 403)
        self.api.force_authenticate(None)
        self.assertEqual(self.api.get(f"/api/medical/files/{file_id}/preview/", self.scope()).status_code, 401)

    def test_strict_input_audit_failure_and_generic_attachment_denial(self):
        invalid = self.upload(unexpected="ignored?")
        self.assertEqual(invalid.status_code, 400)
        self.assertEqual(MedicalAttachment.objects.count(), 0)
        created = self.upload()
        file_id = created.data["id"]
        self.clean(file_id)
        blob = MedicalAttachment.objects.get(pk=file_id).attachment
        self.assertEqual(self.api.get(f"/api/file-attachments/{blob.pk}/download/").status_code, 404)
        with patch("apps.medical.file_reads.write_patient_audit", side_effect=MedicalAuditUnavailable()):
            response = self.api.get(f"/api/medical/files/{file_id}/preview/", self.scope())
        self.assertEqual(response.status_code, 503)
        self.assertNotIn("Synthetic", str(response.data))

    def test_existing_foreign_tenant_patient_cannot_be_used_for_reads_or_upload(self):
        foreign = Business.objects.create(owner=self.owner, name="Foreign", slug="file-api-foreign")
        client = Client.objects.create(business=foreign, full_name="Foreign synthetic patient")
        patient = PatientProfile.objects.create(business=foreign, client=client, created_by=self.owner)
        created = self.upload()
        for scope in (self.scope() | {"patient_id": patient.pk},
                      self.scope() | {"business_id": foreign.pk, "patient_id": patient.pk}):
            workspace = self.api.get("/api/medical/files/workspace-access/", scope)
            self.assertIn(workspace.status_code, (403, 404))
            self.assertNotIn("record_id", workspace.data)
            for suffix in ("", "preview/", "download/", "revisions/"):
                response = self.api.get(f"/api/medical/files/{created.data['id']}/{suffix}", scope)
                self.assertIn(response.status_code, (403, 404))
                self.assertNotIn("Foreign synthetic", str(response.data))
            self.assertIn(self.upload(**scope).status_code, (403, 404))
        self.assertEqual(MedicalAttachment.objects.count(), 1)
        self.assertFalse(MedicalAuditEvent.objects.filter(business=foreign).exists())

    @override_settings(MAX_UPLOAD_SIZE_MB=1, FILE_UPLOAD_MAX_MEMORY_SIZE=1)
    def test_upload_never_spills_to_disk_and_rejects_oversize_or_multiple_files(self):
        with patch("django.core.files.uploadhandler.TemporaryUploadedFile", side_effect=AssertionError("No clinical temp files")):
            response = self.upload()
            self.assertEqual(response.status_code, 201, response.data)
            oversized = self.upload(file=SimpleUploadedFile("Large.pdf", b"%PDF-1.4\n" + b"x" * (1024 * 1024), "application/pdf"))
            self.assertEqual(oversized.status_code, 413, oversized.data)
            multiple = self.upload(file=[SimpleUploadedFile("a.pdf", b"%PDF-a", "application/pdf"),
                                         SimpleUploadedFile("b.pdf", b"%PDF-b", "application/pdf")])
            self.assertEqual(multiple.status_code, 400, multiple.data)
        self.assertEqual(MedicalAttachment.objects.count(), 1)
