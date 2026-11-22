from unittest.mock import patch

from django.db import DatabaseError
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from apps.businesses.models import Business, BusinessRole, RolePermission
from apps.clients.models import Client
from .models import DentalMedicalRecord, MedicalAuditEvent
from . import tests_patient_search as fixtures
from .tests_patient_services import key


@override_settings(MEDICAL_DATA_KEYS={"test": key(7)}, MEDICAL_DATA_ACTIVE_KEY_ID="test",
                   MEDICAL_IDENTITY_INDEX_KEY=key(8))
class PatientListProjectionTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        fixtures.PatientSearchTests.setUpTestData.__func__(cls)

    def setUp(self):
        self.api = APIClient()
        self.api.force_authenticate(self.reception)
        self.url = "/api/medical/patients/list-projection/"
        self.payload = {"business_id": self.business.pk, "branch_id": self.branch.pk,
                        "client_ids": [self.patient_client.pk, self.relative.pk]}

    def request(self, **changes):
        return self.api.post(self.url, self.payload | changes, format="json")

    def test_record_presence_is_not_identity_status_and_no_private_values_are_decrypted(self):
        with patch("apps.medical.identity_crypto.decrypt_medical_value", side_effect=AssertionError("No decryption")):
            response = self.request()
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data["results"], [
            {"client_id": self.patient_client.pk, "has_record": False, "identity_status": "unverified"},
            {"client_id": self.relative.pk, "has_record": False, "identity_status": None}])
        DentalMedicalRecord.objects.create(business=self.business, patient=self.patient, number="SYNTHETIC-PROJECTION", opened_by=self.owner)
        response = self.request()
        self.assertTrue(response.data["results"][0]["has_record"])
        self.assertEqual(response["Cache-Control"], "no-store, private")
        self.assertTrue(MedicalAuditEvent.objects.filter(patient=self.patient, action="read").exists())

    def test_foreign_and_missing_ids_are_omitted_and_duplicates_do_not_repeat(self):
        foreign_business = Business.objects.create(owner=self.owner, name="Foreign projection", slug="foreign-projection")
        foreign = Client.objects.create(business=foreign_business, full_name="Not visible")
        response = self.request(client_ids=[self.relative.pk, self.relative.pk, foreign.pk, foreign.pk + 1000])
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["results"], [{"client_id": self.relative.pk, "has_record": False, "identity_status": None}])

    def test_owner_without_medical_role_and_revoked_branch_cannot_read_status(self):
        self.api.force_authenticate(self.owner)
        self.assertEqual(self.request().status_code, 403)
        self.api.force_authenticate(self.reception)
        self.assignment.branches.clear()
        response = self.request()
        self.assertEqual(response.status_code, 403)
        self.assertNotIn("results", response.data)
        self.assertEqual(response["Cache-Control"], "no-store, private")

    def test_medical_role_does_not_bypass_core_client_read_scope(self):
        role = BusinessRole.objects.create(business=self.business, name="No core client read")
        RolePermission.objects.create(business_role=role, resource="clients", action="view", is_allowed=False, scope="none")
        self.member.business_role = role
        self.member.save(update_fields=["business_role"])
        response = self.request()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["results"], [])

    def test_bounded_strict_payload_and_audit_failure(self):
        for ids in ([], list(range(1, 102)), [0]):
            self.assertEqual(self.request(client_ids=ids).status_code, 400)
        self.assertEqual(self.request(extra="forbidden").status_code, 400)
        self.assertEqual(self.api.post(self.url + "?query=forbidden", self.payload, format="json").status_code, 400)
        before = MedicalAuditEvent.objects.count()
        with patch("apps.medical.audit.MedicalAuditEvent.objects.create", side_effect=DatabaseError("synthetic")):
            response = self.request()
        self.assertEqual(response.status_code, 503)
        self.assertEqual(MedicalAuditEvent.objects.count(), before)
