from datetime import timedelta
from unittest.mock import patch

from django.db import DatabaseError
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from apps.businesses.models import Business, RolePermission
from apps.clients.models import Client
from .models import PatientProfile
from .models import MedicalAuditEvent, PatientRepresentative
from . import tests_patient_services as patient_fixtures
from . import tests_representative_services as fixtures


@override_settings(MEDICAL_DATA_KEYS={"test": patient_fixtures.key(7)}, MEDICAL_DATA_ACTIVE_KEY_ID="test",
                   MEDICAL_IDENTITY_INDEX_KEY=patient_fixtures.key(8))
class RepresentativeAPITests(TestCase):
    @classmethod
    def setUpTestData(cls):
        fixtures.RepresentativeServiceTests.setUpTestData.__func__(cls)
        RolePermission.objects.create(business_role=cls.assignment.business_role,
            resource="medical_patients", action="view", scope="business")

    def setUp(self):
        fixtures.RepresentativeServiceTests.setUp(self)
        self.api = APIClient()
        self.api.force_authenticate(self.reception)
        self.url = f"/api/medical/patients/{self.patient.pk}/representatives/"
        self.scope = {"business_id": self.business.pk, "branch_id": self.branch.pk}
        self.payload = {**self.scope, "representative_client_id": self.relative.pk,
            "expected_patient_revision": 1, "expected_client_updated_at": self.relative.updated_at.isoformat(),
            "protocol_reference": "synthetic-representation-v1", "method": "synthetic",
            "fields": {"basis": "Private synthetic authority evidence"}, "permissions": ["receive_documents"],
            "valid_from": self.start.isoformat(), "valid_until": (self.start + timedelta(days=1)).isoformat()}

    def post(self, **changes):
        return self.api.post(self.url, {**self.payload, **changes}, format="json", HTTP_IDEMPOTENCY_KEY="api-rep-create")

    def assert_private(self, response):
        self.assertEqual(response["Cache-Control"], "no-store, private")
        self.assertEqual(response["Pragma"], "no-cache")
        for secret in ("Private synthetic authority evidence", "synthetic-not-real-approval", "authority_encrypted", "trained_member_ids"):
            self.assertNotIn(secret, str(response.data))

    def test_create_list_revoke_replay_and_audit_are_reachable(self):
        created = self.post()
        self.assertEqual(created.status_code, 201, created.data)
        self.assert_private(created)
        replay = self.post()
        self.assertEqual(replay.status_code, 200)
        self.assertTrue(replay.data["replayed"])
        listed = self.api.get(self.url, self.scope)
        self.assertEqual(listed.status_code, 200, listed.data)
        self.assert_private(listed)
        row = listed.data["results"][0]
        self.assertEqual((row["id"], row["status"], row["permissions"]), (created.data["id"], "active", ["receive_documents"]))
        self.assertEqual(MedicalAuditEvent.objects.filter(action="read", representative_id=row["id"]).count(), 1)
        url = self.url + f"{row['id']}/revoke/"
        payload = {**self.scope, "representative_client_id": self.relative.pk, "expected_revision": 1, "reason": "Private reason"}
        for expected_replayed in (False, True):
            result = self.api.post(url, payload, format="json", HTTP_IDEMPOTENCY_KEY="api-rep-revoke")
            self.assertEqual(result.status_code, 200, result.data)
            self.assertEqual(result.data["replayed"], expected_replayed)
            self.assert_private(result)
        self.assertEqual(self.api.get(self.url, self.scope).data["results"][0]["status"], "revoked")

    def test_owner_and_revoked_role_cannot_read_or_create(self):
        self.post()
        self.api.force_authenticate(self.owner)
        for response in (self.api.get(self.url, self.scope), self.post()):
            self.assertEqual(response.status_code, 403)
            self.assert_private(response)
        self.api.force_authenticate(self.reception)
        self.assignment.branches.clear()
        response = self.api.get(self.url, self.scope)
        self.assertEqual(response.status_code, 403)
        self.assert_private(response)

    def test_foreign_or_missing_patient_and_strict_input(self):
        response = self.api.get("/api/medical/patients/999999/representatives/", self.scope)
        self.assertEqual(response.status_code, 404)
        for response in (self.post(verified_by=self.owner.pk), self.api.get(self.url, {**self.scope, "clinical": "secret"}),
                         self.api.get(self.url, {**self.scope, "limit": 51})):
            self.assertEqual(response.status_code, 400)
            self.assert_private(response)
        self.assertFalse(PatientRepresentative.objects.exists())

    def test_stale_version_and_missing_idempotency_key_do_not_write(self):
        self.assertEqual(self.post(expected_patient_revision=99).status_code, 409)
        response = self.api.post(self.url, self.payload, format="json")
        self.assertEqual(response.status_code, 400)
        self.assert_private(response)
        self.assertFalse(PatientRepresentative.objects.exists())

    def test_read_audit_failure_does_not_return_private_projection(self):
        self.post()
        with patch("apps.medical.audit.MedicalAuditEvent.objects.create", side_effect=DatabaseError):
            response = self.api.get(self.url, self.scope)
        self.assertEqual(response.status_code, 503)
        self.assert_private(response)
        self.assertNotIn(self.relative.full_name, str(response.data))

    def test_list_pagination_and_empty_page_are_audited(self):
        self.post()
        second = self.api.post(self.url, self.payload, format="json", HTTP_IDEMPOTENCY_KEY="second-explicit-grant")
        self.assertEqual(second.status_code, 201)
        page = self.api.get(self.url, {**self.scope, "limit": 1})
        self.assertEqual(page.data["next_offset"], 1)
        self.assertEqual(len(page.data["results"]), 1)
        next_page = self.api.get(self.url, {**self.scope, "limit": 1, "offset": 1})
        self.assertIsNone(next_page.data["next_offset"])
        self.assertNotEqual(next_page.data["results"][0]["id"], page.data["results"][0]["id"])
        count = MedicalAuditEvent.objects.filter(action="read").count()
        empty = self.api.get(self.url, {**self.scope, "offset": 2})
        self.assertEqual(empty.data["results"], [])
        self.assertEqual(MedicalAuditEvent.objects.filter(action="read").count(), count + 1)

    def test_representation_has_no_general_update_or_delete(self):
        for method in (self.api.patch, self.api.put, self.api.delete):
            response = method(self.url, self.scope, format="json")
            self.assertEqual(response.status_code, 405)
            self.assert_private(response)

    def test_form_requires_complete_localized_protocol_and_training(self):
        url = "/api/medical/patients/representative-form/"
        response = self.api.get(url, self.scope)
        self.assertEqual(response.status_code, 503)
        policy = self.policies[str(self.business.pk)]
        label = {"ru": "Учебное основание", "kk": "Сынақ негізі", "en": "Synthetic basis"}
        policy["methods"]["synthetic"].update(label=label, field_labels={"basis": label})
        policy["permission_labels"] = {code: label for code in policy["permissions"]}
        response = self.api.get(url, self.scope)
        self.assertEqual(response.status_code, 200, response.data)
        self.assert_private(response)
        self.assertEqual(response.data["permissions"][0]["label"], label)
        self.assertTrue(response.data["requires_expiry"])
        self.assertEqual(response.data["methods"][0]["fields"][0]["code"], "basis")
        policy["trained_member_ids"] = []
        self.assertEqual(self.api.get(url, self.scope).status_code, 403)

    def test_existing_foreign_patient_is_not_disclosed(self):
        business = Business.objects.create(owner=self.owner, name="Foreign", slug="rep-api-foreign")
        client = Client.objects.create(business=business, full_name="Private foreign patient")
        patient = PatientProfile.objects.create(business=business, client=client, created_by=self.owner)
        response = self.api.get(f"/api/medical/patients/{patient.pk}/representatives/", self.scope)
        self.assertEqual(response.status_code, 404)
        self.assert_private(response)
        self.assertNotIn(client.full_name, str(response.data))

    def test_tampered_period_is_not_reported_as_valid_authority(self):
        self.post()
        relation = PatientRepresentative.objects.get()
        PatientRepresentative.objects.filter(pk=relation.pk).update(valid_until=relation.valid_until + timedelta(days=1))
        response = self.api.get(self.url, self.scope)
        self.assertEqual(response.status_code, 503)
        self.assert_private(response)
        self.assertNotIn(self.relative.full_name, str(response.data))

    def test_invalid_permission_labels_fail_closed_for_form_and_command(self):
        policy = self.policies[str(self.business.pk)]
        policy["permission_labels"] = {"receive_documents": {"ru": "Incomplete"}}
        response = self.api.get("/api/medical/patients/representative-form/", self.scope)
        self.assertEqual(response.status_code, 503)
        self.assert_private(response)
        self.assertEqual(self.post().status_code, 503)
        self.assertFalse(PatientRepresentative.objects.exists())

    def test_historical_labels_survive_protocol_removal_without_approve_access(self):
        policy = self.policies[str(self.business.pk)]
        label = {"ru": "Получение документов", "kk": "Құжаттарды алу", "en": "Receive documents"}
        policy["permission_labels"] = {code: label for code in policy["permissions"]}
        self.assertEqual(self.post().status_code, 201)
        RolePermission.objects.filter(business_role=self.assignment.business_role, action="approve").delete()
        with override_settings(MEDICAL_REPRESENTATIVE_POLICIES=""):
            response = self.api.get(self.url, self.scope)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["results"][0]["permission_labels"], {"receive_documents": label})
        self.assert_private(response)

    def test_unlabeled_authority_is_explicit_without_invented_labels(self):
        self.assertEqual(self.post().status_code, 201)
        response = self.api.get(self.url, self.scope)
        self.assertIsNone(response.data["results"][0]["permission_labels"])
