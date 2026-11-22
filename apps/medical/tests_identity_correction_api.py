from unittest.mock import patch

from django.db import DatabaseError
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from apps.businesses.models import Business, RolePermission
from apps.clients.models import Client
from .models import MedicalAuditEvent, PatientIdentityCorrection
from . import tests_identity_iin_corrections as correction_fixtures
from . import tests_patient_services as fixtures


@override_settings(MEDICAL_DATA_KEYS={"test": fixtures.key(7)}, MEDICAL_DATA_ACTIVE_KEY_ID="test",
                   MEDICAL_IDENTITY_INDEX_KEY=fixtures.key(8))
class IdentityCorrectionAPITests(TestCase):
    @classmethod
    def setUpTestData(cls):
        correction_fixtures.IINCorrectionTests.setUpTestData.__func__(cls)
        for role in (cls.assignment.business_role, cls.head_assignment.business_role):
            RolePermission.objects.get_or_create(business_role=role, resource="medical_patients", action="view", defaults={"scope": "business"})

    def setUp(self):
        correction_fixtures.IINCorrectionTests.setUp(self)
        correction_fixtures.IINCorrectionTests.history(self)
        self.api = APIClient(); self.api.force_authenticate(self.reception)
        self.scope = {"business_id": self.business.pk, "branch_id": self.branch.pk}
        self.path = f"/api/medical/patients/{self.patient.pk}/iin-correction/"
        self.list_path = "/api/medical/patients/identity-corrections/"
        self.payload = {**self.scope, "expected_revision": 2,
            "expected_client_updated_at": self.patient_client.updated_at.isoformat(), "iin": "000000000002",
            "reason": "Private correction reason", "protocol_reference": "synthetic-v1",
            "method": "synthetic_document", "fields": {"check_reference": "Private recheck"}}

    def request_correction(self):
        response = self.api.post(self.path, self.payload, format="json", HTTP_IDEMPOTENCY_KEY="api-correction")
        self.assertEqual(response.status_code, 201, response.data)
        return response.data["id"]

    def decision(self, correction_id, **values):
        return self.api.post(f"{self.list_path}{correction_id}/decision/",
            {"business_id": self.business.pk, "approve": True, "reason": "Private review", **values},
            format="json", HTTP_IDEMPOTENCY_KEY="api-decision")

    def listing(self):
        return self.api.get(self.list_path, {**self.scope, "client_id": self.patient_client.pk})

    def test_request_list_review_and_replay_are_private_and_audited(self):
        correction_id = self.request_correction()
        response = self.listing()
        self.assertEqual(response.status_code, 200, response.data)
        self.assertFalse(response.data["actions"]["approve"])
        self.assertEqual(response.data["results"][0]["proposed_iin"], "000000000002")
        self.assertIn("no-store", response["Cache-Control"])
        self.assertNotIn("fields", response.data["results"][0])
        self.api.force_authenticate(self.head)
        self.assertTrue(self.listing().data["actions"]["approve"])
        response = self.decision(correction_id)
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data["state"], "applied")
        self.assertTrue(self.decision(correction_id).data["replayed"])
        self.assertEqual(MedicalAuditEvent.objects.filter(identity_correction_id=correction_id,
            action="identity_correction_applied").count(), 1)

    def test_reception_owner_and_revoked_head_cannot_approve(self):
        correction_id = self.request_correction()
        for actor in (self.reception, self.owner):
            self.api.force_authenticate(actor)
            response = self.decision(correction_id)
            self.assertEqual(response.status_code, 403)
            self.assertIn("no-store", response["Cache-Control"])
        self.head_assignment.business_role.is_active = False
        self.head_assignment.business_role.save(update_fields=["is_active"])
        self.api.force_authenticate(self.head)
        self.assertEqual(self.decision(correction_id).status_code, 403)
        self.assertEqual(PatientIdentityCorrection.objects.get(pk=correction_id).state, "pending")

    def test_strict_fields_query_and_missing_idempotency_do_not_write(self):
        for path, data in ((self.path + "?iin=not-allowed", self.payload),
                           (self.path, {**self.payload, "approved_by": self.head.pk})):
            self.assertEqual(self.api.post(path, data, format="json", HTTP_IDEMPOTENCY_KEY="invalid").status_code, 400)
        self.assertEqual(self.api.post(self.path, self.payload, format="json").status_code, 400)
        self.assertEqual(PatientIdentityCorrection.objects.count(), 0)

    def test_list_requires_medical_view_and_branch_scope(self):
        self.request_correction()
        self.api.force_authenticate(self.head)
        RolePermission.objects.filter(business_role=self.head_assignment.business_role, action="view").update(is_allowed=False)
        self.assertEqual(self.listing().status_code, 403)
        self.api.force_authenticate(self.reception)
        self.assignment.branches.clear()
        self.assertEqual(self.listing().status_code, 403)

    def test_list_audit_failure_and_denial_audit_failure_return_503(self):
        self.request_correction()
        with patch("apps.medical.audit.MedicalAuditEvent.objects.create", side_effect=DatabaseError("synthetic")):
            self.assertEqual(self.listing().status_code, 503)
            self.api.force_authenticate(self.owner)
            self.assertEqual(self.listing().status_code, 503)

    def test_foreign_business_and_client_do_not_expose_correction(self):
        correction_id = self.request_correction()
        foreign = Business.objects.create(owner=self.owner, name="Other synthetic clinic", slug="iin-foreign")
        client = Client.objects.create(business=foreign, full_name="Private foreign name")
        self.assertEqual(self.api.get(self.list_path, {**self.scope, "client_id": client.pk}).status_code, 404)
        self.api.force_authenticate(self.head)
        self.assertEqual(self.decision(correction_id, business_id=foreign.pk).status_code, 403)
        self.assertFalse(MedicalAuditEvent.objects.filter(business=foreign).exists())
