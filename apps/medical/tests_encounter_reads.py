from unittest.mock import patch

from django.db import DatabaseError
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.exceptions import NotFound, PermissionDenied, ValidationError

from apps.businesses.models import Business
from apps.clients.models import Client
from . import tests_encounter_content as fixtures
from . import tests_patient_services as crypto_fixtures
from .audit import MedicalAuditUnavailable
from .encounter_reads import read_encounter_for_treating_clinician
from .identity_crypto import MedicalDataUnavailable
from .models import MedicalAuditEvent, MedicalEncounter, MedicalEncounterRevision, PatientProfile, TreatmentParticipation


@override_settings(MEDICAL_DATA_KEYS={"test": crypto_fixtures.key(7)}, MEDICAL_DATA_ACTIVE_KEY_ID="test")
class TreatingClinicianReadTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        fixtures.EncounterContentTests.setUpTestData.__func__(cls)

    append = fixtures.EncounterContentTests.append
    advance = fixtures.EncounterContentTests.advance

    def setUp(self):
        self.version = self.append()

    def read(self, **overrides):
        return read_encounter_for_treating_clinician(**(dict(actor=self.doctor, business_id=self.business.pk,
            patient_id=self.patient.pk, version_id=self.version.pk, appointment_id=self.appointment.pk) | overrides))

    def participation(self, **overrides):
        now = timezone.now()
        return TreatmentParticipation.objects.create(**(dict(patient=self.patient, member=self.member,
            branch=self.first, proposed_by=self.owner, proposed_at=now, accepted_at=now, state="active") | overrides))

    def test_read_returns_exact_version_and_writes_audit_on_every_read(self):
        for _ in range(2):
            result = self.read()
            self.assertEqual((result["version_id"], result["revision"], result["author_id"]),
                             (self.version.pk, 1, self.doctor.pk))
            self.assertEqual(result["content"]["plan"], "Оқу жоспары")
        self.assertEqual(MedicalAuditEvent.objects.filter(action="read", encounter_version=self.version).count(), 2)

    def test_history_and_other_author_are_readable_through_current_participation(self):
        self.advance()
        second = self.append(author=self.owner, content={"plan": "Another author"})
        self.appointment.status = "completed"
        self.appointment.save(update_fields=["status"])
        item = self.participation()
        first = self.read(appointment_id=None, participation_id=item.pk)
        later = self.read(appointment_id=None, participation_id=item.pk, version_id=second.pk)
        self.assertEqual(first["revision"], 1)
        self.assertEqual(later["author_id"], self.owner.pk)
        self.assertEqual(later["content"], {"plan": "Another author"})

    def test_patient_history_from_other_branch_does_not_require_target_write_access(self):
        # The historical branch is set before encrypting its new version.
        self.appointment.branch = self.second
        self.appointment.save(update_fields=["branch"])
        MedicalEncounter.objects.filter(pk=self.encounter_record.pk).update(branch=self.second)
        self.encounter_record.refresh_from_db()
        self.advance()
        second = self.append()
        item = self.participation()
        result = self.read(appointment_id=None, participation_id=item.pk, version_id=second.pk)
        self.assertEqual(result["revision"], 2)
        self.assertFalse(self.assignment.branches.filter(pk=self.second.pk).exists())

    def test_cancelled_basis_and_revoked_participation_deny_before_decrypt(self):
        self.appointment.status = "cancelled"
        self.appointment.save(update_fields=["status"])
        with patch("apps.medical.encounter_reads.read_encounter_revision") as decrypt:
            with self.assertRaises(PermissionDenied):
                self.read()
            item = self.participation()
            item.state, item.closed_at, item.closed_by = "ended", timezone.now(), self.doctor
            item.save()
            with self.assertRaises(PermissionDenied):
                self.read(appointment_id=None, participation_id=item.pk)
            decrypt.assert_not_called()
        self.assertFalse(MedicalAuditEvent.objects.exists())

    def test_owner_assistant_and_revoked_role_cannot_read(self):
        with self.assertRaises(PermissionDenied):
            self.read(actor=self.owner)
        self.assignment.kind = "assistant"
        self.assignment.save(update_fields=["kind"])
        with self.assertRaises(PermissionDenied):
            self.read()
        self.assignment.kind, self.assignment.revoked_at = "doctor", timezone.now()
        self.assignment.save(update_fields=["kind", "revoked_at"])
        with self.assertRaises(PermissionDenied):
            self.read()

    def test_foreign_patient_business_and_unrelated_version_are_denied(self):
        foreign = Business.objects.create(owner=self.owner, name="Foreign", slug="encounter-read-foreign")
        client = Client.objects.create(business=foreign, full_name="Foreign synthetic patient")
        patient = PatientProfile.objects.create(business=foreign, client=client, created_by=self.owner)
        with self.assertRaises(NotFound):
            self.read(patient_id=patient.pk)
        with self.assertRaises(PermissionDenied):
            self.read(business_id=foreign.pk)
        with self.assertRaises(PermissionDenied):
            self.read(version_id=self.version.pk + 999)
        self.assertFalse(MedicalAuditEvent.objects.exists())

    def test_no_or_ambiguous_basis_is_not_implicit_access(self):
        for override in ({"appointment_id": None}, {"participation_id": 1}, {"version_id": True}):
            with self.subTest(override=override), self.assertRaises(ValidationError):
                self.read(**override)

    def test_audit_failure_prevents_decrypt_and_return(self):
        with patch("apps.medical.audit.MedicalAuditEvent.objects.create", side_effect=DatabaseError("synthetic")):
            with patch("apps.medical.encounter_reads.read_encounter_revision") as decrypt:
                with self.assertRaises(MedicalAuditUnavailable):
                    self.read()
                decrypt.assert_not_called()

    def test_corrupt_ciphertext_is_not_returned_as_empty_success(self):
        MedicalEncounterRevision.objects.filter(pk=self.version.pk).update(content_encrypted="corrupt")
        with self.assertRaises(MedicalDataUnavailable):
            self.read()
        self.assertFalse(MedicalAuditEvent.objects.filter(result="success").exists())
