import json
from unittest.mock import patch

from django.db import IntegrityError, connection
from django.test import TestCase, override_settings
from django.test.utils import CaptureQueriesContext
from rest_framework.exceptions import ValidationError
from apps.core.domain_errors import InvalidTransition

from . import tests_encounter_storage as fixtures
from . import tests_patient_services as crypto_fixtures
from .encounter_content import append_encounter_revision, read_encounter_revision, validate_clinical_draft
from .identity_crypto import MedicalDataUnavailable, MedicalKeyUnavailable, encrypt_medical_value
from .models import MedicalEncounter, MedicalEncounterRevision


@override_settings(MEDICAL_DATA_KEYS={"test": crypto_fixtures.key(7)}, MEDICAL_DATA_ACTIVE_KEY_ID="test")
class EncounterContentTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        fixtures.MedicalEncounterStorageTests.setUpTestData.__func__(cls)
        cls.encounter_record = MedicalEncounter.objects.create(business=cls.business, patient=cls.patient,
            record=cls.record, appointment=cls.appointment, branch=cls.first, primary_clinician=cls.member)

    def append(self, **overrides):
        return append_encounter_revision(**(dict(encounter=self.encounter_record, author=self.doctor,
            content={"complaints": "Учебные жалобы\nSynthetic text", "plan": "Оқу жоспары"},
            reason="Synthetic private correction") | overrides))

    def advance(self):
        MedicalEncounter.objects.filter(pk=self.encounter_record.pk).update(revision=self.encounter_record.revision + 1)
        self.encounter_record.refresh_from_db()

    def test_round_trip_preserves_unicode_without_plaintext_database_queries(self):
        with CaptureQueriesContext(connection) as queries:
            version = self.append()
        sql = "\n".join(row["sql"] for row in queries)
        for plaintext in ("Учебные жалобы", "Synthetic text", "Оқу жоспары", "Synthetic private correction"):
            self.assertNotIn(plaintext, sql)
            self.assertNotIn(plaintext, version.content_encrypted + version.reason_encrypted)
        self.assertEqual(read_encounter_revision(version), {"content": {"complaints": "Учебные жалобы\nSynthetic text",
            "plan": "Оқу жоспары"}, "reason": "Synthetic private correction"})
        self.appointment.refresh_from_db()
        self.assertEqual((self.appointment.status, self.appointment.notes), ("created", ""))

    def test_later_revision_does_not_overwrite_earlier_content_or_author(self):
        first = self.append()
        self.advance()
        second = self.append(author=self.owner, content={"plan": "New synthetic draft"})
        self.assertNotEqual(first.pk, second.pk)
        self.assertIn("complaints", read_encounter_revision(first)["content"])
        self.assertEqual(read_encounter_revision(second)["content"], {"plan": "New synthetic draft"})
        first.refresh_from_db()
        self.assertEqual(first.author_id, self.doctor.pk)

    def test_duplicate_revision_cannot_replace_history(self):
        first = self.append()
        with self.assertRaises(IntegrityError):
            self.append(content={"diagnosis": "Must not replace"})
        self.assertEqual(MedicalEncounterRevision.objects.count(), 1)
        self.assertNotIn("diagnosis", read_encounter_revision(first)["content"])

    def test_swapped_ciphertexts_are_rejected_even_with_same_encounter(self):
        first = self.append()
        self.advance()
        second = self.append(content={"diagnosis": "Other draft"})
        MedicalEncounterRevision.objects.filter(pk=second.pk).update(content_encrypted=first.content_encrypted)
        with self.assertRaises(MedicalDataUnavailable):
            read_encounter_revision(second)

    def test_author_metadata_tampering_is_detected(self):
        version = self.append()
        MedicalEncounterRevision.objects.filter(pk=version.pk).update(author=self.owner)
        with self.assertRaises(MedicalDataUnavailable):
            read_encounter_revision(version)

    def test_reason_cannot_be_replaced_by_content_envelope_or_removed(self):
        version = self.append()
        for cipher in (version.content_encrypted, ""):
            MedicalEncounterRevision.objects.filter(pk=version.pk).update(reason_encrypted=cipher)
            with self.subTest(cipher=bool(cipher)), self.assertRaises(MedicalDataUnavailable):
                read_encounter_revision(version)

    def test_authenticated_but_malformed_snapshot_fails_closed(self):
        version = self.append()
        encrypted = encrypt_medical_value(json.dumps({"schema": 1, "content": {}}),
            business_id=self.business.pk, subject_id=version.pk, purpose="encounter_content")
        MedicalEncounterRevision.objects.filter(pk=version.pk).update(content_encrypted=encrypted)
        with self.assertRaises(MedicalDataUnavailable):
            read_encounter_revision(version)

    def test_validation_does_not_echo_clinical_values_and_allows_empty_draft(self):
        self.assertEqual(validate_clinical_draft({}), {})
        for content in ({"SECRET_FIELD": "private"}, {"plan": 123}, {"diagnosis": "x" * 32769}, []):
            with self.subTest(kind=type(content).__name__), self.assertRaises(ValidationError) as failure:
                self.append(content=content)
            self.assertNotIn("SECRET_FIELD", str(failure.exception))
        self.assertEqual(MedicalEncounterRevision.objects.count(), 0)
        self.assertEqual(read_encounter_revision(self.append(content={}, reason="")), {"content": {}, "reason": ""})

    def test_missing_keys_do_not_persist_staging_or_empty_revision(self):
        with override_settings(MEDICAL_DATA_KEYS={}):
            with self.assertRaises(MedicalKeyUnavailable):
                self.append()
        self.assertEqual(MedicalEncounterRevision.objects.count(), 0)

    def test_failure_after_staging_rolls_back_allocated_revision(self):
        calls = 0
        def encrypt(value, **kwargs):
            nonlocal calls
            calls += 1
            if calls == 2:
                raise MedicalKeyUnavailable()
            return encrypt_medical_value(value, **kwargs)
        with patch("apps.medical.encounter_content.encrypt_medical_value", side_effect=encrypt):
            with self.assertRaises(MedicalKeyUnavailable):
                self.append()
        self.assertEqual(calls, 2)
        self.assertEqual(MedicalEncounterRevision.objects.count(), 0)

    def test_stale_encounter_snapshot_cannot_append_revision(self):
        self.append()
        stale = MedicalEncounter.objects.get(pk=self.encounter_record.pk)
        self.advance()
        with self.assertRaises(InvalidTransition):
            self.append(encounter=stale)
        self.assertEqual(MedicalEncounterRevision.objects.count(), 1)

    def test_parent_revision_rollback_is_not_accepted_as_current_history(self):
        self.append()
        self.advance()
        second = self.append()
        MedicalEncounter.objects.filter(pk=self.encounter_record.pk).update(revision=1)
        with self.assertRaises(MedicalDataUnavailable):
            read_encounter_revision(second)

    def test_inconsistent_parent_branch_fails_closed_on_read(self):
        version = self.append()
        MedicalEncounter.objects.filter(pk=self.encounter_record.pk).update(branch=self.second)
        with self.assertRaises(MedicalDataUnavailable):
            read_encounter_revision(version)
