from unittest.mock import patch

from django.db import DatabaseError, IntegrityError, transaction
from django.db.models.deletion import ProtectedError
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.exceptions import NotFound, PermissionDenied, ValidationError

from apps.businesses.models import Business, RolePermission
from apps.clients.models import Client
from apps.core.domain_errors import InvalidTransition
from apps.core.idempotency import CRMCommandConflict
from apps.core.models import CRMCommandIdempotency
from . import tests_appointment_access as fixtures
from . import tests_patient_services as crypto_fixtures
from .audit import MedicalAuditUnavailable, write_patient_audit
from .models import DentalMedicalRecord, MedicalAuditEvent, PatientProfile, TreatmentParticipation
from .record_services import open_dental_record


@override_settings(MEDICAL_IDENTITY_INDEX_KEY=crypto_fixtures.key(8))
class DentalRecordOpeningTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        fixtures.AppointmentMedicalBasisTests.setUpTestData.__func__(cls)
        # Synthetic verified state; this fixture does not certify a real identity protocol.
        type(cls.patient).objects.filter(pk=cls.patient.pk).update(identity_status="verified",
            verified_at=timezone.now(), verified_by=cls.owner, verification_evidence_encrypted="synthetic-evidence")
        cls.patient.refresh_from_db()
        RolePermission.objects.create(business_role=cls.role, resource="medical_records",
            action="create", scope="own", is_allowed=True)

    def open(self, **overrides):
        return open_dental_record(**(dict(actor=self.doctor, business_id=self.business.pk,
            patient_id=self.patient.pk, number="PRIVATE-LOCAL-001", expected_patient_revision=1,
            appointment_id=self.appointment.pk, idempotency_key="open-chart") | overrides))

    def test_open_and_replay_preserve_one_chart_and_audit(self):
        record, replayed = self.open()
        self.assertFalse(replayed)
        same, replayed = self.open()
        self.assertTrue(replayed)
        self.assertEqual(same.pk, record.pk)
        self.assertEqual((record.number, record.opened_by_id, record.state), ("PRIVATE-LOCAL-001", self.doctor.pk, "active"))
        event = MedicalAuditEvent.objects.get()
        self.assertEqual((event.action, event.record_id), ("record_opened", record.pk))
        self.assertNotIn(record.number, str(event.__dict__))
        self.assertNotIn(record.number, str(CRMCommandIdempotency.objects.get().__dict__))
        self.assertEqual(CRMCommandIdempotency.objects.get().response_json, {})
        with self.assertRaises(ProtectedError):
            record.delete()

    def test_duplicate_patient_chart_and_changed_replay_conflict(self):
        self.open()
        with self.assertRaises(InvalidTransition):
            self.open(number="OTHER", idempotency_key="second")
        with self.assertRaises(CRMCommandConflict):
            self.open(number="OTHER")
        self.assertEqual(DentalMedicalRecord.objects.count(), 1)

    def test_number_collision_does_not_expose_other_patient(self):
        client = Client.objects.create(business=self.business, full_name="Other private patient")
        patient = PatientProfile.objects.create(business=self.business, client=client, created_by=self.owner)
        DentalMedicalRecord.objects.create(business=self.business, patient=patient, number="PRIVATE-LOCAL-001", opened_by=self.owner)
        with self.assertRaises(InvalidTransition) as caught:
            self.open()
        self.assertNotIn(client.full_name, str(caught.exception))
        self.assertFalse(MedicalAuditEvent.objects.exists())

    def test_foreign_business_patient_and_owner_are_denied(self):
        foreign = Business.objects.create(owner=self.owner, name="Foreign", slug="record-open-foreign")
        client = Client.objects.create(business=foreign, full_name="Foreign synthetic")
        patient = PatientProfile.objects.create(business=foreign, client=client, created_by=self.owner)
        with self.assertRaises(NotFound):
            self.open(patient_id=patient.pk)
        for values in ({"business_id": foreign.pk}, {"actor": self.owner}):
            with self.subTest(values=values), self.assertRaises(PermissionDenied):
                self.open(**values)
        self.assertFalse(DentalMedicalRecord.objects.exists())

    def test_revoked_role_and_branch_deny_replay(self):
        self.open()
        self.assignment.branches.clear()
        with self.assertRaises(PermissionDenied):
            self.open()
        self.assignment.branches.add(self.first)
        self.assignment.revoked_at = timezone.now()
        self.assignment.save(update_fields=["revoked_at"])
        with self.assertRaises(PermissionDenied):
            self.open()

    def test_active_participation_allows_open_without_valid_booking(self):
        self.appointment.status = "cancelled"
        self.appointment.save(update_fields=["status"])
        with self.assertRaises(PermissionDenied):
            self.open()
        now = timezone.now()
        item = TreatmentParticipation.objects.create(patient=self.patient, member=self.member, branch=self.first,
            proposed_by=self.owner, proposed_at=now, accepted_at=now, state="active")
        self.open(appointment_id=None, participation_id=item.pk)

    def test_stale_revision_and_invalid_input_do_not_create(self):
        with self.assertRaises(InvalidTransition):
            self.open(expected_patient_revision=2)
        for values in ({"number": " "}, {"number": "x" * 65}, {"appointment_id": None},
                       {"participation_id": 1}, {"idempotency_key": ""}):
            with self.subTest(values=values), self.assertRaises(ValidationError):
                self.open(**values)
        self.assertFalse(DentalMedicalRecord.objects.exists())

    def test_audit_failure_rolls_back_record_and_command(self):
        with patch("apps.medical.audit.MedicalAuditEvent.objects.create", side_effect=DatabaseError("synthetic")):
            with self.assertRaises(MedicalAuditUnavailable):
                self.open()
        self.assertFalse(DentalMedicalRecord.objects.exists())
        self.assertFalse(CRMCommandIdempotency.objects.exists())
        self.open()

    def test_record_audit_requires_exact_patient_and_exclusive_relation(self):
        record, _ = self.open()
        client = Client.objects.create(business=self.business, full_name="Other synthetic")
        patient = PatientProfile.objects.create(business=self.business, client=client, created_by=self.owner)
        for values in ({"record": None}, {"record": record, "patient": patient}):
            with self.subTest(values=values), self.assertRaises(ValueError):
                write_patient_audit(**(dict(actor=self.doctor, business=self.business, patient=self.patient,
                    action="record_opened", record=record) | values))
        item = TreatmentParticipation.objects.create(patient=self.patient, member=self.member, branch=self.first,
            proposed_by=self.owner)
        with self.assertRaises(ValueError):
            write_patient_audit(actor=self.doctor, business=self.business, patient=self.patient,
                action="record_opened", record=record, participation=item)
        for values in ({}, {"record": record, "participation": item, "participation_revision": 1}):
            with self.subTest(values=values), self.assertRaises(IntegrityError), transaction.atomic():
                MedicalAuditEvent.objects.create(business=self.business, patient=self.patient, patient_revision=1,
                    actor=self.doctor, action="record_opened", result="success", **values)

    def test_unverified_identity_blocks_clinical_write(self):
        type(self.patient).objects.filter(pk=self.patient.pk).update(identity_status="unverified",
            verified_at=None, verified_by=None, verification_evidence_encrypted="")
        with self.assertRaises(InvalidTransition):
            self.open()
        self.assertFalse(CRMCommandIdempotency.objects.exists())
        self.assertFalse(MedicalAuditEvent.objects.exists())
