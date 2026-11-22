from unittest.mock import patch

from django.db import DatabaseError
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from apps.businesses.models import Business, RolePermission
from apps.clients.models import Client
from .models import MedicalAuditEvent, PatientProfile
from . import tests_patient_services as fixtures


@override_settings(MEDICAL_DATA_KEYS={"test": fixtures.key(7)}, MEDICAL_DATA_ACTIVE_KEY_ID="test",
                   MEDICAL_IDENTITY_INDEX_KEY=fixtures.key(8))
class PatientAdministrationAPITests(TestCase):
    @classmethod
    def setUpTestData(cls):
        fixtures.PatientCreationTests.setUpTestData.__func__(cls)
        for action in ("view", "update", "approve"):
            RolePermission.objects.create(business_role=cls.assignment.business_role, resource="medical_patients",
                                          action=action, scope="business")

    def setUp(self):
        self.api = APIClient()
        self.api.force_authenticate(self.reception)
        self.scope = {"business_id": self.business.pk, "branch_id": self.branch.pk}
        self.collection = "/api/medical/patients/"
        self.create_data = {**self.scope, "client_id": self.patient_client.pk,
                            "demographics": {"address": "Private administrative address"}, "iin": "000000000001"}

    def create_patient(self):
        response = self.api.post(self.collection, self.create_data, format="json", HTTP_IDEMPOTENCY_KEY="api-create")
        self.assertEqual(response.status_code, 201, response.data)
        return response.data["id"]

    def form_policy(self):
        return {str(self.business.pk): {"reference": "synthetic-v1", "approval_reference": "private-approval",
            "trained_member_ids": [self.member.pk], "methods": {"synthetic": {
                "required_fields": ["checked"], "optional_fields": ["note"],
                "label": {"ru": "Учебная проверка", "kk": "Оқу тексеруі", "en": "Synthetic check"},
                "field_labels": {
                    "checked": {"ru": "Основание", "kk": "Негіздеме", "en": "Basis"},
                    "note": {"ru": "Примечание", "kk": "Ескертпе", "en": "Note"},
                }}}}}

    def test_verification_form_is_localized_and_excludes_private_configuration(self):
        with override_settings(MEDICAL_IDENTITY_VERIFICATION_POLICIES=self.form_policy()):
            response = self.api.get(self.collection + "verification-form/", self.scope)
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(set(response.data), {"reference", "methods"})
        self.assertEqual(response.data["reference"], "synthetic-v1")
        method = response.data["methods"][0]
        self.assertEqual(method["code"], "synthetic")
        self.assertEqual(set(method["label"]), {"ru", "kk", "en"})
        self.assertEqual([field["required"] for field in method["fields"]], [True, False])
        self.assertEqual([field["max_length"] for field in method["fields"]], [2000, 2000])
        self.assertNotIn("private-approval", response.content.decode())
        self.assertNotIn("trained_member_ids", response.content.decode())
        self.assertEqual(response["Cache-Control"], "no-store, private")
        self.assertFalse(MedicalAuditEvent.objects.exists())

    def test_verification_form_requires_training_and_current_permission(self):
        policy = self.form_policy()
        policy[str(self.business.pk)]["trained_member_ids"] = []
        with override_settings(MEDICAL_IDENTITY_VERIFICATION_POLICIES=policy):
            self.assertEqual(self.api.get(self.collection + "verification-form/", self.scope).status_code, 403)
        with override_settings(MEDICAL_IDENTITY_VERIFICATION_POLICIES=self.form_policy()):
            RolePermission.objects.filter(business_role=self.assignment.business_role,
                resource="medical_patients", action="approve").update(is_allowed=False)
            self.assertEqual(self.api.get(self.collection + "verification-form/", self.scope).status_code, 403)
            self.api.force_authenticate(self.owner)
            self.assertEqual(self.api.get(self.collection + "verification-form/", self.scope).status_code, 403)

    def test_verification_form_fails_closed_for_missing_or_incomplete_labels(self):
        for mutation in ("missing", "locale", "extra", "blank"):
            policy = self.form_policy()
            schema = policy[str(self.business.pk)]["methods"]["synthetic"]
            if mutation == "missing":
                del schema["label"]
                del schema["field_labels"]
            elif mutation == "locale":
                del schema["label"]["kk"]
            elif mutation == "extra":
                schema["field_labels"]["secret"] = schema["label"]
            else:
                schema["field_labels"]["note"]["en"] = " "
            with self.subTest(mutation=mutation), override_settings(MEDICAL_IDENTITY_VERIFICATION_POLICIES=policy):
                response = self.api.get(self.collection + "verification-form/", self.scope)
                self.assertEqual(response.status_code, 503)
                self.assertNotIn("private-approval", response.content.decode())

    def test_labeled_protocol_is_accepted_by_verification_command(self):
        pk = self.create_patient()
        with override_settings(MEDICAL_IDENTITY_VERIFICATION_POLICIES=self.form_policy()):
            response = self.api.post(f"{self.collection}{pk}/verify/", {**self.scope,
                "expected_revision": 1, "expected_client_updated_at": self.patient_client.updated_at.isoformat(),
                "protocol_reference": "synthetic-v1", "method": "synthetic", "fields": {"checked": "Test basis"}},
                format="json", HTTP_IDEMPOTENCY_KEY="labeled-verify")
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data["identity_status"], "verified")

    def test_full_administrative_http_flow(self):
        pk = self.create_patient()
        url = f"{self.collection}{pk}/"
        read = self.api.get(url, self.scope)
        self.assertEqual(read.status_code, 200)
        self.assertEqual(read.data["iin"], "000000000001")
        self.assertNotIn("verification_evidence_encrypted", read.data)
        self.assertNotIn("identity_revisions", read.data)
        preliminary = self.api.post(url + "preliminary/", {**self.scope, "expected_revision": 1,
            "demographics": {"address": "Corrected address"}, "iin": None, "reason": "Preliminary correction"},
            format="json", HTTP_IDEMPOTENCY_KEY="api-preliminary")
        self.assertEqual(preliminary.status_code, 200, preliminary.data)
        self.assertEqual(preliminary.data["revision"], 2)
        policy = {str(self.business.pk): {"reference": "synthetic-v1", "approval_reference": "synthetic-only",
            "trained_member_ids": [self.member.pk], "methods": {"synthetic": {"required_fields": ["checked"], "optional_fields": []}}}}
        verification = {**self.scope, "expected_revision": 2,
            "expected_client_updated_at": read.data["client_updated_at"].isoformat(),
            "protocol_reference": "synthetic-v1", "method": "synthetic", "fields": {"checked": "Synthetic evidence"}}
        with override_settings(MEDICAL_IDENTITY_VERIFICATION_POLICIES=policy):
            verified = self.api.post(url + "verify/", verification, format="json", HTTP_IDEMPOTENCY_KEY="api-verify")
            self.assertEqual(verified.status_code, 200, verified.data)
            self.assertEqual(verified.data["identity_status"], "verified")
            corrected = self.api.post(url + "correct/", {**verification, "expected_revision": 3,
                "full_name": "Corrected synthetic name", "demographics": {"address": "Rechecked address"},
                "reason": "Controlled correction"}, format="json", HTTP_IDEMPOTENCY_KEY="api-correct")
        self.assertEqual(corrected.status_code, 200, corrected.data)
        self.assertEqual(corrected.data["revision"], 4)
        final = self.api.get(f"{self.collection}by-client/{self.patient_client.pk}/", self.scope)
        self.assertEqual(final.status_code, 200, final.data)
        self.assertEqual(final.data["full_name"], "Corrected synthetic name")
        self.assertEqual(final.data["demographics"]["address"], "Rechecked address")
        self.assertEqual(MedicalAuditEvent.objects.filter(action="read").count(), 2)

    def test_create_replay_and_unknown_fields(self):
        pk = self.create_patient()
        replay = self.api.post(self.collection, self.create_data, format="json", HTTP_IDEMPOTENCY_KEY="api-create")
        self.assertEqual(replay.status_code, 200)
        self.assertTrue(replay.data["replayed"])
        self.assertEqual(replay.data["id"], pk)
        response = self.api.post(self.collection, {**self.create_data, "identity_status": "verified"},
            format="json", HTTP_IDEMPOTENCY_KEY="api-unknown")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(PatientProfile.objects.get(pk=pk).identity_status, "unverified")

    def test_access_projection_has_only_scope_and_current_exact_actions(self):
        url = self.collection + "access/"
        response = self.api.get(url, self.scope)
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data, {**self.scope, "actions": {
            "view": True, "create": True, "update": True, "approve": True}})
        self.assertEqual(response["Cache-Control"], "no-store, private")
        RolePermission.objects.filter(business_role=self.assignment.business_role,
            resource="medical_patients", action="approve").update(is_allowed=False)
        response = self.api.get(url, self.scope)
        self.assertEqual(response.data["actions"], {
            "view": True, "create": True, "update": True, "approve": False})
        self.assertFalse(MedicalAuditEvent.objects.exists())
        self.assignment.revoked_at = self.patient_client.updated_at
        self.assignment.save(update_fields=["revoked_at"])
        self.assertEqual(self.api.get(url, self.scope).status_code, 403)

    def test_access_projection_denies_owner_doctor_branch_and_invalid_query(self):
        url = self.collection + "access/"
        self.assertEqual(self.api.get(url, {**self.scope, "client_id": self.patient_client.pk}).status_code, 400)
        self.assertEqual(self.api.get(url, {**self.scope, "branch_id": 999999}).status_code, 403)
        self.api.force_authenticate(self.owner)
        denied = self.api.get(url, self.scope)
        self.assertEqual(denied.status_code, 403)
        self.assertEqual(denied["Cache-Control"], "no-store, private")
        self.api.force_authenticate(self.reception)
        self.assignment.kind = "doctor"
        self.assignment.save(update_fields=["kind"])
        self.assertEqual(self.api.get(url, self.scope).status_code, 403)

    def test_missing_idempotency_key_is_rejected(self):
        response = self.api.post(self.collection, self.create_data, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertFalse(PatientProfile.objects.exists())

    def test_no_store_on_success_denial_and_validation(self):
        pk = self.create_patient()
        responses = [self.api.get(f"{self.collection}{pk}/", self.scope), self.api.get(f"{self.collection}{pk}/")]
        self.api.force_authenticate(self.owner)
        responses.append(self.api.get(f"{self.collection}{pk}/", self.scope))
        self.assertEqual([r.status_code for r in responses], [200, 400, 403])
        for response in responses:
            self.assertEqual(response["Cache-Control"], "no-store, private")

    def test_owner_doctor_and_unauthenticated_cannot_use_reception_projection(self):
        pk = self.create_patient()
        self.api.force_authenticate(self.owner)
        self.assertEqual(self.api.get(f"{self.collection}{pk}/", self.scope).status_code, 403)
        self.assignment.kind = "doctor"
        self.assignment.save(update_fields=["kind"])
        self.api.force_authenticate(self.reception)
        self.assertEqual(self.api.get(f"{self.collection}{pk}/", self.scope).status_code, 403)
        self.api.force_authenticate(None)
        self.assertEqual(self.api.get(f"{self.collection}{pk}/", self.scope).status_code, 401)

    def test_branch_revocation_and_foreign_patient_denied(self):
        pk = self.create_patient()
        foreign = Business.objects.create(owner=self.owner, name="Foreign", slug="foreign-patient-api")
        client = Client.objects.create(business=foreign, full_name="Foreign")
        other = PatientProfile.objects.create(business=foreign, client=client, created_by=self.owner)
        self.assertEqual(self.api.get(f"{self.collection}{other.pk}/", self.scope).status_code, 404)
        self.crm_branch.branches.clear()
        self.assertEqual(self.api.get(f"{self.collection}{pk}/", self.scope).status_code, 403)

    def test_read_audit_failure_returns_no_patient_data(self):
        pk = self.create_patient()
        with patch("apps.medical.audit.MedicalAuditEvent.objects.create", side_effect=DatabaseError("synthetic")):
            response = self.api.get(f"{self.collection}{pk}/", self.scope)
        self.assertEqual(response.status_code, 503)
        self.assertNotIn("Private administrative address", response.content.decode())
        self.assertNotIn("000000000001", response.content.decode())
        self.assertFalse(MedicalAuditEvent.objects.filter(action="read").exists())

    def test_missing_key_returns_no_patient_data(self):
        pk = self.create_patient()
        with override_settings(MEDICAL_DATA_KEYS={}):
            response = self.api.get(f"{self.collection}{pk}/", self.scope)
        self.assertEqual(response.status_code, 503)
        self.assertNotIn("Private administrative address", response.content.decode())

    def test_generic_mutation_and_list_are_unavailable(self):
        pk = self.create_patient()
        for method in (self.api.put, self.api.patch, self.api.delete):
            self.assertEqual(method(f"{self.collection}{pk}/", {}, format="json").status_code, 405)
        self.assertEqual(self.api.get(self.collection, self.scope).status_code, 405)

    def test_stale_preliminary_update_is_conflict_and_preserves_data(self):
        pk = self.create_patient()
        response = self.api.post(f"{self.collection}{pk}/preliminary/", {**self.scope,
            "expected_revision": 2, "demographics": {}, "iin": None, "reason": "Stale editor"},
            format="json", HTTP_IDEMPOTENCY_KEY="stale")
        self.assertEqual(response.status_code, 409)
        patient = PatientProfile.objects.get(pk=pk)
        self.assertEqual(patient.revision, 1)
        self.assertIsNotNone(patient.iin_digest)

    def test_missing_protocol_is_safe_503_through_http(self):
        pk = self.create_patient()
        with override_settings(MEDICAL_IDENTITY_VERIFICATION_POLICIES=""):
            response = self.api.post(f"{self.collection}{pk}/verify/", {**self.scope, "expected_revision": 1,
                "expected_client_updated_at": self.patient_client.updated_at.isoformat(),
                "protocol_reference": "unknown", "method": "synthetic", "fields": {"secret": "Private evidence"}},
                format="json", HTTP_IDEMPOTENCY_KEY="missing-protocol")
        self.assertEqual(response.status_code, 503)
        self.assertNotIn("Private evidence", response.content.decode())
        self.assertEqual(PatientProfile.objects.get(pk=pk).identity_status, "unverified")

    def test_revoked_view_permission_and_archived_client_block_read(self):
        pk = self.create_patient()
        permission = RolePermission.objects.get(business_role=self.assignment.business_role, action="view")
        permission.is_allowed = False
        permission.save(update_fields=["is_allowed"])
        self.assertEqual(self.api.get(f"{self.collection}{pk}/", self.scope).status_code, 403)
        permission.is_allowed = True
        permission.save(update_fields=["is_allowed"])
        self.patient_client.is_archived = True
        self.patient_client.save(update_fields=["is_archived"])
        self.assertEqual(self.api.get(f"{self.collection}{pk}/", self.scope).status_code, 404)
