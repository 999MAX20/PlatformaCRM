from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from rest_framework.exceptions import NotFound, PermissionDenied, ValidationError
from rest_framework.test import APIClient

from apps.branches.models import Branch
from apps.businesses.models import Business, BusinessCapability, BusinessMember, BusinessRole
from .role_access import assert_medical_role_permission
from .role_reads import (read_medical_role_workspace, read_medical_role_definitions,
                         read_medical_role_members, read_medical_role_member_context,
                         read_medical_role_member_branches)
from . import tests_role_services as fixtures
from .tests_patient_services import key


@override_settings(MEDICAL_DATA_KEYS={"test": key(7)}, MEDICAL_DATA_ACTIVE_KEY_ID="test",
                   MEDICAL_IDENTITY_INDEX_KEY=key(8))
class MedicalRoleReadTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        fixtures.MedicalRoleServiceTests.setUpTestData.__func__(cls)

    define = fixtures.MedicalRoleServiceTests.define
    assign = fixtures.MedicalRoleServiceTests.assign
    revoke = fixtures.MedicalRoleServiceTests.revoke

    def read(self, service, **kwargs):
        return service(**({"actor": self.owner, "business_id": self.business.pk} | kwargs))

    def context(self, **kwargs):
        return self.read(read_medical_role_member_context, **({"member_id": self.member.pk} | kwargs))

    def test_owner_reads_definition_assignment_without_receiving_clinical_role(self):
        role, _ = self.define()
        assignment, _ = self.assign(role)
        rows = self.read(read_medical_role_definitions)["results"]
        self.assertEqual([row["id"] for row in rows], [role.pk])
        self.assertEqual(rows[0]["permissions"], [dict(self.rules[0], is_allowed=True)])
        result = self.context()
        self.assertEqual(result["assignment"]["revision"], assignment.revision)
        self.assertEqual(result["assignment"]["branches"], [self.branch.pk])
        self.assertTrue(result["can_assign"])
        self.assertTrue(result["can_revoke"])
        self.assertFalse(result["can_assign_all_branches"])
        with self.assertRaises(PermissionDenied):
            assert_medical_role_permission(self.owner, self.business, "medical_records", "view")

    def test_lists_are_tenant_scoped_paginated_and_searchable(self):
        first, _ = self.define()
        second, _ = self.define(name="Second", idempotency_key="second")
        other_business = Business.objects.create(owner=self.other, name="Other", slug="role-read-other")
        BusinessRole.objects.create(business=other_business, name="Foreign", preset_key="medical_doctor")
        BusinessMember.objects.create(business=other_business, user=self.other)
        page = self.read(read_medical_role_definitions, limit=1)
        self.assertEqual(page["next_after_id"], first.pk)
        last = self.read(read_medical_role_definitions, after_id=page["next_after_id"], limit=1)
        self.assertEqual([r["id"] for r in last["results"]], [second.pk])
        self.assertIsNone(last["next_after_id"])
        self.assertEqual(self.read(read_medical_role_definitions, query="Second")["results"][0]["id"], second.pk)
        self.assertEqual(self.read(read_medical_role_definitions, query="absent")["results"], [])
        self.assertEqual([r["id"] for r in self.read(read_medical_role_members)["results"]], [self.member.pk])
        self.assertEqual(self.read(read_medical_role_members, after_id=self.member.pk)["results"], [])

    def test_every_read_requires_current_owner_not_medical_or_crm_admin(self):
        role, _ = self.define(kind="head")
        self.assign(role)
        BusinessMember.objects.filter(pk=self.member.pk).update(role="admin")
        reads = [(read_medical_role_workspace, {}), (read_medical_role_definitions, {}),
                 (read_medical_role_members, {}), (read_medical_role_member_context, {"member_id": self.member.pk}),
                 (read_medical_role_member_branches, {"member_id": self.member.pk})]
        for actor in (self.employee, self.other):
            for service, params in reads:
                with self.subTest(actor=actor.pk, service=service.__name__), self.assertRaises(PermissionDenied):
                    self.read(service, actor=actor, **params)
        Business.objects.filter(pk=self.business.pk).update(owner=self.other)
        with self.assertRaises(PermissionDenied):
            self.read(read_medical_role_workspace)
        self.assertIn("can_assign", self.read(read_medical_role_workspace, actor=self.other))

    def test_disabled_account_and_platform_owner_are_denied(self):
        get_user_model().objects.filter(pk=self.owner.pk).update(is_active=False)
        with self.assertRaises(PermissionDenied):
            self.context()
        get_user_model().objects.filter(pk=self.owner.pk).update(is_active=True, is_superuser=True)
        with self.assertRaises(PermissionDenied):
            self.context()

    def test_disabled_module_and_inactive_member_can_be_read_for_revocation(self):
        role, _ = self.define()
        assignment, _ = self.assign(role)
        BusinessCapability.objects.filter(business=self.business, module_key="medical_records").update(is_enabled=False)
        BusinessMember.objects.filter(pk=self.member.pk).update(is_active=False)
        get_user_model().objects.filter(pk=self.employee.pk).update(is_active=False)
        result = self.context()
        self.assertFalse(result["can_assign"])
        self.assertTrue(result["can_revoke"])
        self.assertFalse(result["member"]["is_active"])
        self.assertFalse(self.read(read_medical_role_workspace)["can_assign"])
        self.revoke(assignment)
        self.assertFalse(self.context()["can_revoke"])

    def test_self_assignment_is_not_offered(self):
        member = BusinessMember.objects.create(business=self.business, user=self.owner, role="owner")
        result = self.context(member_id=member.pk)
        self.assertFalse(result["can_assign"])
        self.assertIsNone(result["assignment"])
        self.assertFalse(result["can_revoke"])

    def test_foreign_and_missing_member_are_indistinguishable(self):
        business = Business.objects.create(owner=self.other, name="Other", slug="role-read-foreign")
        member = BusinessMember.objects.create(business=business, user=self.other)
        for member_id in (member.pk, 999999):
            for service in (read_medical_role_member_context, read_medical_role_member_branches):
                with self.subTest(member=member_id, service=service.__name__), self.assertRaises(NotFound):
                    self.read(service, member_id=member_id)

    def test_branch_options_intersect_current_crm_access(self):
        Branch.objects.create(business=self.business, name="Not granted")
        result = self.read(read_medical_role_member_branches, member_id=self.member.pk)
        self.assertEqual(result["results"], [{"id": self.branch.pk, "name": self.branch.name}])
        self.crm_branches.branches.clear()
        self.assertEqual(self.read(read_medical_role_member_branches, member_id=self.member.pk)["results"], [])

    def test_permission_choices_preserve_assistant_limits(self):
        data = self.read(read_medical_role_workspace)
        assistant = data["permissions_by_kind"]["assistant"]
        self.assertFalse(any(action in {"sign", "issue", "export", "manage"} for row in assistant for action in row["actions"]))
        self.assertFalse(any(row["resource"] == "medical_participation" for row in assistant))

    def test_page_limits_and_parameters_are_strict(self):
        for params in ({"limit": 0}, {"limit": 51}, {"limit": True}, {"after_id": 0}, {"query": "x" * 101}):
            with self.subTest(params=params), self.assertRaises(ValidationError):
                self.read(read_medical_role_definitions, **params)

    def test_http_routes_are_read_only_private_and_authorized(self):
        api = APIClient()
        api.force_authenticate(self.owner)
        root = "/api/medical/role-management/"
        for route, extra in (("workspace", {}), ("roles", {}), ("members", {}),
                             ("member-context", {"member_id": self.member.pk}), ("branches", {"member_id": self.member.pk}),
                             ("history", {"member_id": self.member.pk})):
            params = {"business_id": self.business.pk, **extra}
            response = api.get(f"{root}{route}/", params)
            self.assertEqual(response.status_code, 200, response.data)
            self.assertIn("no-store", response["Cache-Control"])
            self.assertEqual(api.get(f"{root}{route}/", params | {"unexpected": "value"}).status_code, 400)
            if route != "roles":
                self.assertEqual(api.post(f"{root}{route}/", params).status_code, 405)
            api.force_authenticate(self.employee)
            denial = api.get(f"{root}{route}/", params)
            self.assertEqual(denial.status_code, 403)
            self.assertIn("no-store", denial["Cache-Control"])
            api.force_authenticate(self.owner)
