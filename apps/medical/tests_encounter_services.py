from unittest.mock import patch

from django.db import DatabaseError
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.exceptions import NotFound, PermissionDenied

from apps.businesses.models import Business, BusinessMember, RolePermission
from apps.clients.models import Client
from apps.core.domain_errors import InvalidTransition
from apps.core.idempotency import CRMCommandConflict
from apps.core.models import CRMCommandIdempotency
from . import tests_encounter_content as fixtures
from . import tests_patient_services as crypto_fixtures
from .audit import MedicalAuditUnavailable
from .encounter_content import read_encounter_revision
from .encounter_services import save_primary_encounter_draft
from .identity_crypto import MedicalKeyUnavailable
from .models import MedicalAuditEvent, MedicalEncounter, MedicalEncounterRevision, PatientProfile, TreatmentParticipation


@override_settings(MEDICAL_DATA_KEYS={"test": crypto_fixtures.key(7)}, MEDICAL_DATA_ACTIVE_KEY_ID="test",
                   MEDICAL_IDENTITY_INDEX_KEY=crypto_fixtures.key(8))
class PrimaryEncounterDraftTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        fixtures.EncounterContentTests.setUpTestData.__func__(cls)
        # Synthetic verified state; this fixture does not certify a real identity protocol.
        type(cls.patient).objects.filter(pk=cls.patient.pk).update(identity_status="verified",
            verified_at=timezone.now(), verified_by=cls.owner, verification_evidence_encrypted="synthetic-evidence")
        cls.patient.refresh_from_db()
        RolePermission.objects.create(business_role=cls.role, resource="medical_records",
            action="update", scope="own", is_allowed=True)

    def setUp(self):
        self.first_version = fixtures.EncounterContentTests.append(self)

    def save(self, **overrides):
        return save_primary_encounter_draft(**(dict(actor=self.doctor, business_id=self.business.pk,
            patient_id=self.patient.pk, encounter_id=self.encounter_record.pk, expected_revision=1,
            content={"complaints": "Private synthetic complaint"}, reason="Private synthetic reason",
            idempotency_key="private-key") | overrides))

    def test_save_preserves_history_calendar_and_private_command_ledger(self):
        version, replayed = self.save()
        self.assertFalse(replayed)
        self.assertEqual((version.revision, version.author_id), (2, self.doctor.pk))
        self.assertEqual(read_encounter_revision(version)["content"], {"complaints": "Private synthetic complaint"})
        self.assertIn("plan", read_encounter_revision(self.first_version)["content"])
        self.appointment.refresh_from_db()
        self.assertEqual((self.appointment.status, self.appointment.notes), ("created", ""))
        self.assertEqual(MedicalAuditEvent.objects.get().encounter_version_id, version.pk)
        command = CRMCommandIdempotency.objects.get()
        self.assertEqual(command.response_json, {})
        self.assertNotIn("Private synthetic", str(command.__dict__))
        self.assertNotEqual(command.idempotency_key, "private-key")

    def test_replay_returns_exact_saved_version_even_after_new_save(self):
        first, _ = self.save()
        self.save(expected_revision=2, content={"plan": "Later"}, idempotency_key="next")
        replay, replayed = self.save()
        self.assertTrue(replayed)
        self.assertEqual(replay.pk, first.pk)
        self.assertEqual(MedicalEncounterRevision.objects.count(), 3)
        self.assertEqual(MedicalAuditEvent.objects.count(), 2)

    def test_conflicting_replay_and_stale_revision_do_not_change_history(self):
        self.save()
        with self.assertRaises(CRMCommandConflict):
            self.save(content={"plan": "Different"})
        with self.assertRaises(InvalidTransition):
            self.save(idempotency_key="stale")
        self.assertEqual(MedicalEncounterRevision.objects.count(), 2)
        self.assertEqual(CRMCommandIdempotency.objects.count(), 1)

    def test_revoked_role_denies_replay(self):
        self.save()
        self.assignment.revoked_at = timezone.now()
        self.assignment.save(update_fields=["revoked_at"])
        with self.assertRaises(PermissionDenied):
            self.save()

    def test_owner_assistant_and_removed_branch_are_denied(self):
        with self.assertRaises(PermissionDenied):
            self.save(actor=self.owner)
        self.assignment.kind = "assistant"
        self.assignment.save(update_fields=["kind"])
        with self.assertRaises(PermissionDenied):
            self.save()
        self.assignment.kind = "doctor"
        self.assignment.save(update_fields=["kind"])
        self.assignment.branches.clear()
        with self.assertRaises(PermissionDenied):
            self.save()
        self.assertFalse(MedicalAuditEvent.objects.exists())

    def test_other_patient_and_encounter_do_not_leak_or_write(self):
        with self.assertRaises(NotFound):
            self.save(patient_id=self.patient.pk + 999)
        with self.assertRaises(PermissionDenied):
            self.save(encounter_id=self.encounter_record.pk + 999)
        self.assertFalse(CRMCommandIdempotency.objects.exists())

    def test_cancelled_booking_requires_independent_current_same_branch_participation(self):
        self.appointment.status = "cancelled"
        self.appointment.save(update_fields=["status"])
        with self.assertRaises(PermissionDenied):
            self.save()
        now = timezone.now()
        item = TreatmentParticipation.objects.create(patient=self.patient, member=self.member,
            branch=self.first, proposed_by=self.owner, state="active", proposed_at=now, accepted_at=now)
        self.save(participation_id=item.pk)
        item.state, item.closed_at, item.closed_by = "ended", timezone.now(), self.doctor
        item.save()
        with self.assertRaises(PermissionDenied):
            self.save(participation_id=item.pk)

    def test_foreign_patient_and_business_are_not_accepted(self):
        foreign = Business.objects.create(owner=self.owner, name="Foreign", slug="encounter-command-foreign")
        client = Client.objects.create(business=foreign, full_name="Foreign synthetic patient")
        patient = PatientProfile.objects.create(business=foreign, client=client, created_by=self.owner)
        with self.assertRaises(NotFound):
            self.save(patient_id=patient.pk)
        with self.assertRaises(PermissionDenied):
            self.save(business_id=foreign.pk)
        self.assertFalse(CRMCommandIdempotency.objects.exists())

    def test_primary_clinician_cannot_overwrite_another_clinician_encounter(self):
        other = BusinessMember.objects.create(business=self.business, user=self.owner, role="specialist")
        MedicalEncounter.objects.filter(pk=self.encounter_record.pk).update(primary_clinician=other)
        with self.assertRaises(PermissionDenied):
            self.save()
        self.assertEqual(MedicalEncounterRevision.objects.count(), 1)

    def test_participation_from_other_branch_does_not_authorize_write(self):
        self.assignment.branches.add(self.second)
        now = timezone.now()
        item = TreatmentParticipation.objects.create(patient=self.patient, member=self.member,
            branch=self.second, proposed_by=self.owner, state="active", proposed_at=now, accepted_at=now)
        with self.assertRaises(PermissionDenied):
            self.save(participation_id=item.pk)
        self.assertFalse(MedicalAuditEvent.objects.exists())

    def test_finalized_and_archived_record_reject_new_write(self):
        now = timezone.now()
        MedicalEncounter.objects.filter(pk=self.encounter_record.pk).update(state="finalized",
            ended_at=now, finalized_at=now, finalized_by=self.doctor)
        with self.assertRaises(InvalidTransition):
            self.save()
        MedicalEncounter.objects.filter(pk=self.encounter_record.pk).update(state="draft",
            ended_at=None, finalized_at=None, finalized_by=None)
        self.record.state, self.record.archived_at, self.record.archived_by = "archived", now, self.doctor
        self.record.save()
        with self.assertRaises(InvalidTransition):
            self.save()

    def test_audit_failure_rolls_back_revision_ciphertext_and_idempotency(self):
        with patch("apps.medical.audit.MedicalAuditEvent.objects.create", side_effect=DatabaseError("synthetic")):
            with self.assertRaises(MedicalAuditUnavailable):
                self.save()
        self.encounter_record.refresh_from_db()
        self.assertEqual(self.encounter_record.revision, 1)
        self.assertEqual(MedicalEncounterRevision.objects.count(), 1)
        self.assertFalse(CRMCommandIdempotency.objects.exists())
        self.save()

    def test_missing_crypto_key_does_not_advance_parent(self):
        with override_settings(MEDICAL_DATA_KEYS={}):
            with self.assertRaises(MedicalKeyUnavailable):
                self.save()
        self.encounter_record.refresh_from_db()
        self.assertEqual(self.encounter_record.revision, 1)
        self.assertEqual(MedicalEncounterRevision.objects.count(), 1)

    def test_unverified_identity_blocks_clinical_write(self):
        type(self.patient).objects.filter(pk=self.patient.pk).update(identity_status="unverified",
            verified_at=None, verified_by=None, verification_evidence_encrypted="")
        with self.assertRaises(InvalidTransition):
            self.save()
        self.assertFalse(CRMCommandIdempotency.objects.exists())
        self.assertFalse(MedicalAuditEvent.objects.exists())
