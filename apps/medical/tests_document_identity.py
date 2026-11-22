import json
from unittest.mock import patch

from django.db import connection
from django.test import TestCase, override_settings
from django.test.utils import CaptureQueriesContext

from apps.clients.models import Client
from . import tests_document_template_source as fixtures
from . import tests_patient_services as crypto_fixtures
from .audit import MedicalAuditUnavailable
from .document_content import read_document_revision
from .identity_crypto import MedicalDataUnavailable, decrypt_medical_value, encrypt_medical_value, iin_digest
from .models import MedicalAuditEvent, MedicalDocument, MedicalDocumentRevision, PatientProfile


@override_settings(MEDICAL_DATA_KEYS={"test": crypto_fixtures.key(7)}, MEDICAL_DATA_ACTIVE_KEY_ID="test",
                   MEDICAL_IDENTITY_INDEX_KEY=crypto_fixtures.key(8))
class DocumentIdentityTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        fixtures.DocumentTemplateSourceTests.setUpTestData.__func__(cls)

    def setUp(self):
        fixtures.DocumentTemplateSourceTests.setUp(self)
        fixtures.DocumentTemplateSourceTests.approve(self)
        self.context = {"business_id": self.business.pk, "subject_id": self.patient.client_id}
        self.fields = {"date_of_birth": "1990-01-02", "sex": "synthetic", "address": "Private synthetic address"}
        PatientProfile.objects.filter(pk=self.patient.pk).update(
            demographics_encrypted=encrypt_medical_value(json.dumps(self.fields), purpose="demographics", **self.context),
            iin_encrypted=encrypt_medical_value("123456789012", purpose="iin", **self.context),
            iin_digest=iin_digest("123456789012", business_id=self.business.pk))

    def save(self, **overrides):
        return fixtures.DocumentTemplateSourceTests.save(self, **overrides)

    def payload(self, version):
        return json.loads(decrypt_medical_value(version.snapshot_encrypted, business_id=self.business.pk,
            subject_id=version.pk, purpose="document_snapshot"))

    def replace_payload(self, version, payload):
        version.snapshot_encrypted = encrypt_medical_value(json.dumps(payload), business_id=self.business.pk,
            subject_id=version.pk, purpose="document_snapshot")
        version.save(update_fields=["snapshot_encrypted"])

    def test_identity_and_exact_encounter_source_are_encrypted(self):
        with CaptureQueriesContext(connection) as queries:
            version, _ = self.save()
        snapshot = read_document_revision(version)
        identity = snapshot["patient_identity"]
        self.assertEqual(self.payload(version)["schema"], 3)
        self.assertEqual(identity["patient_id"], self.patient.pk)
        self.assertEqual(identity["client_id"], self.patient.client_id)
        self.assertEqual(identity["full_name"], self.patient.client.full_name)
        self.assertEqual(identity["revision"], self.patient.revision)
        self.assertEqual(identity["demographics"], self.fields)
        self.assertEqual(identity["iin"], "123456789012")
        self.assertEqual(snapshot["encounter_source"], {
            "version_id": self.first_version.pk, "revision": self.first_version.revision,
            "record_number": self.record.number, "started_at": self.encounter_record.started_at.isoformat(),
            "timezone": self.business.timezone})
        writes = "\n".join(row["sql"] for row in queries if not row["sql"].startswith("SELECT"))
        for private in ("Private synthetic address", "123456789012", "1990-01-02"):
            self.assertNotIn(private, writes)
            self.assertNotIn(private, version.snapshot_encrypted)

    def test_later_identity_record_timezone_edits_do_not_change_old_snapshot_or_replay(self):
        first, _ = self.save()
        before = read_document_revision(first)
        Client.objects.filter(pk=self.patient.client_id).update(full_name="Changed synthetic name")
        PatientProfile.objects.filter(pk=self.patient.pk).update(demographics_encrypted="corrupt-later")
        type(self.record).objects.filter(pk=self.record.pk).update(number="CHANGED")
        type(self.business).objects.filter(pk=self.business.pk).update(timezone="Asia/Almaty")
        self.assertEqual(read_document_revision(first), before)
        replay, replayed = self.save()
        self.assertTrue(replayed)
        self.assertEqual(replay.pk, first.pk)
        self.assertEqual(read_document_revision(replay), before)

    def test_new_version_captures_changed_identity_while_old_stays_unchanged(self):
        first, _ = self.save()
        Client.objects.filter(pk=self.patient.client_id).update(full_name="Changed synthetic name")
        second, _ = self.save(document_id=first.document_id, expected_document_revision=1,
            idempotency_key="identity-update", document_text="Updated text")
        self.assertNotEqual(read_document_revision(first)["patient_identity"]["full_name"], "Changed synthetic name")
        self.assertEqual(read_document_revision(second)["patient_identity"]["full_name"], "Changed synthetic name")

    def test_corrupt_or_foreign_identity_and_mismatched_index_roll_back(self):
        before = MedicalAuditEvent.objects.count()
        original = PatientProfile.objects.get(pk=self.patient.pk)
        for changes in ({"demographics_encrypted": "corrupt"},
                        {"demographics_encrypted": encrypt_medical_value("{}", business_id=self.business.pk + 999,
                            subject_id=self.patient.client_id, purpose="demographics")},
                        {"iin_digest": "a" * 64}, {"iin_encrypted": "corrupt"}):
            with self.subTest(changes=list(changes)):
                PatientProfile.objects.filter(pk=self.patient.pk).update(**changes)
                with self.assertRaises(MedicalDataUnavailable):
                    self.save()
                self.assertFalse(MedicalDocument.objects.exists())
                self.assertFalse(MedicalDocumentRevision.objects.exists())
                self.assertEqual(MedicalAuditEvent.objects.count(), before)
                PatientProfile.objects.filter(pk=self.patient.pk).update(
                    demographics_encrypted=original.demographics_encrypted,
                    iin_encrypted=original.iin_encrypted, iin_digest=original.iin_digest)

    def test_missing_optional_demographics_and_iin_stay_explicitly_absent(self):
        PatientProfile.objects.filter(pk=self.patient.pk).update(demographics_encrypted="", iin_encrypted="", iin_digest=None)
        version, _ = self.save()
        identity = read_document_revision(version)["patient_identity"]
        self.assertEqual(identity["demographics"], {})
        self.assertIsNone(identity["iin"])

    def test_invalid_decrypted_identity_shapes_fail_closed(self):
        for value in ({"date_of_birth": "1990-13-01"}, {"sex": 123}, {"address": []}, {"unsupported": "private"}):
            PatientProfile.objects.filter(pk=self.patient.pk).update(demographics_encrypted=
                encrypt_medical_value(json.dumps(value), purpose="demographics", **self.context))
            with self.subTest(value=value), self.assertRaises(MedicalDataUnavailable):
                self.save()
        self.assertFalse(MedicalDocumentRevision.objects.exists())

    def test_snapshot_binding_and_source_shapes_fail_closed(self):
        version, _ = self.save()
        original = self.payload(version)
        for key, field, value in (("patient_identity", "patient_id", self.patient.pk + 1),
                ("patient_identity", "revision", True), ("patient_identity", "verified_at", "invalid"),
                ("encounter_source", "version_id", self.first_version.pk + 1),
                ("encounter_source", "revision", True), ("encounter_source", "timezone", "invalid/zone")):
            payload = json.loads(json.dumps(original))
            payload["snapshot"][key][field] = value
            self.replace_payload(version, payload)
            with self.subTest(field=field), self.assertRaises(MedicalDataUnavailable):
                read_document_revision(version)

    def test_schema2_history_remains_readable_without_new_fields(self):
        version, _ = self.save()
        legacy = self.payload(version)
        legacy["schema"] = 2
        del legacy["snapshot"]["patient_identity"]
        del legacy["snapshot"]["encounter_source"]
        self.replace_payload(version, legacy)
        self.assertEqual(read_document_revision(version), legacy["snapshot"])

    def test_audit_failure_rolls_back_new_identity_snapshot(self):
        before = MedicalAuditEvent.objects.count()
        with patch("apps.medical.document_services.write_patient_audit", side_effect=MedicalAuditUnavailable()):
            with self.assertRaises(MedicalAuditUnavailable):
                self.save()
        self.assertFalse(MedicalDocument.objects.exists())
        self.assertFalse(MedicalDocumentRevision.objects.exists())
        self.assertEqual(MedicalAuditEvent.objects.count(), before)
