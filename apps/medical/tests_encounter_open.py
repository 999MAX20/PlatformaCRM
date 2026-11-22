from datetime import timedelta
from unittest.mock import patch

from django.db import DatabaseError
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.exceptions import NotFound, PermissionDenied, ValidationError

from apps.businesses.models import Business, RolePermission
from apps.clients.models import Client
from apps.core.domain_errors import InvalidTransition
from apps.core.idempotency import CRMCommandConflict
from apps.core.models import CRMCommandIdempotency
from . import tests_encounter_storage as fixtures
from . import tests_patient_services as crypto_fixtures
from .audit import MedicalAuditUnavailable
from .encounter_content import read_encounter_revision
from .encounter_services import open_primary_encounter, save_primary_encounter_draft
from .identity_crypto import MedicalKeyUnavailable
from .models import DentalMedicalRecord, MedicalAuditEvent, MedicalEncounter, MedicalEncounterRevision, PatientProfile


@override_settings(MEDICAL_DATA_KEYS={"test": crypto_fixtures.key(7)}, MEDICAL_DATA_ACTIVE_KEY_ID="test",
                   MEDICAL_IDENTITY_INDEX_KEY=crypto_fixtures.key(8))
class OpenPrimaryEncounterTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        fixtures.MedicalEncounterStorageTests.setUpTestData.__func__(cls)
        # Synthetic verified state; this fixture does not certify a real identity protocol.
        type(cls.patient).objects.filter(pk=cls.patient.pk).update(identity_status="verified",
            verified_at=timezone.now(), verified_by=cls.owner, verification_evidence_encrypted="synthetic-evidence")
        cls.patient.refresh_from_db()
        for action in ("create", "update"):
            RolePermission.objects.create(business_role=cls.role, resource="medical_records",
                action=action, scope="own", is_allowed=True)

    def open(self, **overrides):
        return open_primary_encounter(**(dict(actor=self.doctor, business_id=self.business.pk,
            patient_id=self.patient.pk, record_id=self.record.pk, appointment_id=self.appointment.pk,
            expected_patient_revision=1, expected_appointment_updated_at=self.appointment.updated_at, idempotency_key="open-synthetic",
            content={"complaints": "Private synthetic clinical text"}) | overrides))

    def test_open_creates_one_encrypted_draft_with_derived_author_and_branch(self):
        version, replay = self.open()
        encounter = version.encounter
        self.assertFalse(replay)
        self.assertEqual((encounter.primary_clinician_id, encounter.branch_id, encounter.revision,
                          encounter.state, version.author_id), (self.member.pk, self.first.pk, 1, "draft", self.doctor.pk))
        self.assertEqual(read_encounter_revision(version)["content"], {"complaints": "Private synthetic clinical text"})
        self.assertEqual(MedicalAuditEvent.objects.get().action, "encounter_opened")
        command = CRMCommandIdempotency.objects.get()
        self.assertEqual(command.response_json, {})
        self.assertNotIn("Private synthetic", str(command.__dict__))
        self.appointment.refresh_from_db()
        self.assertEqual((self.appointment.status, self.appointment.notes), ("created", ""))

    def test_replay_returns_initial_version_after_later_save(self):
        initial, _ = self.open()
        save_primary_encounter_draft(actor=self.doctor, business_id=self.business.pk, patient_id=self.patient.pk,
            encounter_id=initial.encounter_id, expected_revision=1, content={"plan": "Later"}, idempotency_key="save")
        replay, replayed = self.open()
        self.assertTrue(replayed)
        self.assertEqual(replay.pk, initial.pk)
        self.assertEqual(MedicalEncounter.objects.count(), 1)
        self.assertEqual(MedicalEncounterRevision.objects.count(), 2)
        self.assertEqual(MedicalAuditEvent.objects.count(), 2)

    def test_new_key_cannot_create_second_primary_encounter(self):
        self.open()
        with self.assertRaises(InvalidTransition):
            self.open(idempotency_key="other")
        with self.assertRaises(CRMCommandConflict):
            self.open(content={"plan": "Changed"})
        self.assertEqual(MedicalEncounter.objects.count(), 1)
        self.assertEqual(CRMCommandIdempotency.objects.count(), 1)

    def test_stale_patient_or_appointment_revision_creates_nothing(self):
        for override in ({"expected_patient_revision": 2}, {"expected_appointment_updated_at": self.appointment.updated_at - timedelta(seconds=1)}):
            with self.subTest(override=override), self.assertRaises(InvalidTransition):
                self.open(**override)
        self.assertFalse(MedicalEncounter.objects.exists())
        self.assertFalse(CRMCommandIdempotency.objects.exists())

    def test_owner_assistant_and_other_branch_are_denied(self):
        with self.assertRaises(PermissionDenied):
            self.open(actor=self.owner)
        self.assignment.kind = "assistant"
        self.assignment.save(update_fields=["kind"])
        with self.assertRaises(PermissionDenied):
            self.open()
        self.assignment.kind = "doctor"
        self.assignment.save(update_fields=["kind"])
        self.assignment.branches.clear()
        with self.assertRaises(PermissionDenied):
            self.open()
        self.assertFalse(MedicalEncounter.objects.exists())

    def test_booking_cancellation_and_role_revocation_deny_replay(self):
        self.open()
        self.appointment.status = "cancelled"
        self.appointment.save(update_fields=["status"])
        with self.assertRaises(PermissionDenied):
            self.open()
        self.appointment.status = "created"
        self.appointment.save(update_fields=["status"])
        self.assignment.revoked_at = timezone.now()
        self.assignment.save(update_fields=["revoked_at"])
        with self.assertRaises(PermissionDenied):
            self.open()

    def test_foreign_patient_record_business_and_wrong_appointment_are_denied(self):
        foreign = Business.objects.create(owner=self.owner, name="Foreign", slug="open-encounter-foreign")
        client = Client.objects.create(business=foreign, full_name="Foreign patient")
        patient = PatientProfile.objects.create(business=foreign, client=client, created_by=self.owner)
        record = DentalMedicalRecord.objects.create(business=foreign, patient=patient, number="F1", opened_by=self.owner)
        with self.assertRaises(NotFound):
            self.open(patient_id=patient.pk)
        for override in ({"record_id": record.pk}, {"business_id": foreign.pk},
                         {"appointment_id": self.appointment.pk + 999}):
            with self.subTest(override=override), self.assertRaises(PermissionDenied):
                self.open(**override)
        self.assertFalse(MedicalEncounter.objects.exists())

    def test_archived_record_rejects_open(self):
        self.record.state, self.record.archived_at, self.record.archived_by = "archived", timezone.now(), self.doctor
        self.record.save()
        with self.assertRaises(InvalidTransition):
            self.open()
        self.assertFalse(MedicalEncounter.objects.exists())

    def test_audit_failure_rolls_back_entire_open_and_retry_succeeds(self):
        with patch("apps.medical.audit.MedicalAuditEvent.objects.create", side_effect=DatabaseError("synthetic")):
            with self.assertRaises(MedicalAuditUnavailable):
                self.open()
        self.assertFalse(MedicalEncounter.objects.exists())
        self.assertFalse(MedicalEncounterRevision.objects.exists())
        self.assertFalse(CRMCommandIdempotency.objects.exists())
        self.open()

    def test_missing_key_rolls_back_encounter(self):
        with override_settings(MEDICAL_DATA_KEYS={}):
            with self.assertRaises(MedicalKeyUnavailable):
                self.open()
        self.assertFalse(MedicalEncounter.objects.exists())
        self.assertFalse(CRMCommandIdempotency.objects.exists())

    def test_empty_draft_is_allowed_invalid_shape_is_not(self):
        for override in ({"content": {"unsupported": "value"}}, {"record_id": True}, {"idempotency_key": ""}):
            with self.subTest(override=override), self.assertRaises(ValidationError):
                self.open(**override)
        version, _ = self.open(content=None)
        self.assertEqual(read_encounter_revision(version)["content"], {})

    def test_unverified_identity_blocks_clinical_write(self):
        type(self.patient).objects.filter(pk=self.patient.pk).update(identity_status="unverified",
            verified_at=None, verified_by=None, verification_evidence_encrypted="")
        with self.assertRaises(InvalidTransition):
            self.open()
        self.assertFalse(CRMCommandIdempotency.objects.exists())
        self.assertFalse(MedicalAuditEvent.objects.exists())
