from unittest.mock import patch

from django.core.cache import cache
from django.db import DatabaseError
from django.test import TestCase, override_settings
from rest_framework.test import APIClient
from rest_framework.throttling import ScopedRateThrottle

from apps.businesses.models import Business, BusinessCapability, BusinessRole, RolePermission
from apps.branches.models import Branch
from .models import MedicalAuditEvent
from . import tests_patient_search as search_fixtures
from . import tests_patient_services as fixtures


@override_settings(MEDICAL_DATA_KEYS={"test": fixtures.key(7)}, MEDICAL_DATA_ACTIVE_KEY_ID="test",
                   MEDICAL_IDENTITY_INDEX_KEY=fixtures.key(8))
class PatientSearchAPITests(TestCase):
    @classmethod
    def setUpTestData(cls):
        search_fixtures.PatientSearchTests.setUpTestData.__func__(cls)

    def setUp(self):
        cache.clear()
        self.api = APIClient()
        self.api.force_authenticate(self.reception)
        self.url = "/api/medical/patients/resolve/"
        self.payload = {"business_id": self.business.pk, "branch_id": self.branch.pk,
                        "kind": "iin", "query": "000000000001"}

    def lookup(self, **changes):
        return self.api.post(self.url, self.payload | changes, format="json")

    def private(self, response):
        self.assertEqual(response["Cache-Control"], "no-store, private")
        self.assertEqual(response["Pragma"], "no-cache")

    def test_post_lookup_with_safe_headers_and_request_logs(self):
        with self.assertLogs("zani.request", level="INFO") as logs:
            response = self.lookup()
        self.assertEqual(response.status_code, 200, response.data)
        self.private(response)
        self.assertEqual(response.data["results"][0]["client_id"], self.patient_client.pk)
        self.assertNotIn(self.payload["query"], str(logs.output))
        self.assertNotIn(self.payload["query"], str(response.data))

    def test_entry_access_returns_only_intersection_of_active_crm_and_medical_branches(self):
        extra = Branch.objects.create(business=self.business, name="Synthetic excluded")
        self.assignment.branches.add(extra)
        url = "/api/medical/patients/search-access/"
        scope = {"business_id": self.business.pk}
        response = self.api.get(url, scope)
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data["branches"], [{"id": self.branch.pk, "name": self.branch.name}])
        self.private(response)
        self.crm_branch.branches.add(extra)
        extra.is_active = False
        extra.save(update_fields=["is_active"])
        self.assertEqual(self.api.get(url, scope).data["branches"], response.data["branches"])
        self.assignment.branches.clear()
        self.assertEqual(self.api.get(url, scope).data["branches"], [])
        self.api.force_authenticate(self.owner)
        self.assertEqual(self.api.get(url, scope).status_code, 403)
        self.assertEqual(self.api.get(url, scope | {"query": "unexpected"}).status_code, 400)

    def test_crm_hidden_and_missing_iin_have_same_empty_projection(self):
        role = BusinessRole.objects.create(business=self.business, name="Synthetic denied CRM")
        RolePermission.objects.create(business_role=role, resource="clients", action="view", is_allowed=False)
        self.member.business_role = role
        self.member.save(update_fields=["business_role"])
        hidden = self.lookup()
        missing = self.lookup(query="999999999999")
        self.assertEqual((hidden.status_code, missing.status_code), (200, 200))
        self.assertEqual(hidden.data, {"results": [], "next_offset": None})
        self.assertEqual(hidden.data, missing.data)
        self.assertFalse(MedicalAuditEvent.objects.filter(patient=self.patient, action="read").exists())

    def test_owner_and_disabled_module_denials_are_audited_without_patient_identity(self):
        self.api.force_authenticate(self.owner)
        denied = self.lookup()
        self.assertEqual(denied.status_code, 403)
        self.private(denied)
        event = MedicalAuditEvent.objects.get(action="access_denied")
        self.assertEqual(event.actor_id, self.owner.pk)
        self.assertIsNone(event.patient_id)
        self.api.force_authenticate(self.reception)
        BusinessCapability.objects.filter(business=self.business, module_key="medical_records").update(is_enabled=False)
        self.assertEqual(self.lookup().status_code, 403)
        self.assertEqual(MedicalAuditEvent.objects.filter(action="access_denied").count(), 2)

    def test_unknown_fields_query_string_and_get_are_rejected(self):
        for response in (self.lookup(patient_id=self.patient.pk), self.lookup(limit=51),
                         self.api.post(self.url + "?extra=1", self.payload, format="json")):
            self.assertEqual(response.status_code, 400, response.data)
            self.private(response)
        response = self.api.get(self.url)
        self.assertEqual(response.status_code, 405)
        self.private(response)

    def test_throttle_is_per_actor_and_cannot_be_reset_by_switching_business(self):
        other = Business.objects.create(owner=self.owner, name="Other", slug="search-api-other")
        with patch.dict(ScopedRateThrottle.THROTTLE_RATES, {"medical_patient_lookup": "2/min"}):
            self.assertEqual(self.lookup().status_code, 200)
            self.assertEqual(self.lookup(business_id=other.pk).status_code, 403)
            limited = self.lookup()
            self.assertEqual(limited.status_code, 429)
            self.assertIn("Retry-After", limited)
            self.private(limited)

    def test_success_and_denial_fail_closed_when_audit_is_unavailable(self):
        with patch("apps.medical.patient_search.MedicalAuditEvent.objects.create", side_effect=DatabaseError):
            response = self.lookup()
            self.assertEqual(response.status_code, 503)
            self.private(response)
            self.assertNotIn(self.patient_client.full_name, str(response.data))
            self.api.force_authenticate(self.owner)
            self.assertEqual(self.lookup().status_code, 503)
