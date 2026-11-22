from unittest.mock import patch

from django.db import DatabaseError
from django.test import TestCase, override_settings
from rest_framework.exceptions import PermissionDenied, ValidationError

from apps.activities.models import ActivityEvent
from apps.clients.models import Client
from apps.core.domain_errors import IdempotencyConflict, InvalidTransition
from apps.core.models import AuditLog, CRMCommandIdempotency
from .audit import MedicalAuditUnavailable
from .models import PatientProfile
from .patient_registration import PatientMatchesRequireReview, register_new_patient
from . import tests_identity_corrections as correction_fixtures
from . import tests_patient_services as fixtures


@override_settings(MEDICAL_DATA_KEYS={"test": fixtures.key(7)}, MEDICAL_DATA_ACTIVE_KEY_ID="test",
                   MEDICAL_IDENTITY_INDEX_KEY=fixtures.key(8))
class PatientRegistrationTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        correction_fixtures.AdministrativeIdentityCorrectionTests.setUpTestData.__func__(cls)
        cls.member.role = "admin"
        cls.member.save(update_fields=["role"])

    def setUp(self):
        correction_fixtures.AdministrativeIdentityCorrectionTests.setUp(self)

    def register(self, **overrides):
        return register_new_patient(**dict({"actor": self.reception, "business_id": self.business.pk,
            "branch_id": self.branch.pk, "full_name": "New synthetic person", "phone": "+77000000009",
            "email": "new-patient@example.test", "demographics": {"date_of_birth": "2000-01-02"},
            "iin": "000000000009", "confirmed_separate_person": False, "idempotency_key": "registration"}, **overrides))

    def test_atomic_creation_keeps_client_and_patient_single_with_normal_core_history(self):
        patient, replayed = self.register()
        self.assertFalse(replayed)
        self.assertEqual(patient.identity_status, "unverified")
        self.assertEqual(patient.client.normalized_phone, "77000000009")
        self.assertEqual(ActivityEvent.objects.filter(client=patient.client, event_type="client.created").count(), 1)
        self.assertEqual(AuditLog.objects.filter(entity_type="Client", entity_id=str(patient.client_id)).count(), 1)
        repeated, replayed = self.register()
        self.assertTrue(replayed); self.assertEqual(repeated.pk, patient.pk)
        self.assertEqual(Client.objects.filter(full_name="New synthetic person").count(), 1)
        command = CRMCommandIdempotency.objects.get(action="medical.patient.register")
        self.assertEqual(command.response_json, {})
        self.assertNotIn("000000000009", str(command.request_hash))
        with self.assertRaises(IdempotencyConflict):
            self.register(full_name="Different person")

    def test_family_contact_requires_explicit_separate_person_and_never_merges(self):
        before = Client.objects.count()
        with self.assertRaises(PatientMatchesRequireReview):
            self.register(phone=self.patient_client.phone)
        self.assertEqual(Client.objects.count(), before)
        patient, _ = self.register(phone=self.patient_client.phone, confirmed_separate_person=True)
        self.assertNotEqual(patient.pk, self.patient.pk)
        self.assertNotEqual(patient.client_id, self.patient_client.pk)

    def test_name_match_also_requires_review(self):
        with self.assertRaises(PatientMatchesRequireReview):
            self.register(full_name=self.patient_client.full_name)

    def test_verified_iin_never_allows_second_person_even_after_confirmation(self):
        before = Client.objects.count()
        with self.assertRaises(InvalidTransition):
            self.register(iin="000000000001", confirmed_separate_person=True)
        self.assertEqual(Client.objects.count(), before)

    def test_medical_audit_failure_rolls_back_client_core_events_and_profile(self):
        counts = (Client.objects.count(), PatientProfile.objects.count(), AuditLog.objects.count(), ActivityEvent.objects.count())
        with patch("apps.medical.audit.MedicalAuditEvent.objects.create", side_effect=DatabaseError("synthetic")):
            with self.assertRaises(MedicalAuditUnavailable):
                self.register()
        self.assertEqual((Client.objects.count(), PatientProfile.objects.count(), AuditLog.objects.count(), ActivityEvent.objects.count()), counts)
        self.assertFalse(CRMCommandIdempotency.objects.filter(action="medical.patient.register").exists())

    def test_current_crm_create_and_medical_branch_are_both_required(self):
        self.member.role = "specialist"; self.member.save(update_fields=["role"])
        with self.assertRaises(PermissionDenied):
            self.register()
        self.member.role = "admin"; self.member.save(update_fields=["role"])
        self.assignment.branches.clear()
        with self.assertRaises(PermissionDenied):
            self.register()

    def test_invalid_contacts_or_demographics_leave_no_client(self):
        before = Client.objects.count()
        for fields in ({"email": "invalid"}, {"full_name": ""}, {"demographics": {"date_of_birth": "future"}}):
            with self.subTest(fields=list(fields)), self.assertRaises(ValidationError):
                self.register(**fields)
        self.assertEqual(Client.objects.count(), before)
