from datetime import datetime, timedelta, timezone
from unittest.mock import patch

from django.core.exceptions import ValidationError as ModelValidationError
from django.db import connection
from django.test import TestCase, override_settings
from django.test.utils import CaptureQueriesContext
from rest_framework.exceptions import ValidationError

from apps.businesses.models import BusinessMember
from apps.core.domain_errors import InvalidTransition
from . import tests_tooth_storage as fixtures
from .tests_patient_services import key
from .identity_crypto import MedicalDataUnavailable, MedicalKeyUnavailable
from .models import DentalToothHistory, DentalToothState
from .tooth_content import append_tooth_history, read_tooth_history, validate_tooth_content


@override_settings(MEDICAL_DATA_KEYS={"test": key(7)}, MEDICAL_DATA_ACTIVE_KEY_ID="test")
class DentalToothContentTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        fixtures.DentalToothStorageTests.setUpTestData.__func__(cls)
        BusinessMember.objects.get_or_create(business=cls.business, user=cls.owner, defaults={"role": "owner"})
        cls.state = DentalToothState.objects.create(business=cls.business, patient=cls.patient, tooth=11)

    def append(self, **overrides):
        return append_tooth_history(**(dict(tooth_state=self.state, encounter=self.encounter,
            author=self.doctor, observation="Синтетическое наблюдение / Оқу", reason="Private synthetic reason") | overrides))

    def advance(self):
        DentalToothState.objects.filter(pk=self.state.pk).update(revision=self.state.revision + 1)
        self.state.refresh_from_db()

    def test_roundtrip_has_no_plaintext_in_sql_or_stored_envelope(self):
        with CaptureQueriesContext(connection) as queries:
            history = self.append()
        for value in ("Синтетическое наблюдение", "Оқу", "Private synthetic reason"):
            self.assertNotIn(value, "\n".join(query["sql"] for query in queries))
            self.assertNotIn(value, history.content_encrypted)
        self.assertEqual(read_tooth_history(history), {"observation": "Синтетическое наблюдение / Оқу",
            "reason": "Private synthetic reason"})

    def test_observed_time_offset_uses_persisted_normalized_metadata(self):
        observed = datetime(2026, 11, 21, 14, 30, tzinfo=timezone(timedelta(hours=5)))
        history = self.append(observed_at=observed)
        self.assertEqual(history.observed_at, observed)
        self.assertIn("Оқу", read_tooth_history(history)["observation"])

    def test_new_revision_preserves_prior_value_and_author(self):
        first = self.append()
        self.advance()
        second = self.append(author=self.owner, observation="Second synthetic observation")
        self.assertEqual(second.previous_id, first.pk)
        self.assertEqual(read_tooth_history(first)["observation"], "Синтетическое наблюдение / Оқу")
        self.assertEqual(read_tooth_history(second)["observation"], "Second synthetic observation")
        first.refresh_from_db()
        self.assertEqual(first.author_id, self.doctor.pk)

    def test_stale_or_duplicate_revision_cannot_overwrite(self):
        first = self.append()
        with self.assertRaises(ModelValidationError):
            self.append(observation="Must not replace")
        DentalToothState.objects.filter(pk=self.state.pk).update(revision=2)
        with self.assertRaises(InvalidTransition):
            self.append()
        self.assertEqual(DentalToothHistory.objects.count(), 1)
        self.assertIn("Оқу", read_tooth_history(first)["observation"])

    def test_missing_predecessor_fails_without_writing(self):
        self.advance()
        with self.assertRaises(MedicalDataUnavailable):
            self.append()
        self.assertEqual(DentalToothHistory.objects.count(), 0)

    def test_swapping_ciphertext_between_revisions_fails(self):
        first = self.append()
        self.advance()
        second = self.append(observation="Second synthetic observation")
        DentalToothHistory.objects.filter(pk=second.pk).update(content_encrypted=first.content_encrypted)
        with self.assertRaises(MedicalDataUnavailable):
            read_tooth_history(second)

    def test_valid_but_tampered_metadata_fails(self):
        first = self.append()
        DentalToothState.objects.filter(pk=self.state.pk).update(tooth=12)
        with self.assertRaises(MedicalDataUnavailable):
            read_tooth_history(first)
        DentalToothState.objects.filter(pk=self.state.pk).update(tooth=11)
        DentalToothHistory.objects.filter(pk=first.pk).update(author=self.owner)
        with self.assertRaises(MedicalDataUnavailable):
            read_tooth_history(first)

    def test_encryption_failure_rolls_back_staging(self):
        from .tooth_content import encrypt_medical_value
        calls = 0
        def encrypt(*args, **kwargs):
            nonlocal calls
            calls += 1
            if calls == 2:
                raise MedicalKeyUnavailable()
            return encrypt_medical_value(*args, **kwargs)
        with patch("apps.medical.tooth_content.encrypt_medical_value", side_effect=encrypt):
            with self.assertRaises(MedicalKeyUnavailable):
                self.append()
        self.assertEqual(DentalToothHistory.objects.count(), 0)

    @override_settings(MEDICAL_DATA_KEYS={})
    def test_missing_keys_do_not_create_history(self):
        with self.assertRaises(MedicalKeyUnavailable):
            self.append()
        self.assertEqual(DentalToothHistory.objects.count(), 0)

    def test_empty_unknown_or_oversized_content_is_rejected(self):
        for content in ({}, {"observation": "", "reason": ""}, {"observation": "ok", "reason": False},
                        {"observation": "ok", "reason": "", "code": "invented"},
                        {"observation": "x" * 32769, "reason": ""}):
            with self.subTest(keys=list(content)), self.assertRaises(ValidationError):
                validate_tooth_content(content)
