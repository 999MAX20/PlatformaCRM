from unittest.mock import patch

from django.core.exceptions import ValidationError as ModelValidationError
from django.db import DatabaseError, IntegrityError, transaction
from django.test import TestCase, override_settings
from rest_framework.exceptions import ValidationError

from apps.core.models import FileAttachment
from . import tests_encounter_content as fixtures
from . import tests_patient_services as crypto
from .audit import MedicalAuditUnavailable, write_patient_audit
from .file_content import append_file_revision, read_file_metadata, validate_file_metadata
from .identity_crypto import MedicalDataUnavailable
from .models import MedicalAttachment, MedicalAttachmentRevision, MedicalAuditEvent


@override_settings(MEDICAL_DATA_KEYS={"test": crypto.key(7)}, MEDICAL_DATA_ACTIVE_KEY_ID="test")
class MedicalFileStorageTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        fixtures.EncounterContentTests.setUpTestData.__func__(cls)
        cls.blob = FileAttachment.objects.create(business=cls.business, uploaded_by=cls.doctor,
            file="private/attachments/synthetic.pdf", original_name="attachment.pdf", content_type="application/pdf",
            size=10, entity_type="medical_attachment", entity_id="opaque")
        cls.item = MedicalAttachment.objects.create(business=cls.business, patient=cls.patient, record=cls.record,
            branch=cls.first, encounter=cls.encounter_record, attachment=cls.blob, created_by=cls.doctor)

    def metadata(self, **overrides):
        return {"name": "Учебный снимок.pdf", "description": "Synthetic private description",
                "teeth": [11, 21], "reason": ""} | overrides

    def append(self, **metadata):
        return append_file_revision(medical_file=self.item, author=self.doctor, metadata=self.metadata(**metadata))

    def test_encrypted_metadata_versions_preserve_previous_name_teeth_and_author(self):
        first = self.append()
        self.assertNotIn("Учебный", first.metadata_encrypted)
        self.assertNotIn("Synthetic private", first.metadata_encrypted)
        MedicalAttachment.objects.filter(pk=self.item.pk).update(revision=2)
        self.item.refresh_from_db()
        second = self.append(name="Changed.pdf", teeth=[55], reason="Synthetic correction")
        self.assertEqual(read_file_metadata(first), self.metadata())
        self.assertEqual(read_file_metadata(second)["teeth"], [55])
        self.blob.refresh_from_db()
        self.assertEqual((self.blob.original_name, self.blob.file.name),
                         ("attachment.pdf", "private/attachments/synthetic.pdf"))
        self.assertEqual(first.author_id, self.doctor.pk)

    def test_duplicate_revision_and_missing_correction_reason_do_not_create_history(self):
        self.append()
        with self.assertRaises(ModelValidationError):
            # full_clean reports the duplicate before the database insert in callers that validate models.
            MedicalAttachmentRevision(medical_file=self.item, revision=1, author=self.doctor,
                                      metadata_encrypted="opaque").full_clean()
        MedicalAttachment.objects.filter(pk=self.item.pk).update(revision=2)
        self.item.refresh_from_db()
        with self.assertRaises(ValidationError):
            self.append(description="Unexplained change")
        self.assertEqual(MedicalAttachmentRevision.objects.count(), 1)

    def test_path_controls_unknown_duplicate_or_non_integer_teeth_are_rejected(self):
        for values in ({"name": "../x.pdf"}, {"name": "x\r\n.pdf"}, {"name": ""},
                       {"teeth": [19]}, {"teeth": [True]}, {"teeth": [11, 11]}, {"teeth": "11"}):
            with self.subTest(values=values), self.assertRaises(ValidationError):
                validate_file_metadata(self.metadata(**values))

    def test_generic_storage_and_wrong_encounter_links_cannot_become_medical(self):
        self.blob.entity_type = "client"
        self.blob.save(update_fields=["entity_type"])
        self.item.refresh_from_db()
        with self.assertRaises(ModelValidationError):
            self.item.clean()
        self.blob.entity_type = "medical_attachment"
        self.blob.save(update_fields=["entity_type"])
        self.item.refresh_from_db()
        self.item.branch_id = self.second.pk
        with self.assertRaises(ModelValidationError):
            self.item.clean()

    def test_ciphertext_cannot_be_substituted_between_versions(self):
        first = self.append()
        MedicalAttachment.objects.filter(pk=self.item.pk).update(revision=2)
        self.item.refresh_from_db()
        second = self.append(reason="Synthetic correction")
        second.metadata_encrypted = first.metadata_encrypted
        with self.assertRaises(MedicalDataUnavailable):
            read_file_metadata(second)

    def test_audit_requires_exact_file_version_and_failure_is_closed(self):
        version = self.append()
        event = write_patient_audit(actor=self.doctor, business=self.business, patient=self.patient,
                                   action="file_uploaded", file_version=version)
        self.assertEqual(event.file_version_id, version.pk)
        with self.assertRaises(ValueError):
            write_patient_audit(actor=self.owner, business=self.business, patient=self.patient,
                                action="file_uploaded", file_version=version)
        with patch("apps.medical.audit.MedicalAuditEvent.objects.create", side_effect=DatabaseError()):
            with self.assertRaises(MedicalAuditUnavailable):
                write_patient_audit(actor=self.doctor, business=self.business, patient=self.patient,
                                    action="read", file_version=version)
        with self.assertRaises(IntegrityError), transaction.atomic():
            MedicalAuditEvent.objects.create(actor=self.doctor, business=self.business, patient=self.patient,
                                             patient_revision=1, action="file_uploaded", result="success")
