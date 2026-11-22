from unittest.mock import patch

from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from apps.businesses.models import Business, BusinessCapability, BusinessMember, BusinessRole
from apps.core.models import AuditLog, CRMCommandIdempotency
from . import tests_role_services as fixtures
from .identity_crypto import MedicalKeyUnavailable
from .models import MedicalRoleAssignment, MedicalRoleRevision
from .tests_patient_services import key


@override_settings(MEDICAL_DATA_KEYS={"test": key(7)}, MEDICAL_DATA_ACTIVE_KEY_ID="test",
                   MEDICAL_IDENTITY_INDEX_KEY=key(8))
class MedicalRoleAPITests(TestCase):
    @classmethod
    def setUpTestData(cls):
        fixtures.MedicalRoleServiceTests.setUpTestData.__func__(cls)

    def setUp(self):
        self.api = APIClient()
        self.api.force_authenticate(self.owner)
        self.root = "/api/medical/role-management/"
        self.definition = {"business_id": self.business.pk, "name": "Synthetic role", "kind": "doctor",
                           "permissions": self.rules}

    def post(self, action, body, token="command"):
        return self.api.post(f"{self.root}{action}/", body, format="json", HTTP_IDEMPOTENCY_KEY=token)

    def proposal(self):
        response = self.post("roles", self.definition, "define")
        self.assertEqual(response.status_code, 201, response.data)
        return {"business_id": self.business.pk, "member_id": self.member.pk, "role_id": response.data["id"],
                "branch_ids": [self.branch.pk], "all_branches": False, "expected_revision": 0,
                "reason": "Synthetic private grant"}

    def test_create_assign_history_revoke_and_replay(self):
        body = self.proposal()
        self.assertEqual(self.post("roles", self.definition, "define").status_code, 200)
        response = self.post("assign", body)
        self.assertEqual(response.status_code, 200, response.data)
        self.assertIn("no-store", response["Cache-Control"])
        self.assertEqual(response.data["revision"], 1)
        self.assertNotIn("Synthetic private", str(response.data))
        self.assertTrue(self.post("assign", body).data["replayed"])
        revoke = {"business_id": self.business.pk, "member_id": self.member.pk,
                  "expected_revision": 1, "reason": "Synthetic private revoke"}
        response = self.post("revoke", revoke, "revoke")
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data["revision"], 2)
        self.assertTrue(self.post("revoke", revoke, "revoke").data["replayed"])
        history = self.api.get(f"{self.root}history/", {"business_id": self.business.pk, "member_id": self.member.pk})
        self.assertEqual([r["reason"] for r in history.data["results"]], [body["reason"], revoke["reason"]])
        self.assertEqual(MedicalRoleRevision.objects.count(), 2)
        self.member.refresh_from_db()
        self.assertEqual(self.member.business_role_id, self.crm_role.pk)

    def test_stale_revision_and_changed_retry_payload_are_conflicts(self):
        body = self.proposal()
        self.assertEqual(self.post("assign", body).status_code, 200)
        self.assertEqual(self.post("assign", body | {"reason": "Changed"}).status_code, 409)
        self.assertEqual(self.post("assign", body, "stale").status_code, 409)
        self.assertEqual(MedicalRoleRevision.objects.count(), 1)

    def test_reason_key_fields_and_permissions_are_validated(self):
        body = self.proposal()
        for invalid in ({key: value for key, value in body.items() if key != "reason"},
                        body | {"reason": "  "}, body | {"reason": "x" * 2001}, body | {"actor": self.owner.pk}):
            self.assertEqual(self.post("assign", invalid).status_code, 400)
        self.assertEqual(self.api.post(f"{self.root}assign/", body, format="json").status_code, 400)
        nested = self.definition | {"permissions": [self.rules[0] | {"is_allowed": True}]}
        self.assertEqual(self.post("roles", nested, "nested").status_code, 400)
        unsafe = self.definition | {"kind": "assistant", "permissions": [
            {"resource": "medical_documents", "action": "sign", "scope": "business"}]}
        self.assertEqual(self.post("roles", unsafe, "unsafe").status_code, 400)
        self.assertFalse(MedicalRoleAssignment.objects.exists())

    def test_employee_owner_transfer_and_self_assignment_are_denied(self):
        body = self.proposal()
        self.api.force_authenticate(self.employee)
        self.assertEqual(self.post("assign", body).status_code, 403)
        self.assertEqual(self.post("roles", self.definition).status_code, 403)
        self.api.force_authenticate(self.owner)
        owner_member = BusinessMember.objects.create(business=self.business, user=self.owner, role="owner")
        self.assertEqual(self.post("assign", body | {"member_id": owner_member.pk}).status_code, 403)
        self.assertEqual(self.post("assign", body).status_code, 200)
        Business.objects.filter(pk=self.business.pk).update(owner=self.other)
        self.assertEqual(self.post("assign", body).status_code, 403)
        revoke = {"business_id": self.business.pk, "member_id": self.member.pk, "expected_revision": 1, "reason": "Revocation"}
        self.assertEqual(self.post("revoke", revoke).status_code, 403)

    def test_foreign_members_roles_and_business_are_rejected(self):
        body = self.proposal()
        other = Business.objects.create(owner=self.other, name="Other", slug="role-api-other")
        member = BusinessMember.objects.create(business=other, user=self.other)
        role = BusinessRole.objects.create(business=other, name="Foreign", preset_key="medical_doctor")
        self.assertEqual(self.post("assign", body | {"business_id": other.pk}).status_code, 403)
        self.assertEqual(self.post("assign", body | {"member_id": member.pk}).status_code, 404)
        self.assertEqual(self.post("assign", body | {"member_id": 999999}).status_code, 404)
        self.assertEqual(self.post("assign", body | {"role_id": role.pk}).status_code, 400)
        self.assertFalse(MedicalRoleAssignment.objects.exists())

    def test_revocation_remains_available_when_module_and_member_disabled(self):
        body = self.proposal()
        self.post("assign", body)
        BusinessCapability.objects.filter(business=self.business, module_key="medical_records").update(is_enabled=False)
        BusinessMember.objects.filter(pk=self.member.pk).update(is_active=False)
        response = self.post("revoke", {"business_id": self.business.pk, "member_id": self.member.pk,
            "expected_revision": 1, "reason": "Synthetic disabled revocation"}, "revoke")
        self.assertEqual(response.status_code, 200, response.data)
        self.assertIsNotNone(response.data["revoked_at"])

    def test_outage_has_no_partial_assignment_and_same_key_can_retry(self):
        body = self.proposal()
        with patch("apps.medical.role_basis.encrypt_medical_value", side_effect=MedicalKeyUnavailable()):
            response = self.post("assign", body)
        self.assertEqual(response.status_code, 503)
        self.assertIn("no-store", response["Cache-Control"])
        self.assertNotIn(body["reason"], str(response.data))
        self.assertFalse(MedicalRoleAssignment.objects.exists())
        self.assertFalse(MedicalRoleRevision.objects.exists())
        self.assertFalse(AuditLog.objects.filter(metadata__kind="medical_role_assigned").exists())
        self.assertFalse(CRMCommandIdempotency.objects.filter(action="medical.role.assign").exists())
        self.assertEqual(self.post("assign", body).status_code, 200)
