from concurrent.futures import ThreadPoolExecutor
from io import BytesIO
from threading import Barrier
from unittest import skipUnless
from unittest.mock import patch

from django.db import close_old_connections, connection, connections
from django.test import TransactionTestCase, override_settings
from rest_framework.exceptions import ValidationError
from PIL import Image

from apps.billing.models import Subscription, SubscriptionPlan
from apps.core.models import FileAttachment
from . import tests_document_artifact_generation as fixtures
from . import tests_document_template_source as template_fixtures
from .audit import MedicalAuditUnavailable, write_patient_audit
from .document_artifact_content import read_document_artifact_manifest, verify_document_artifact_bytes
from .models import MedicalAuditEvent, MedicalDocumentArtifact
from .tests_patient_services import key


@skipUnless(connection.vendor == "postgresql", "Document artifact races require PostgreSQL row locks")
@override_settings(MEDICAL_DATA_KEYS={"test": key(7)}, MEDICAL_DATA_ACTIVE_KEY_ID="test",
                   MEDICAL_IDENTITY_INDEX_KEY=key(8), USE_S3=False)
class DocumentArtifactConcurrencyTests(TransactionTestCase):
    def setUp(self):
        fixtures.DocumentArtifactGenerationTests.setUpTestData.__func__(self)
        fixtures.DocumentArtifactGenerationTests.setUp(self)

    prepare = fixtures.DocumentArtifactGenerationTests.prepare
    files = fixtures.DocumentArtifactGenerationTests.files

    def parallel(self, commands):
        barrier = Barrier(len(commands))

        def execute(command):
            close_old_connections()
            try:
                barrier.wait(timeout=10)
                try:
                    return command()
                except ValidationError:
                    return "quota"
                except MedicalAuditUnavailable:
                    return "audit"
            finally:
                connections.close_all()

        with ThreadPoolExecutor(max_workers=len(commands)) as executor:
            return [future.result(timeout=30) for future in [executor.submit(execute, command) for command in commands]]

    def test_duplicate_generation_returns_one_artifact_and_one_file(self):
        results = self.parallel([lambda: self.prepare(), lambda: self.prepare()])
        self.assertCountEqual([result[1] for result in results], [False, True])
        self.assertEqual(results[0][0].pk, results[1][0].pk)
        self.assertEqual(MedicalDocumentArtifact.objects.count(), 1)
        self.assertEqual(FileAttachment.objects.count(), 1)
        self.assertEqual(len(self.files()), 1)
        self.assertEqual(MedicalAuditEvent.objects.filter(action="read", document_version=self.version).count(), 2)

    def test_competing_languages_cannot_overconsume_remaining_storage(self):
        plan = SubscriptionPlan.objects.create(name="Synthetic document storage", code="document-race", limits_json={"storage_mb": 1})
        Subscription.objects.update_or_create(business=self.business, defaults={"plan": plan})
        with patch("apps.medical.document_artifact_services.render_draft_pdf", return_value=b"%PDF-1.4\n" + b"x" * (600 * 1024)):
            results = self.parallel([lambda: self.prepare(language="ru")[1], lambda: self.prepare(language="kk")[1]])
        self.assertCountEqual(results, [False, "quota"])
        self.assertEqual(MedicalDocumentArtifact.objects.count(), 1)
        self.assertEqual(FileAttachment.objects.count(), 1)
        self.assertEqual(len(self.files()), 1)

    def test_competing_languages_share_one_captured_logo(self):
        self.business.brand_logo_url = "https://clinic.example.test/logo.png"
        self.business.save(update_fields=["brand_logo_url"])
        self.version = template_fixtures.DocumentTemplateSourceTests.save(self, idempotency_key="logo-race")[0]
        output = BytesIO()
        Image.new("RGB", (80, 40), "#006450").save(output, format="PNG")
        with patch("apps.medical.document_artifact_services.capture_document_logo", return_value=output.getvalue()) as capture:
            results = self.parallel([lambda: self.prepare(language="ru"), lambda: self.prepare(language="kk")])
        capture.assert_called_once_with("https://clinic.example.test/logo.png")
        self.assertEqual([result[1] for result in results], [False, False])
        self.assertEqual(read_document_artifact_manifest(results[0][0])["logo"],
                         read_document_artifact_manifest(results[1][0])["logo"])
        self.assertEqual(MedicalDocumentArtifact.objects.count(), 2)
        self.assertEqual(len(self.files()), 2)

    def test_failed_audit_cleanup_does_not_remove_the_waiting_successful_request_file(self):
        first = iter([True, False])

        def audit(**kwargs):
            if next(first):
                raise MedicalAuditUnavailable()
            return write_patient_audit(**kwargs)

        with patch("apps.medical.document_artifact_services.write_patient_audit", side_effect=audit):
            results = self.parallel([lambda: self.prepare()[1], lambda: self.prepare()[1]])
        self.assertCountEqual(results, ["audit", False])
        item = MedicalDocumentArtifact.objects.get()
        with item.attachment.file.open("rb") as source:
            body = source.read()
        self.assertEqual(verify_document_artifact_bytes(item, body), body)
        self.assertEqual(FileAttachment.objects.count(), 1)
        self.assertEqual(len(self.files()), 1)
        self.assertEqual(MedicalAuditEvent.objects.filter(action="read", document_version=self.version).count(), 1)
