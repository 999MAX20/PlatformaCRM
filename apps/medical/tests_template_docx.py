import hashlib
from io import BytesIO
from unittest.mock import patch

from django.db import DatabaseError
from django.test import TestCase, override_settings
from django.utils import timezone
from docx import Document
from rest_framework.exceptions import PermissionDenied

from apps.businesses.models import Business, RolePermission
from apps.core.antivirus import ScanResult, ScanUnavailable
from apps.core.domain_errors import InvalidTransition
from apps.core.models import AuditLog
from . import tests_common_templates as fixtures
from . import tests_patient_services as crypto
from .audit import MedicalAuditUnavailable
from .document_artifact_services import DocumentPDFUnavailable
from .document_rule_services import save_document_rules
from .tests_document_rules import default_rule
from .template_docx import download_template_docx


def clean(stream):
    body = stream.read()
    return ScanResult(True, hashlib.sha256(body).hexdigest(), len(body), "ClamAV test/1")


@override_settings(MEDICAL_DATA_KEYS={"test": crypto.key(7)}, MEDICAL_DATA_ACTIVE_KEY_ID="test",
                   MEDICAL_IDENTITY_INDEX_KEY=crypto.key(8))
class TemplateDocxTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        fixtures.CommonTemplateTests.setUpTestData.__func__(cls)
        for role, scope in ((cls.role, "own"), (cls.head_role, "business")):
            RolePermission.objects.create(business_role=role, resource="medical_documents",
                action="export", scope=scope, is_allowed=True)

    save = fixtures.CommonTemplateTests.save
    submit = fixtures.CommonTemplateTests.submit
    approve = fixtures.CommonTemplateTests.approve

    def setUp(self):
        self.version, _ = self.save(text="Synthetic {{patient.full_name}}")
        self.rules = self.configure()

    def configure(self, **changes):
        return save_document_rules(actor=self.head, business_id=self.business.pk,
            template_ids=[self.version.template_id], reason="Synthetic permission",
            content={"name": "Synthetic kind", "docx_allowed": True, "default": default_rule(), "services": []},
            idempotency_key="initial-rules", **changes)[0]

    def download(self, **changes):
        return download_template_docx(**(dict(actor=self.head, business_id=self.business.pk,
            version_id=self.version.pk, language="ru") | changes))

    @patch("apps.medical.template_docx.scan_stream", side_effect=clean)
    def test_exact_draft_literal_fields_and_export_audit(self, scanner):
        original = self.version.snapshot_encrypted
        first = self.download()
        self.assertEqual(first, self.download())
        doc = Document(BytesIO(first))
        self.assertIn("Synthetic {{patient.full_name}}", "\n".join(p.text for p in doc.paragraphs))
        self.assertIn("Черновик", "\n".join(p.text for s in doc.sections for p in s.header.paragraphs))
        event = AuditLog.objects.filter(entity_type="medical_template_version").first()
        self.assertEqual(event.metadata["sha256"], hashlib.sha256(first).hexdigest())
        self.assertEqual(event.metadata["rule_version_id"], self.rules.pk)
        self.assertNotIn("Synthetic", str(event.metadata))
        self.version.refresh_from_db()
        self.assertEqual(self.version.snapshot_encrypted, original)

    @patch("apps.medical.template_docx.scan_stream", side_effect=clean)
    def test_doctor_needs_approved_common_and_current_export_permission(self, scanner):
        with self.assertRaises(PermissionDenied):
            self.download(actor=self.doctor)
        self.approve(self.version)
        self.assertTrue(self.download(actor=self.doctor).startswith(b"PK"))
        RolePermission.objects.filter(business_role=self.role, action="export").update(is_allowed=False)
        with self.assertRaises(PermissionDenied):
            self.download(actor=self.doctor)

    @patch("apps.medical.template_docx.scan_stream", side_effect=clean)
    def test_owner_tenant_and_suspended_template_denied_before_scan(self, scanner):
        other = Business.objects.create(owner=self.owner, name="Other export", slug="other-export")
        for changes in ({"actor": self.owner}, {"business_id": other.pk}):
            with self.assertRaises(PermissionDenied):
                self.download(**changes)
        self.version.template.is_active = False
        self.version.template.save(update_fields=["is_active"])
        with self.assertRaises(InvalidTransition):
            self.download()
        scanner.assert_not_called()

    def test_scan_failure_infected_or_wrong_digest_never_exports(self):
        for result in (ScanUnavailable(), ScanResult(False, "x", 1, "test"), ScanResult(True, "x", 1, "test")):
            with self.subTest(result=result), patch("apps.medical.template_docx.scan_stream",
                    **({"side_effect": result} if isinstance(result, Exception) else {"return_value": result})):
                with self.assertRaises(DocumentPDFUnavailable):
                    self.download()
        self.assertFalse(AuditLog.objects.filter(entity_type="medical_template_version").exists())

    def test_revocation_during_scan_prevents_download(self):
        def revoke(stream):
            self.head_assignment.revoked_at = timezone.now()
            self.head_assignment.save(update_fields=["revoked_at"])
            return clean(stream)
        with patch("apps.medical.template_docx.scan_stream", side_effect=revoke), self.assertRaises(PermissionDenied):
            self.download()
        self.assertFalse(AuditLog.objects.filter(entity_type="medical_template_version").exists())

    def test_matrix_change_during_scan_requires_fresh_attempt(self):
        def change(stream):
            save_document_rules(actor=self.head, business_id=self.business.pk,
                template_ids=[self.version.template_id], reason="Synthetic changed requirements",
                content={"name": "Changed", "docx_allowed": True, "default": default_rule(), "services": []},
                idempotency_key="changed", kind_id=self.rules.kind_id, expected_revision=1)
            return clean(stream)
        with patch("apps.medical.template_docx.scan_stream", side_effect=change), self.assertRaises(InvalidTransition):
            self.download()
        self.assertFalse(AuditLog.objects.filter(entity_type="medical_template_version").exists())

    @patch("apps.medical.template_docx.scan_stream", side_effect=clean)
    def test_audit_failure_prevents_download(self, scanner):
        with patch("apps.medical.template_docx.AuditLog.objects.create", side_effect=DatabaseError()), self.assertRaises(MedicalAuditUnavailable):
            self.download()

    @patch("apps.medical.template_docx.scan_stream", side_effect=clean)
    def test_common_export_requires_business_scope_and_explicit_opt_in(self, scanner):
        RolePermission.objects.filter(business_role=self.head_role, action="export").update(scope="own")
        with self.assertRaises(PermissionDenied):
            self.download()
        RolePermission.objects.filter(business_role=self.head_role, action="export").update(scope="business")
        save_document_rules(actor=self.head, business_id=self.business.pk,
            template_ids=[self.version.template_id], reason="Disable editable export",
            content={"name": "Restricted", "docx_allowed": False, "default": default_rule(), "services": []},
            idempotency_key="off", kind_id=self.rules.kind_id, expected_revision=1)
        with self.assertRaises(PermissionDenied):
            self.download()
        scanner.assert_not_called()

    @patch("apps.medical.template_docx.scan_stream", side_effect=clean)
    def test_personal_export_does_not_grant_head_access_to_private_content(self, scanner):
        from .template_services import save_personal_template_draft
        from .template_reviews import submit_personal_template, decide_template_review
        personal, _ = save_personal_template_draft(actor=self.doctor, business_id=self.business.pk,
            title="Personal", text="Private {{patient.full_name}}", idempotency_key="personal")
        submit_personal_template(actor=self.doctor, business_id=self.business.pk,
            version_id=personal.pk, idempotency_key="submit-personal")
        decide_template_review(actor=self.head, business_id=self.business.pk, version_id=personal.pk,
            decision="approved", reason="Synthetic approval", idempotency_key="approve-personal")
        save_document_rules(actor=self.head, business_id=self.business.pk, template_ids=[personal.template_id],
            reason="Allow personal", content={"name": "Personal kind", "docx_allowed": True,
                "default": default_rule(), "services": []}, idempotency_key="personal-kind")
        self.assertTrue(self.download(actor=self.doctor, version_id=personal.pk).startswith(b"PK"))
        with self.assertRaises(PermissionDenied):
            self.download(version_id=personal.pk)
