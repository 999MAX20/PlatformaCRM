from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from unittest import skipUnless

from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import close_old_connections, connection, connections
from django.test import TransactionTestCase, override_settings
from rest_framework.exceptions import ValidationError

from apps.billing.models import Subscription, SubscriptionPlan
from apps.core.domain_errors import InvalidTransition
from apps.core.models import FileAttachment
from . import tests_file_upload as fixtures
from . import tests_patient_services as crypto
from .file_services import update_medical_file_metadata
from .models import MedicalAttachment, MedicalAttachmentRevision, MedicalAuditEvent


@skipUnless(connection.vendor == "postgresql", "File races require PostgreSQL row locks")
@override_settings(MEDICAL_DATA_KEYS={"test": crypto.key(7)}, MEDICAL_DATA_ACTIVE_KEY_ID="test",
                   MEDICAL_IDENTITY_INDEX_KEY=crypto.key(8), USE_S3=False)
class MedicalFileConcurrencyTests(TransactionTestCase):
    def setUp(self):
        fixtures.MedicalFileUploadTests.setUpTestData.__func__(self)
        fixtures.MedicalFileUploadTests.setUp(self)

    upload = fixtures.MedicalFileUploadTests.upload
    stored_files = fixtures.MedicalFileUploadTests.stored_files

    def parallel(self, commands):
        barrier = Barrier(len(commands))

        def execute(command):
            close_old_connections()
            try:
                barrier.wait(timeout=10)
                try:
                    return command()
                except InvalidTransition:
                    return "conflict"
                except ValidationError:
                    return "validation"
            finally:
                connections.close_all()

        with ThreadPoolExecutor(max_workers=len(commands)) as executor:
            futures = [executor.submit(execute, command) for command in commands]
            return [future.result(timeout=30) for future in futures]

    def test_duplicate_upload_creates_one_blob_and_one_exact_audit(self):
        self.assertCountEqual(self.parallel([lambda: self.upload()[1], lambda: self.upload()[1]]), [False, True])
        self.assertEqual(MedicalAttachment.objects.count(), 1)
        self.assertEqual(len(self.stored_files()), 1)
        self.assertEqual(MedicalAuditEvent.objects.filter(action="file_uploaded").count(), 1)

    def test_competing_metadata_edits_keep_one_new_version(self):
        first, _ = self.upload()

        def edit(key):
            return update_medical_file_metadata(actor=self.doctor, business_id=self.business.pk,
                patient_id=self.patient.pk, appointment_id=self.appointment.pk, file_id=first.medical_file_id,
                expected_revision=1, description=key, teeth=[21], reason="Synthetic correction",
                idempotency_key=key)[1]

        self.assertCountEqual(self.parallel([lambda: edit("first"), lambda: edit("second")]), [False, "conflict"])
        self.assertEqual(MedicalAttachmentRevision.objects.count(), 2)
        self.assertEqual(MedicalAuditEvent.objects.filter(action="file_metadata_updated").count(), 1)

    def test_simultaneous_uploads_cannot_both_consume_remaining_quota(self):
        plan = SubscriptionPlan.objects.create(name="Synthetic storage", code="medical-file-test", limits_json={"storage_mb": 1})
        Subscription.objects.update_or_create(business=self.business, defaults={"plan": plan})

        def upload(key):
            return self.upload(idempotency_key=key,
                uploaded_file=SimpleUploadedFile("test.pdf", b"%PDF-1.4\n" + b"x" * (600 * 1024), "application/pdf"))[1]

        self.assertCountEqual(self.parallel([lambda: upload("first"), lambda: upload("second")]), [False, "validation"])
        self.assertEqual(FileAttachment.objects.count(), 1)
        self.assertEqual(len(self.stored_files()), 1)
