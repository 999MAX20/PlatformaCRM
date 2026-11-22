from unittest.mock import patch

from django.db import IntegrityError, connection, transaction
from django.test import TestCase, override_settings
from django.test.utils import CaptureQueriesContext
from rest_framework.exceptions import ValidationError

from apps.businesses.models import BusinessMember
from apps.core.domain_errors import InvalidTransition
from . import tests_encounter_content as fixtures
from . import tests_patient_services as crypto_fixtures
from .document_content import append_document_revision, read_document_revision
from .identity_crypto import MedicalDataUnavailable, MedicalKeyUnavailable
from .models import MedicalDocument, MedicalDocumentRevision, MedicalEncounter


@override_settings(MEDICAL_DATA_KEYS={"test": crypto_fixtures.key(7)}, MEDICAL_DATA_ACTIVE_KEY_ID="test")
class DocumentContentTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        fixtures.EncounterContentTests.setUpTestData.__func__(cls)
        cls.source = fixtures.EncounterContentTests.append(cls)
        cls.document = MedicalDocument.objects.create(business=cls.business,
            encounter=cls.encounter_record, template_code="synthetic_form")

    def append(self, **overrides):
        return append_document_revision(**(dict(document=self.document, source_version=self.source,
            author=self.doctor, template={"code": "synthetic_form", "version": 1,
                "title": "Учебный документ", "text": "Тек үлгі / Synthetic template"},
            reason="Synthetic document reason") | overrides))

    def test_encrypted_round_trip_snapshots_real_clinic_and_source_without_calendar_write(self):
        self.business.legal_name = "Synthetic private legal name"
        self.business.save(update_fields=["legal_name"])
        with CaptureQueriesContext(connection) as queries:
            version = self.append()
        sql = "\n".join(row["sql"] for row in queries if not row["sql"].startswith("SELECT"))
        for value in ("Учебный документ", "Тек үлгі", "Synthetic private legal name", "Учебные жалобы"):
            self.assertNotIn(value, sql)
            self.assertNotIn(value, version.snapshot_encrypted)
        snapshot = read_document_revision(version)
        self.assertEqual(snapshot["business"]["legal_name"], self.business.legal_name)
        self.assertEqual(snapshot["performed_by"]["member_id"], self.member.pk)
        self.assertEqual(snapshot["prepared_by"]["user_id"], self.doctor.pk)
        self.assertEqual(snapshot["clinical"]["plan"], "Оқу жоспары")
        self.document.refresh_from_db()
        self.appointment.refresh_from_db()
        self.assertEqual((self.document.revision, self.document.state, self.appointment.status), (1, "draft", "created"))

    def test_later_brand_author_and_template_changes_preserve_earlier_version(self):
        first = self.append()
        before = read_document_revision(first)
        self.business.legal_name = "Changed clinic"
        self.business.brand_logo_url = "https://example.invalid/new-logo.png"
        self.business.save(update_fields=["legal_name", "brand_logo_url"])
        self.first.address = "Changed branch"
        self.first.save(update_fields=["address"])
        self.doctor.full_name = "Changed clinician"
        self.doctor.save(update_fields=["full_name"])
        self.document.refresh_from_db()
        second = self.append(template={"code": "synthetic_form", "version": 2, "title": "New", "text": "New"})
        self.assertEqual(read_document_revision(first), before)
        self.assertEqual(read_document_revision(second)["business"]["legal_name"], "Changed clinic")
        self.assertEqual(read_document_revision(second)["branch"]["address"], "Changed branch")
        self.assertEqual(read_document_revision(second)["template"]["version"], 2)

    def test_stale_document_does_not_create_another_revision(self):
        self.append()
        with self.assertRaises(InvalidTransition):
            self.append()
        self.assertEqual(MedicalDocumentRevision.objects.count(), 1)

    def test_stale_clinical_source_blocks_new_snapshot(self):
        MedicalEncounter.objects.filter(pk=self.encounter_record.pk).update(revision=2)
        with self.assertRaises(InvalidTransition):
            self.append()
        self.assertFalse(MedicalDocumentRevision.objects.exists())

    def test_document_keeps_original_clinical_text_after_source_changes(self):
        first = self.append()
        before = read_document_revision(first)
        fixtures.EncounterContentTests.advance(self)
        self.source = fixtures.EncounterContentTests.append(self, content={"plan": "Later plan"})
        self.document.refresh_from_db()
        second = self.append()
        self.assertEqual(read_document_revision(first), before)
        self.assertEqual(read_document_revision(second)["clinical"], {"plan": "Later plan"})

    def test_different_encounter_source_is_rejected(self):
        from .encounter_content import append_encounter_revision
        self.appointment.pk = None
        self.appointment.save()
        encounter = MedicalEncounter.objects.create(business=self.business, patient=self.patient,
            record=self.record, appointment=self.appointment, branch=self.first, primary_clinician=self.member)
        source = append_encounter_revision(encounter=encounter, author=self.doctor, content={})
        with self.assertRaises(ValidationError):
            self.append(source_version=source)
        self.assertFalse(MedicalDocumentRevision.objects.exists())

    def test_read_rejects_reassigned_patient_relation(self):
        from apps.clients.models import Client
        from .models import PatientProfile
        first = self.append()
        client = Client.objects.create(business=self.business, full_name="Other synthetic patient")
        patient = PatientProfile.objects.create(business=self.business, client=client, created_by=self.owner)
        MedicalEncounter.objects.filter(pk=self.encounter_record.pk).update(patient=patient)
        with self.assertRaises(MedicalDataUnavailable):
            read_document_revision(first)

    def test_inactive_or_nonmember_author_is_rejected(self):
        BusinessMember.objects.filter(pk=self.member.pk).update(is_active=False)
        with self.assertRaises(ValidationError):
            self.append()
        self.assertFalse(MedicalDocumentRevision.objects.exists())

    def test_mismatched_business_is_rejected_before_snapshot(self):
        from apps.businesses.models import Business
        other = Business.objects.create(owner=self.owner, name="Other", slug="other-document-tenant")
        wrong = MedicalDocument.objects.create(business=other, encounter=self.encounter_record, template_code="synthetic_form")
        from django.core.exceptions import ValidationError as ModelValidationError
        with self.assertRaises(ModelValidationError):
            self.append(document=wrong)
        self.assertFalse(MedicalDocumentRevision.objects.exists())

    def test_swapped_ciphertext_and_author_metadata_fail_closed(self):
        first = self.append()
        self.document.refresh_from_db()
        second = self.append()
        MedicalDocumentRevision.objects.filter(pk=second.pk).update(snapshot_encrypted=first.snapshot_encrypted)
        with self.assertRaises(MedicalDataUnavailable):
            read_document_revision(second)
        MedicalDocumentRevision.objects.filter(pk=first.pk).update(author=self.owner)
        with self.assertRaises(MedicalDataUnavailable):
            read_document_revision(first)

    def test_atomic_failure_does_not_leave_staging_or_advance_document(self):
        from .identity_crypto import encrypt_medical_value
        calls = 0
        def encrypt(value, **kwargs):
            nonlocal calls
            calls += 1
            if calls == 2:
                raise MedicalKeyUnavailable()
            return encrypt_medical_value(value, **kwargs)
        with patch("apps.medical.document_content.encrypt_medical_value", side_effect=encrypt):
            with self.assertRaises(MedicalKeyUnavailable):
                self.append()
        self.document.refresh_from_db()
        self.assertEqual(self.document.revision, 0)
        self.assertFalse(MedicalDocumentRevision.objects.exists())

    def test_caller_transaction_failure_rolls_back_version_and_revision(self):
        with self.assertRaises(RuntimeError), transaction.atomic():
            self.append()
            raise RuntimeError("Synthetic audit failure")
        self.document.refresh_from_db()
        self.assertEqual(self.document.revision, 0)
        self.assertFalse(MedicalDocumentRevision.objects.exists())

    def test_template_validation_does_not_echo_input_or_accept_signature_state(self):
        for template in ({}, {"code": "synthetic_form", "version": True, "title": "private", "text": "private"},
                         {"code": "other", "version": 1, "title": "private", "text": "private"}):
            with self.subTest(template=template), self.assertRaises(ValidationError) as error:
                self.append(template=template)
            self.assertNotIn("private", str(error.exception))
        with self.assertRaises(IntegrityError), transaction.atomic():
            MedicalDocument.objects.filter(pk=self.document.pk).update(state="signed")

    def test_duplicate_version_and_missing_ciphertext_rejected_by_database(self):
        first = self.append()
        for revision, content in ((first.revision, first.snapshot_encrypted), (2, ""), (0, first.snapshot_encrypted)):
            with self.subTest(revision=revision), self.assertRaises(IntegrityError), transaction.atomic():
                MedicalDocumentRevision.objects.create(document=self.document, source_version=self.source,
                    author=self.doctor, revision=revision, snapshot_encrypted=content)

    def test_missing_key_does_not_allocate_snapshot(self):
        with override_settings(MEDICAL_DATA_KEYS={}):
            with self.assertRaises(MedicalKeyUnavailable):
                self.append()
        self.assertFalse(MedicalDocumentRevision.objects.exists())
