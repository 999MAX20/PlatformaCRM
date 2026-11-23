from unittest import skipUnless

from django.db import connection
from django.test import TransactionTestCase, override_settings

from apps.core.domain_errors import InvalidTransition
from apps.core.models import FileAttachment
from . import tests_document_docx_export as fixtures
from . import tests_document_artifact_concurrency as races
from .document_review_services import transition_document_review
from .models import MedicalDocumentArtifact
from .tests_patient_services import key


@skipUnless(connection.vendor == "postgresql", "DOCX races require PostgreSQL row locks")
@override_settings(MEDICAL_DATA_KEYS={"test": key(7)}, MEDICAL_DATA_ACTIVE_KEY_ID="test",
                   MEDICAL_IDENTITY_INDEX_KEY=key(8), USE_S3=False)
class DocumentDOCXConcurrencyTests(TransactionTestCase):
    def setUp(self):
        fixtures.DocumentDOCXExportTests.setUpTestData.__func__(self)
        fixtures.DocumentDOCXExportTests.setUp(self)

    prepare = fixtures.DocumentDOCXExportTests.prepare
    read = fixtures.DocumentDOCXExportTests.read
    parallel = races.DocumentArtifactConcurrencyTests.parallel

    def test_duplicate_docx_generation_keeps_one_artifact_and_file(self):
        results = self.parallel([lambda: self.prepare(), lambda: self.prepare()])
        self.assertCountEqual([result[1] for result in results], [False, True])
        self.assertEqual(results[0][0].pk, results[1][0].pk)
        self.assertEqual(MedicalDocumentArtifact.objects.count(), 1)
        self.assertEqual(FileAttachment.objects.count(), 1)

    def test_review_transition_serializes_with_generation_and_prevents_later_download(self):
        def generate():
            try:
                return self.prepare()[0].pk
            except InvalidTransition:
                return "blocked"

        def review():
            transition_document_review(actor=self.doctor, business_id=self.business.pk, patient_id=self.patient.pk,
                version_id=self.version.pk, appointment_id=self.appointment.pk, expected_state_revision=1,
                target="ready_for_review", reason="", idempotency_key="docx-race-review")
            return "reviewed"

        result = self.parallel([generate, review])
        self.assertEqual(result[1], "reviewed")
        self.assertEqual(MedicalDocumentArtifact.objects.count(), 0 if result[0] == "blocked" else 1)
        with self.assertRaises(InvalidTransition):
            self.prepare()
        with self.assertRaises(InvalidTransition):
            self.read()
