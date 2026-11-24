from unittest.mock import patch

from django.db import DatabaseError
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.exceptions import NotFound, PermissionDenied, ValidationError

from apps.businesses.models import Business
from apps.core.domain_errors import InvalidTransition
from apps.core.idempotency import CRMCommandConflict
from apps.core.models import CRMCommandIdempotency
from . import tests_encounter_services as fixtures
from .tests_patient_services import key
from .audit import MedicalAuditUnavailable
from .identity_crypto import MedicalKeyUnavailable
from .models import DentalToothHistory, DentalToothState, MedicalAuditEvent, PatientProfile, TreatmentParticipation
from .tooth_content import read_tooth_history
from .tooth_policy import ToothNotationUnavailable
from .tooth_services import save_primary_tooth_observation


@override_settings(MEDICAL_DATA_KEYS={"test": key(7)}, MEDICAL_DATA_ACTIVE_KEY_ID="test",
                   MEDICAL_IDENTITY_INDEX_KEY=key(8), MEDICAL_TOOTH_SURFACE_POLICIES="")
class PrimaryToothObservationTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        fixtures.PrimaryEncounterDraftTests.setUpTestData.__func__(cls)

    def save(self, **overrides):
        return save_primary_tooth_observation(**(dict(actor=self.doctor, business_id=self.business.pk,
            patient_id=self.patient.pk, encounter_id=self.encounter_record.pk, tooth=11,
            expected_patient_revision=1, expected_encounter_revision=1, expected_tooth_revision=0,
            observation="Private synthetic tooth observation", reason="Private synthetic reason",
            idempotency_key="synthetic-tooth") | overrides))

    def test_save_writes_encrypted_history_and_audit_without_calendar_money_or_plaintext_ledger(self):
        history, replay = self.save()
        self.assertFalse(replay)
        self.assertEqual((history.revision, history.author_id, history.encounter_id), (1, self.doctor.pk, self.encounter_record.pk))
        self.assertEqual(MedicalAuditEvent.objects.get().tooth_history_id, history.pk)
        self.assertIn("Private synthetic", read_tooth_history(history)["observation"])
        command = CRMCommandIdempotency.objects.get()
        self.assertEqual(command.response_json, {})
        self.assertNotIn("Private synthetic", str(command.__dict__))
        self.assertNotEqual(command.idempotency_key, "synthetic-tooth")
        self.appointment.refresh_from_db()
        self.assertEqual((self.appointment.status, self.appointment.notes), ("created", ""))
        self.encounter_record.refresh_from_db()
        self.assertEqual(self.encounter_record.revision, 1)

    def test_replay_returns_exact_initial_version_after_later_change(self):
        first, _ = self.save()
        second, _ = self.save(expected_tooth_revision=1, observation="Later observation", idempotency_key="later")
        replay, was_replayed = self.save()
        self.assertTrue(was_replayed)
        self.assertEqual(replay.pk, first.pk)
        self.assertEqual(second.previous_id, first.pk)
        self.assertEqual(DentalToothHistory.objects.count(), 2)
        self.assertEqual(MedicalAuditEvent.objects.count(), 2)

    def test_explicit_states_preserve_legacy_history_and_omitted_state(self):
        legacy, _ = self.save()
        self.assertNotIn("tooth_status", read_tooth_history(legacy))
        for revision, status in enumerate(("not_examined", "no_findings", "observation", "absent"), start=1):
            text = "Synthetic finding" if status == "observation" else ""
            row, _ = self.save(expected_tooth_revision=revision, tooth_status=status,
                observation=text, idempotency_key=status)
            self.assertEqual(read_tooth_history(row)["tooth_status"], status)
            self.assertNotIn(status, row.content_encrypted)
        latest, _ = self.save(expected_tooth_revision=5, idempotency_key="legacy-client")
        self.assertEqual(read_tooth_history(latest)["tooth_status"], "absent")
        self.assertNotIn("tooth_status", read_tooth_history(legacy))
        replay, repeated = self.save(expected_tooth_revision=4, tooth_status="absent",
            observation="", idempotency_key="absent")
        self.assertTrue(repeated)
        self.assertEqual(replay.revision, 5)
        with self.assertRaises(CRMCommandConflict):
            self.save(expected_tooth_revision=4, tooth_status="no_findings", observation="", idempotency_key="absent")

    def test_state_validation_and_denied_role_leave_no_history(self):
        for values in ({"tooth_status": "healthy"}, {"tooth_status": True},
                       {"tooth_status": "observation", "observation": ""},
                       {"tooth_status": "absent", "surface": "synthetic_surface"}):
            with self.subTest(values=values), self.assertRaises(ValidationError):
                self.save(**values)
        for kind in ("assistant", "reception"):
            self.assignment.kind = kind
            self.assignment.save(update_fields=["kind"])
            with self.subTest(kind=kind), self.assertRaises(PermissionDenied):
                self.save(tooth_status="absent", observation="")
        self.assertFalse(DentalToothHistory.objects.exists())

    def test_reused_key_changed_payload_is_rejected(self):
        self.save()
        with self.assertRaises(CRMCommandConflict):
            self.save(observation="Different content")

    def test_stale_patient_encounter_and_tooth_revisions_are_rejected(self):
        self.save()
        for values in ({"expected_patient_revision": 2}, {"expected_encounter_revision": 2},
                       {"expected_tooth_revision": 0}, {"tooth": 12, "expected_tooth_revision": 1}):
            with self.subTest(values=values), self.assertRaises(InvalidTransition):
                self.save(idempotency_key="stale", **values)
        self.assertEqual(DentalToothHistory.objects.count(), 1)

    def test_owner_has_no_automatic_medical_access(self):
        with self.assertRaises(PermissionDenied):
            self.save(actor=self.owner)
        self.assertFalse(DentalToothState.objects.exists())

    def test_role_revocation_blocks_replay(self):
        self.save()
        type(self.assignment).objects.filter(pk=self.assignment.pk).update(revoked_at=timezone.now())
        with self.assertRaises(PermissionDenied):
            self.save()

    def test_unverified_identity_blocks_write_and_replay(self):
        self.save()
        PatientProfile.objects.filter(pk=self.patient.pk).update(identity_status="unverified", verified_at=None,
            verified_by=None, verification_evidence_encrypted="")
        with self.assertRaises(InvalidTransition):
            self.save()

    def test_foreign_business_or_patient_not_found(self):
        foreign = Business.objects.create(owner=self.owner, name="Foreign", slug="tooth-service-foreign")
        with self.assertRaises(PermissionDenied):
            self.save(business_id=foreign.pk)
        with self.assertRaises(NotFound):
            self.save(patient_id=self.patient.pk + 10000)

    def test_revoked_branch_scope_blocks_new_write_and_replay(self):
        self.save()
        self.assignment.branches.clear()
        with self.assertRaises(PermissionDenied):
            self.save()

    def test_another_primary_clinician_cannot_be_edited(self):
        from apps.businesses.models import BusinessMember
        other, _ = BusinessMember.objects.get_or_create(business=self.business, user=self.owner, defaults={"role": "owner"})
        type(self.encounter_record).objects.filter(pk=self.encounter_record.pk).update(primary_clinician=other)
        with self.assertRaises(PermissionDenied):
            self.save()

    def test_surface_policy_without_approval_fails_closed(self):
        policy = {str(self.business.pk): {"reference": "synthetic-v1", "approval_reference": "",
            "teeth": {"11": ["synthetic_surface"]}}}
        with override_settings(MEDICAL_TOOTH_SURFACE_POLICIES=policy):
            with self.assertRaises(ToothNotationUnavailable):
                self.save(surface="synthetic_surface", surface_reference="synthetic-v1")
        self.assertFalse(DentalToothState.objects.exists())

    def test_current_appointment_basis_is_required(self):
        type(self.appointment).objects.filter(pk=self.appointment.pk).update(is_archived=True, archived_at=timezone.now())
        with self.assertRaises(PermissionDenied):
            self.save()

    def test_active_participation_can_supply_same_branch_basis(self):
        type(self.appointment).objects.filter(pk=self.appointment.pk).update(is_archived=True, archived_at=timezone.now())
        now = timezone.now()
        participation = TreatmentParticipation.objects.create(patient=self.patient, member=self.member,
            branch=self.first, proposed_by=self.owner, state="active", proposed_at=now, accepted_at=now)
        history, _ = self.save(participation_id=participation.pk)
        self.assertEqual(history.encounter_id, self.encounter_record.pk)

    def test_archived_record_and_finalized_encounter_cannot_be_changed(self):
        type(self.record).objects.filter(pk=self.record.pk).update(state="archived", archived_at=timezone.now(), archived_by=self.owner)
        with self.assertRaises(InvalidTransition):
            self.save()
        type(self.record).objects.filter(pk=self.record.pk).update(state="active", archived_at=None, archived_by=None)
        now = timezone.now()
        type(self.encounter_record).objects.filter(pk=self.encounter_record.pk).update(state="finalized", ended_at=now,
            finalized_at=now, finalized_by=self.doctor)
        with self.assertRaises(InvalidTransition):
            self.save()

    def test_audit_failure_rolls_back_initial_state_history_and_command(self):
        with patch("apps.medical.audit.MedicalAuditEvent.objects.create", side_effect=DatabaseError("synthetic")):
            with self.assertRaises(MedicalAuditUnavailable):
                self.save()
        self.assertFalse(DentalToothState.objects.exists())
        self.assertFalse(DentalToothHistory.objects.exists())
        self.assertFalse(CRMCommandIdempotency.objects.exists())

    @override_settings(MEDICAL_DATA_KEYS={})
    def test_missing_key_rolls_back_initial_state(self):
        with self.assertRaises(MedicalKeyUnavailable):
            self.save()
        self.assertFalse(DentalToothState.objects.exists())

    def test_surface_requires_configured_approved_vocabulary_and_snapshot(self):
        with self.assertRaises(ToothNotationUnavailable):
            self.save(surface="synthetic_surface", surface_reference="synthetic-v1")
        policy = {str(self.business.pk): {"reference": "synthetic-v1", "approval_reference": "synthetic-test-only",
            "teeth": {"11": ["synthetic_surface"]}}}
        with override_settings(MEDICAL_TOOTH_SURFACE_POLICIES=policy):
            with self.assertRaises(InvalidTransition):
                self.save(surface="synthetic_surface", surface_reference="old")
            with self.assertRaises(ValidationError):
                self.save(tooth=12, surface="synthetic_surface", surface_reference="synthetic-v1")
            history, _ = self.save(surface="synthetic_surface", surface_reference="synthetic-v1")
        self.assertEqual(read_tooth_history(history)["surface_protocol"],
            {"reference": "synthetic-v1", "approval_reference": "synthetic-test-only"})

    def test_invalid_identifiers_and_empty_observation_never_create_state(self):
        for values in ({"tooth": 56}, {"tooth": True}, {"expected_tooth_revision": -1},
                       {"expected_tooth_revision": False}, {"observation": " "}, {"idempotency_key": ""}):
            with self.subTest(values=values), self.assertRaises(ValidationError):
                self.save(**values)
        self.assertFalse(DentalToothState.objects.exists())
