from unittest.mock import patch

from django.db import DatabaseError, IntegrityError, transaction
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.exceptions import NotFound, PermissionDenied

from apps.businesses.models import Business, BusinessCapability, RolePermission
from apps.core.domain_errors import InvalidTransition, ModuleDisabled
from apps.core.idempotency import CRMCommandConflict
from apps.core.models import CRMCommandIdempotency
from . import tests_encounter_services as fixtures
from . import tests_patient_services as crypto_fixtures
from .audit import MedicalAuditUnavailable, write_patient_audit
from .document_services import read_document_for_treating_clinician, save_primary_document_draft
from .identity_crypto import MedicalKeyUnavailable
from .models import MedicalAuditEvent, MedicalDocument, MedicalDocumentRevision, PatientProfile, TreatmentParticipation


@override_settings(MEDICAL_DATA_KEYS={"test": crypto_fixtures.key(7)}, MEDICAL_DATA_ACTIVE_KEY_ID="test",
                   MEDICAL_IDENTITY_INDEX_KEY=crypto_fixtures.key(8))
class DocumentServiceTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        fixtures.PrimaryEncounterDraftTests.setUpTestData.__func__(cls)
        for action in ("view", "create", "update"):
            RolePermission.objects.create(business_role=cls.role, resource="medical_documents",
                                          action=action, scope="own", is_allowed=True)

    def setUp(self):
        fixtures.PrimaryEncounterDraftTests.setUp(self)

    def save(self, **overrides):
        return save_primary_document_draft(**(dict(actor=self.doctor, business_id=self.business.pk,
            patient_id=self.patient.pk, encounter_id=self.encounter_record.pk, expected_encounter_revision=1,
            expected_patient_revision=self.patient.revision, idempotency_key="private-document-key",
            template={"code": "synthetic", "version": 1, "title": "Учебный документ",
                      "text": "Private synthetic template"}, reason="Private synthetic reason") | overrides))

    def read(self, version, **overrides):
        return read_document_for_treating_clinician(**(dict(actor=self.doctor, business_id=self.business.pk,
            patient_id=self.patient.pk, version_id=version.pk, appointment_id=self.appointment.pk) | overrides))

    def test_create_read_and_replay_bind_exact_versions_without_plaintext_ledger(self):
        version, replayed = self.save()
        self.assertFalse(replayed)
        event = MedicalAuditEvent.objects.get()
        self.assertEqual((event.action, event.document_version_id), ("document_draft_created", version.pk))
        result = self.read(version)
        self.assertEqual(result["snapshot"]["clinical"]["plan"], "Оқу жоспары")
        self.assertEqual(MedicalAuditEvent.objects.filter(action="read", document_version=version).count(), 1)
        replay, replayed = self.save()
        self.assertTrue(replayed)
        self.assertEqual(replay.pk, version.pk)
        self.assertEqual((MedicalDocument.objects.count(), MedicalDocumentRevision.objects.count()), (1, 1))
        command = CRMCommandIdempotency.objects.get()
        self.assertNotIn("Private synthetic", str(command.__dict__))
        self.assertNotEqual(command.idempotency_key, "private-document-key")
        self.assertEqual(command.response_json, {})
        self.appointment.refresh_from_db()
        self.assertEqual((self.appointment.status, self.appointment.notes), ("created", ""))

    def test_update_preserves_old_version_and_create_replay_after_update(self):
        first, _ = self.save()
        second, _ = self.save(document_id=first.document_id, expected_document_revision=1,
            idempotency_key="update", template={"code": "synthetic", "version": 2, "title": "New", "text": "New"})
        self.assertEqual(second.revision, 2)
        self.assertEqual(self.read(first)["snapshot"]["template"]["version"], 1)
        self.assertEqual(self.read(second)["snapshot"]["template"]["version"], 2)
        self.assertEqual(self.save()[0].pk, first.pk)
        self.assertEqual(MedicalAuditEvent.objects.filter(action="document_draft_saved", document_version=second).count(), 1)

    def test_stale_patient_encounter_document_and_conflicting_retry_do_not_write(self):
        with self.assertRaises(InvalidTransition):
            self.save(expected_patient_revision=999)
        with self.assertRaises(InvalidTransition):
            self.save(expected_encounter_revision=999)
        first, _ = self.save()
        with self.assertRaises(CRMCommandConflict):
            self.save(reason="Other")
        with self.assertRaises(InvalidTransition):
            self.save(document_id=first.document_id, expected_document_revision=2, idempotency_key="stale")
        self.assertEqual(MedicalDocumentRevision.objects.count(), 1)
        self.assertEqual(CRMCommandIdempotency.objects.count(), 1)

    def test_revocation_denies_read_and_replay(self):
        version, _ = self.save()
        self.assignment.revoked_at = timezone.now()
        self.assignment.save(update_fields=["revoked_at"])
        with self.assertRaises(PermissionDenied):
            self.read(version)
        with self.assertRaises(PermissionDenied):
            self.save()
        self.assertEqual(MedicalAuditEvent.objects.count(), 1)

    def test_owner_and_assistant_do_not_inherit_primary_clinician_access(self):
        with self.assertRaises(PermissionDenied):
            self.save(actor=self.owner)
        self.assignment.kind = "assistant"
        self.assignment.save(update_fields=["kind"])
        with self.assertRaises(PermissionDenied):
            self.save()
        self.assertFalse(MedicalDocument.objects.exists())

    def test_branch_and_disabled_module_deny_replay_and_read(self):
        version, _ = self.save()
        self.assignment.branches.clear()
        with self.assertRaises(PermissionDenied):
            self.save()
        with self.assertRaises(PermissionDenied):
            self.read(version)
        self.assignment.branches.add(self.first)
        BusinessCapability.objects.filter(business=self.business, module_key="medical_records").update(is_enabled=False)
        with self.assertRaises(ModuleDisabled):
            self.save()
        with self.assertRaises(ModuleDisabled):
            self.read(version)

    def test_individual_document_permissions_are_required(self):
        version, _ = self.save()
        RolePermission.objects.filter(business_role=self.role, resource="medical_documents").delete()
        with self.assertRaises(PermissionDenied):
            self.read(version)
        with self.assertRaises(PermissionDenied):
            self.save()
        self.assertTrue(RolePermission.objects.filter(business_role=self.role, resource="medical_records").exists())

    def test_patient_and_business_isolation(self):
        version, _ = self.save()
        other = Business.objects.create(owner=self.owner, name="Other", slug="other-document-service")
        with self.assertRaises(PermissionDenied):
            self.read(version, business_id=other.pk)
        with self.assertRaises(NotFound):
            self.save(patient_id=self.patient.pk + 999)
        with self.assertRaises(PermissionDenied):
            self.save(encounter_id=self.encounter_record.pk + 999)
        with self.assertRaises(PermissionDenied):
            self.save(document_id=version.document_id + 999, expected_document_revision=1)

    def test_another_patients_document_is_hidden_despite_valid_own_access_basis(self):
        from apps.clients.models import Client
        from .document_content import append_document_revision
        from .encounter_content import append_encounter_revision
        from .models import DentalMedicalRecord, MedicalEncounter
        client = Client.objects.create(business=self.business, full_name="Other synthetic patient")
        patient = PatientProfile.objects.create(business=self.business, client=client, created_by=self.owner)
        record = DentalMedicalRecord.objects.create(business=self.business, patient=patient,
            number="DOCUMENT-OTHER", opened_by=self.doctor)
        from apps.scheduling.models import Appointment
        appointment = Appointment.objects.create(business=self.business, client=client, branch=self.first,
            service=self.service, resource=self.staff, start_at=self.appointment.start_at, end_at=self.appointment.end_at)
        encounter = MedicalEncounter.objects.create(business=self.business, patient=patient, record=record,
            appointment=appointment, branch=self.first, primary_clinician=self.member)
        source = append_encounter_revision(encounter=encounter, author=self.doctor, content={"plan": "Other patient secret"})
        document = MedicalDocument.objects.create(business=self.business, encounter=encounter, template_code="other")
        version = append_document_revision(document=document, source_version=source, author=self.doctor,
            template={"code": "other", "version": 1, "title": "Other", "text": "Other"})
        with self.assertRaises(PermissionDenied):
            self.read(version)
        with self.assertRaises(PermissionDenied):
            self.save(document_id=document.pk, expected_document_revision=1)
        self.assertFalse(MedicalAuditEvent.objects.exists())

    def test_cancelled_booking_needs_active_same_branch_participation_for_writes(self):
        version, _ = self.save()
        self.appointment.status = "cancelled"
        self.appointment.save(update_fields=["status"])
        with self.assertRaises(PermissionDenied):
            self.read(version)
        with self.assertRaises(PermissionDenied):
            self.save()
        now = timezone.now()
        participation = TreatmentParticipation.objects.create(patient=self.patient, member=self.member,
            branch=self.first, state="active", proposed_by=self.owner, proposed_at=now, accepted_at=now)
        self.assertEqual(self.read(version, appointment_id=None, participation_id=participation.pk)["version_id"], version.pk)
        self.save(participation_id=participation.pk, idempotency_key="participation")
        participation.branch = self.second
        participation.save(update_fields=["branch"])
        self.assignment.branches.add(self.second)
        with self.assertRaises(PermissionDenied):
            self.save(participation_id=participation.pk, idempotency_key="wrong-branch")

    def test_unverified_identity_blocks_new_documents(self):
        PatientProfile.objects.filter(pk=self.patient.pk).update(identity_status="unverified",
            verified_at=None, verified_by=None, verification_evidence_encrypted="")
        with self.assertRaises(InvalidTransition):
            self.save()
        self.assertFalse(MedicalDocument.objects.exists())

    def test_write_audit_failure_rolls_back_document_version_and_receipt(self):
        with patch("apps.medical.audit.MedicalAuditEvent.objects.create", side_effect=DatabaseError()):
            with self.assertRaises(MedicalAuditUnavailable):
                self.save()
        self.assertFalse(MedicalDocument.objects.exists())
        self.assertFalse(MedicalDocumentRevision.objects.exists())
        self.assertFalse(CRMCommandIdempotency.objects.exists())

    def test_read_audit_failure_prevents_decryption(self):
        version, _ = self.save()
        with patch("apps.medical.audit.MedicalAuditEvent.objects.create", side_effect=DatabaseError()), \
                patch("apps.medical.document_services.read_document_revision") as decrypt:
            with self.assertRaises(MedicalAuditUnavailable):
                self.read(version)
            decrypt.assert_not_called()

    def test_failed_update_retains_prior_version_and_does_not_save_receipt(self):
        first, _ = self.save()
        with patch("apps.medical.audit.MedicalAuditEvent.objects.create", side_effect=DatabaseError()):
            with self.assertRaises(MedicalAuditUnavailable):
                self.save(document_id=first.document_id, expected_document_revision=1, idempotency_key="update-failure")
        self.assertEqual(MedicalDocument.objects.get(pk=first.document_id).revision, 1)
        self.assertEqual(MedicalDocumentRevision.objects.count(), 1)
        self.assertEqual(CRMCommandIdempotency.objects.count(), 1)
        self.assertEqual(self.read(first)["revision"], 1)

    def test_key_failure_rolls_back_document_and_receipt(self):
        with override_settings(MEDICAL_DATA_KEYS={}):
            with self.assertRaises(MedicalKeyUnavailable):
                self.save()
        self.assertFalse(MedicalDocument.objects.exists())
        self.assertFalse(CRMCommandIdempotency.objects.exists())

    def test_audit_rejects_wrong_action_mixed_relation_or_other_actor(self):
        version, _ = self.save()
        cases = [{"action": "document_draft_saved"}, {"actor": self.owner},
                 {"record": self.record}, {"action": "patient_updated"}]
        for changes in cases:
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                write_patient_audit(**(dict(actor=self.doctor, business=self.business, patient=self.patient,
                    action="document_draft_created", document_version=version) | changes))
        with self.assertRaises(IntegrityError), transaction.atomic():
            MedicalAuditEvent.objects.create(actor=self.doctor, business=self.business, patient=self.patient,
                patient_revision=self.patient.revision, action="document_draft_created", result="success")
