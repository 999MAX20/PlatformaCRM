from unittest.mock import patch

from django.db import DatabaseError, connection
from django.test import TestCase, override_settings
from django.test.utils import CaptureQueriesContext
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied, ValidationError

from apps.businesses.models import Business, RolePermission
from apps.clients.models import Client
from .audit import MedicalAuditUnavailable
from .models import MedicalAuditEvent, PatientProfile
from .patient_search import resolve_patients
from .patient_services import create_patient_profile
from . import tests_patient_services as fixtures


@override_settings(MEDICAL_DATA_KEYS={"test": fixtures.key(7)}, MEDICAL_DATA_ACTIVE_KEY_ID="test",
                   MEDICAL_IDENTITY_INDEX_KEY=fixtures.key(8))
class PatientSearchTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        fixtures.PatientCreationTests.setUpTestData.__func__(cls)
        RolePermission.objects.create(business_role=cls.assignment.business_role, resource="medical_patients",
                                      action="view", scope="business")
        cls.patient, _ = create_patient_profile(actor=cls.reception, business_id=cls.business.pk,
            client_id=cls.patient_client.pk, branch_id=cls.branch.pk,
            demographics={"date_of_birth": "2000-01-02", "address": "Synthetic private address"},
            iin="000000000001", idempotency_key="search-fixture")

    def search(self, **overrides):
        return resolve_patients(**{"actor": self.reception, "business_id": self.business.pk,
            "branch_id": self.branch.pk, "kind": "name", "query": "Synthetic", **overrides})

    def test_family_contact_returns_separate_possible_matches_with_no_private_fields(self):
        result = self.search(kind="phone", query="+7 (700) 000-00-01")
        self.assertEqual([row["client_id"] for row in result["results"]], [self.patient_client.pk, self.relative.pk])
        self.assertTrue(all(row["match"] == "possible" for row in result["results"]))
        self.assertEqual(result["results"][0]["date_of_birth"], "2000-01-02")
        self.assertNotIn("000000000001", str(result))
        self.assertNotIn("Synthetic private address", str(result))
        self.assertIsNone(result["next_offset"])

    def test_iin_only_verified_identity_is_confirmed_and_raw_iin_not_queried(self):
        self.assertEqual(self.search(kind="iin", query="000000000001")["results"][0]["match"], "possible")
        PatientProfile.objects.filter(pk=self.patient.pk).update(identity_status="verified", verified_at=timezone.now(),
            verified_by=self.owner, verification_evidence_encrypted="synthetic-fixture")
        with CaptureQueriesContext(connection) as captured:
            result = self.search(kind="iin", query="000000000001")
        self.assertEqual(result["results"][0]["match"], "exact_confirmed")
        self.assertNotIn("000000000001", str(list(captured)))

    def test_birth_and_pagination_match_before_page_boundary(self):
        self.assertEqual([row["patient_id"] for row in self.search(kind="birth", query="2000-01-02")["results"]], [self.patient.pk])
        self.assertEqual(self.search(kind="birth", query="2000-01-03")["results"], [])
        first = self.search(limit=1)
        self.assertEqual(first["next_offset"], 1)
        second = self.search(limit=1, offset=first["next_offset"])
        self.assertEqual(second["results"][0]["client_id"], self.relative.pk)
        self.assertIsNone(second["next_offset"])

    def test_archive_is_explicit_and_reads_are_audited_even_for_empty_result(self):
        Client.objects.filter(pk=self.patient_client.pk).update(is_archived=True)
        self.assertEqual(self.search(kind="iin", query="000000000001")["results"], [])
        result = self.search(kind="iin", query="000000000001", include_archived=True)
        self.assertTrue(result["results"][0]["is_archived"])
        self.assertTrue(MedicalAuditEvent.objects.filter(patient=self.patient, action="read").exists())
        self.assertEqual(MedicalAuditEvent.objects.filter(patient=None, action="read").count(), 2)

    def test_foreign_business_never_contributes_candidates(self):
        other = Business.objects.create(owner=self.owner, name="Other", slug="search-other")
        Client.objects.create(business=other, full_name="Synthetic hidden", phone=self.patient_client.phone)
        self.assertEqual(len(self.search()["results"]), 2)
        with self.assertRaises(PermissionDenied):
            self.search(business_id=other.pk)

    def test_owner_branch_and_revoked_assignment_are_denied(self):
        with self.assertRaises(PermissionDenied):
            self.search(actor=self.owner)
        with self.assertRaises(PermissionDenied):
            self.search(branch_id=self.branch.pk + 1000)
        self.assignment.revoked_at = timezone.now()
        self.assignment.save(update_fields=["revoked_at"])
        with self.assertRaises(PermissionDenied):
            self.search()

    def test_invalid_search_and_page(self):
        for values in ({"kind": "unknown"}, {"kind": []}, {"query": " "}, {"kind": "iin", "query": "invalid"},
                       {"kind": "birth", "query": "2000-99-99"}, {"kind": "phone", "query": "abc"},
                       {"offset": -1}, {"limit": 51}, {"include_archived": "true"}):
            with self.subTest(values=values), self.assertRaises(ValidationError):
                self.search(**values)

    def test_audit_failure_does_not_return_data_or_leave_partial_read_events(self):
        before = MedicalAuditEvent.objects.count()
        with patch("apps.medical.patient_search.write_patient_audit", side_effect=MedicalAuditUnavailable):
            with self.assertRaises(MedicalAuditUnavailable):
                self.search()
        self.assertEqual(MedicalAuditEvent.objects.count(), before)
        with patch("apps.medical.patient_search.MedicalAuditEvent.objects.create", side_effect=DatabaseError):
            with self.assertRaises(MedicalAuditUnavailable):
                self.search(query="Not present")
