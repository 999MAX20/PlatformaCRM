from io import BytesIO
from unittest.mock import patch

from django.test import TestCase, override_settings
from django.utils import timezone
from docx import Document
from rest_framework.exceptions import PermissionDenied

from apps.businesses.models import Business, RolePermission
from apps.core.domain_errors import InvalidTransition
from apps.core.file_scanning import FileQuarantined
from apps.core.models import FileAttachment
from . import tests_document_artifact_generation as fixtures
from . import tests_document_template_source as documents
from .audit import MedicalAuditUnavailable
from .document_artifact_services import prepare_document_draft_docx, read_document_draft_docx
from .document_rule_services import save_document_rules
from .models import MedicalAuditEvent, MedicalDocumentArtifact, MedicalRoleAssignment
from .tests_document_rules import default_rule
from .tests_patient_services import key


@override_settings(MEDICAL_DATA_KEYS={"test": key(7)}, MEDICAL_DATA_ACTIVE_KEY_ID="test",
                   MEDICAL_IDENTITY_INDEX_KEY=key(8), USE_S3=False)
class DocumentDOCXExportTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        fixtures.DocumentArtifactGenerationTests.setUpTestData.__func__(cls)

    def setUp(self):
        fixtures.DocumentArtifactGenerationTests.setUp(self)
        self.legacy = self.version
        RolePermission.objects.update_or_create(business_role=self.role, resource="medical_documents",
            action="export", defaults={"scope": "business", "is_allowed": True})
        self.rules = save_document_rules(actor=self.head, business_id=self.business.pk,
            content={"name": "Synthetic export kind", "docx_allowed": True, "default": default_rule(), "services": []},
            template_ids=[self.template.template_id], reason="Synthetic permission", idempotency_key="docx-rules")[0]
        self.version = documents.DocumentTemplateSourceTests.save(self, idempotency_key="allowed-document")[0]
        self.scope = dict(actor=self.doctor, business_id=self.business.pk, patient_id=self.patient.pk,
            version_id=self.version.pk, language="ru", appointment_id=self.appointment.pk)

    def prepare(self, **changes):
        return prepare_document_draft_docx(**(self.scope | changes))

    def read(self, **changes):
        return read_document_draft_docx(**(self.scope | changes))

    def clean(self, item):
        with item.attachment.file.open("rb") as source:
            body = source.read()
        FileAttachment.objects.filter(pk=item.attachment_id).update(scan_status="clean", scan_sha256=item.sha256,
            scanned_at=timezone.now())
        return body

    def test_allowed_draft_is_marked_and_replay_exports_exact_bytes_with_audit(self):
        item, replayed = self.prepare()
        self.assertFalse(replayed)
        self.assertEqual(item.format, "docx")
        body = self.clean(item)
        docx = Document(BytesIO(body))
        self.assertIn("Черновик", " ".join(p.text for p in docx.sections[0].header.paragraphs))
        self.assertIn("Doctor edited synthetic text", " ".join(p.text for p in docx.paragraphs))
        with patch("apps.medical.document_artifact_services.render_draft_docx", side_effect=AssertionError("No regeneration")):
            replay, repeated = self.prepare()
        self.assertTrue(repeated)
        self.assertEqual(replay.pk, item.pk)
        self.assertEqual(self.read(), body)
        self.assertTrue(MedicalAuditEvent.objects.filter(action="document_exported", document_version=self.version).exists())

    def test_legacy_default_deny_and_future_rule_change_does_not_rewrite_saved_permission(self):
        with self.assertRaises(PermissionDenied):
            self.prepare(version_id=self.legacy.pk)
        save_document_rules(actor=self.head, business_id=self.business.pk, kind_id=self.rules.kind_id,
            expected_revision=1, content={"name": "Synthetic deny", "default": default_rule(), "services": []},
            template_ids=[self.template.template_id], reason="Synthetic disabled export", idempotency_key="deny-docx")
        item, _ = self.prepare()
        body = self.clean(item)
        self.assertEqual(self.read(), body)
        new = documents.DocumentTemplateSourceTests.save(self, idempotency_key="new-denied-document")[0]
        with self.assertRaises(PermissionDenied):
            self.prepare(version_id=new.pk)

    def test_reviewed_and_historical_versions_cannot_prepare_or_download_existing_docx(self):
        from .document_review_services import transition_document_review
        item, _ = self.prepare()
        self.clean(item)
        for expected, state in ((1, "ready_for_review"), (2, "reviewed")):
            transition_document_review(actor=self.doctor, business_id=self.business.pk, patient_id=self.patient.pk,
                version_id=self.version.pk, appointment_id=self.appointment.pk, expected_state_revision=expected,
                target=state, reason="", idempotency_key=f"docx-{state}")
            for operation in (self.prepare, self.read):
                with self.assertRaises(InvalidTransition):
                    operation()
        transition_document_review(actor=self.doctor, business_id=self.business.pk, patient_id=self.patient.pk,
            version_id=self.version.pk, appointment_id=self.appointment.pk, expected_state_revision=3,
            target="draft", reason="Synthetic reopen", idempotency_key="docx-reopen")
        documents.DocumentTemplateSourceTests.save(self, document_id=self.version.document_id,
            expected_document_revision=1, document_text="New synthetic text", reason="Synthetic edit", idempotency_key="docx-edit")
        for operation in (self.prepare, self.read):
            with self.assertRaises(InvalidTransition):
                operation()

    def test_export_permission_revocation_owner_and_other_business_deny_before_storage(self):
        item, _ = self.prepare()
        self.clean(item)
        other = Business.objects.create(name="Synthetic foreign export", owner=self.owner)
        for changes in ({"actor": self.owner}, {"business_id": other.pk}):
            with self.assertRaises(PermissionDenied):
                self.prepare(**changes)
        RolePermission.objects.filter(business_role=self.role, resource="medical_documents", action="export").update(is_allowed=False)
        with patch("apps.medical.document_artifact_services.open_clean_attachment", side_effect=AssertionError("No storage")):
            for operation in (self.prepare, self.read):
                with self.assertRaises(PermissionDenied):
                    operation()
        RolePermission.objects.filter(business_role=self.role, resource="medical_documents", action="export").update(is_allowed=True)
        MedicalRoleAssignment.objects.filter(pk=self.assignment.pk).update(revoked_at=timezone.now())
        with self.assertRaises(PermissionDenied):
            self.read()

    def test_quarantine_hash_and_audit_failure_never_release_bytes(self):
        item, _ = self.prepare()
        with self.assertRaises(FileQuarantined):
            self.read()
        self.clean(item)
        with patch("apps.medical.document_artifact_services.write_patient_audit", side_effect=MedicalAuditUnavailable):
            with self.assertRaises(MedicalAuditUnavailable):
                self.read()
        with item.attachment.file.open("wb") as target:
            target.write(b"Synthetic replaced bytes")
        with self.assertRaises(FileQuarantined):
            self.read()
        item.attachment.refresh_from_db()
        self.assertEqual(item.attachment.scan_status, "error")
        self.assertFalse(MedicalAuditEvent.objects.filter(action="document_exported").exists())

    def test_failed_audit_rolls_back_generated_blob_and_artifact(self):
        with patch("apps.medical.document_artifact_services.write_patient_audit", side_effect=MedicalAuditUnavailable):
            with self.assertRaises(MedicalAuditUnavailable):
                self.prepare()
        self.assertFalse(MedicalDocumentArtifact.objects.exists())
        self.assertFalse(FileAttachment.objects.exists())
        self.assertEqual(fixtures.DocumentArtifactGenerationTests.files(self), [])

    def test_finalized_encounter_or_archived_record_blocks_existing_editable_artifact(self):
        item, _ = self.prepare()
        self.clean(item)
        now = timezone.now()
        type(self.encounter_record).objects.filter(pk=self.encounter_record.pk).update(
            state="finalized", ended_at=now, finalized_at=now, finalized_by=self.doctor)
        for operation in (self.prepare, self.read):
            with self.assertRaises(InvalidTransition):
                operation()

        type(self.encounter_record).objects.filter(pk=self.encounter_record.pk).update(
            state="draft", ended_at=None, finalized_at=None, finalized_by=None)
        type(self.record).objects.filter(pk=self.record.pk).update(
            state="archived", archived_at=now, archived_by=self.doctor)
        for operation in (self.prepare, self.read):
            with self.assertRaises(InvalidTransition):
                operation()

    def test_document_correction_basis_expires_at_exact_24_hours(self):
        from .correction_access_services import request_correction_access, review_correction_access
        from apps.branches.models import BranchAccess
        head_assignment = MedicalRoleAssignment.objects.get(member__user=self.head, member__business=self.business)
        head_assignment.branches.add(self.encounter_record.branch)
        branch_access, _ = BranchAccess.objects.get_or_create(member=head_assignment.member, defaults={"all_branches": False})
        branch_access.branches.add(self.encounter_record.branch)
        head_role = head_assignment.business_role
        for resource, action in (("medical_records", "view"), ("medical_records", "manage"), ("clients", "view")):
            RolePermission.objects.update_or_create(business_role=head_role, resource=resource, action=action,
                defaults={"scope": "business", "is_allowed": True})
        requested, _ = request_correction_access(actor=self.doctor, business_id=self.business.pk,
            encounter_id=self.encounter_record.pk, document_id=self.version.document_id,
            expected_patient_revision=self.patient.revision, expected_target_revision=1,
            reason="Synthetic limited correction", idempotency_key="docx-correction-request")
        grant, _ = review_correction_access(actor=self.head, business_id=self.business.pk, request_id=requested.pk,
            expected_revision=1, decision="approve", reason="Synthetic approval", idempotency_key="docx-correction-review")
        self.assertEqual((grant.expires_at - grant.reviewed_at).total_seconds(), 24 * 3600)
        now = timezone.now()
        type(self.encounter_record).objects.filter(pk=self.encounter_record.pk).update(
            state="finalized", ended_at=now, finalized_at=now, finalized_by=self.doctor)
        self.scope.pop("appointment_id")
        self.scope["correction_access_id"] = grant.pk
        item, _ = self.prepare()
        expected = self.clean(item)
        self.assertEqual(self.read(), expected)
        with patch("apps.medical.correction_access_context.timezone.now", return_value=grant.expires_at):
            with patch("apps.medical.document_artifact_services.open_clean_attachment", side_effect=AssertionError("No expired read")):
                for operation in (self.prepare, self.read):
                    with self.assertRaises(PermissionDenied):
                        operation()
