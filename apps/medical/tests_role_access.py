from types import SimpleNamespace

from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from django.test import TestCase
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.test import APIClient

from apps.branches.models import Branch, BranchAccess
from apps.businesses.models import Business, BusinessCapability, BusinessMember, BusinessRole, RolePermission
from apps.businesses.role_services import update_role_visibility
from apps.businesses.serializers import RolePermissionSerializer
from apps.core.domain_errors import ModuleDisabled
from .models import MedicalRoleAssignment
from .role_access import assert_medical_role_permission, assert_medical_branch_permission


class MedicalRoleAccessTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        users = get_user_model()
        cls.owner = users.objects.create_user(username="medical-role-owner", email="medical-role-owner@example.test")
        cls.doctor = users.objects.create_user(username="medical-role-doctor", email="medical-role-doctor@example.test")
        cls.business = Business.objects.create(owner=cls.owner, name="Medical roles", slug="medical-role",
            business_type="dentistry", profile_key="dentistry", profile_version=2, profile_assigned_at=timezone.now())
        for key in ("medical_records", "clients", "appointments"):
            BusinessCapability.objects.create(business=cls.business, module_key=key, is_enabled=True)
        cls.role = BusinessRole.objects.create(business=cls.business, name="Explicit medical role")
        cls.member = BusinessMember.objects.create(business=cls.business, user=cls.doctor, role="specialist")
        cls.assignment = MedicalRoleAssignment.objects.create(member=cls.member, business_role=cls.role,
            kind="doctor", granted_by=cls.owner)
        cls.permission = RolePermission.objects.create(business_role=cls.role, resource="medical_records",
            action="view", scope="own", is_allowed=True)
        cls.first = Branch.objects.create(business=cls.business, name="First")
        cls.second = Branch.objects.create(business=cls.business, name="Second")
        cls.assignment.branches.add(cls.first)
        cls.crm_grant = BranchAccess.objects.create(member=cls.member, all_branches=True)

    def check(self, user=None, resource="medical_records", action="view"):
        return assert_medical_role_permission(user or self.doctor, self.business, resource, action)

    def test_explicit_medical_assignment_is_separate_from_crm_membership_role(self):
        result = self.check()
        self.assertEqual((result.assignment_id, result.kind, result.scope), (self.assignment.pk, "doctor", "own"))
        self.assertIsNone(self.member.business_role_id)

    def test_owner_and_platform_admin_have_no_implicit_medical_role(self):
        with self.assertRaises(PermissionDenied):
            self.check(self.owner)
        get_user_model().objects.filter(pk=self.doctor.pk).update(is_superuser=True)
        with self.assertRaises(PermissionDenied):
            self.check()
        get_user_model().objects.filter(pk=self.doctor.pk).update(is_superuser=False, role="platform_manager")
        with self.assertRaises(PermissionDenied):
            self.check()

    def test_anonymous_and_unknown_actions_fail_closed(self):
        with self.assertRaises(PermissionDenied):
            self.check(AnonymousUser())
        for resource, action in (("clients", "view"), ("medical_records", "unknown")):
            with self.subTest(resource=resource), self.assertRaises(PermissionDenied):
                self.check(resource=resource, action=action)

    def test_member_or_account_revocation_is_observed_on_loaded_instances(self):
        self.check()
        self.doctor._permission_read_memberships = {(self.business._state.db, self.business.pk): self.member}
        BusinessMember.objects.filter(pk=self.member.pk).update(is_active=False)
        with self.assertRaises(PermissionDenied):
            self.check()
        BusinessMember.objects.filter(pk=self.member.pk).update(is_active=True)
        get_user_model().objects.filter(pk=self.doctor.pk).update(is_active=False)
        with self.assertRaises(PermissionDenied):
            self.check()

    def test_assignment_and_role_revocation_are_immediate(self):
        self.check()
        MedicalRoleAssignment.objects.filter(pk=self.assignment.pk).update(revoked_at=timezone.now())
        with self.assertRaises(PermissionDenied):
            self.check()
        MedicalRoleAssignment.objects.filter(pk=self.assignment.pk).update(revoked_at=None)
        BusinessRole.objects.filter(pk=self.role.pk).update(is_active=False)
        with self.assertRaises(PermissionDenied):
            self.check()

    def test_exact_rule_required_without_manage_or_wildcard_fallback(self):
        RolePermission.objects.filter(pk=self.permission.pk).delete()
        RolePermission.objects.create(business_role=self.role, resource="medical_records", action="manage")
        RolePermission.objects.create(business_role=self.role, resource="*", action="view")
        with self.assertRaises(PermissionDenied):
            self.check()

    def test_permission_revocation_and_none_scope_are_observed(self):
        self.check()
        RolePermission.objects.filter(pk=self.permission.pk).update(is_allowed=False)
        with self.assertRaises(PermissionDenied):
            self.check()
        RolePermission.objects.filter(pk=self.permission.pk).update(is_allowed=True, scope="none")
        with self.assertRaises(PermissionDenied):
            self.check()

    def test_disabled_capability_rejects_explicit_grants(self):
        self.check()
        BusinessCapability.objects.filter(business=self.business, module_key="medical_records").update(is_enabled=False)
        with self.assertRaises(ModuleDisabled):
            self.check()

    def test_foreign_role_and_foreign_business_are_not_accepted(self):
        foreign = Business.objects.create(owner=self.owner, name="Foreign", slug="medical-role-foreign")
        foreign_role = BusinessRole.objects.create(business=foreign, name="Foreign role")
        RolePermission.objects.create(business_role=foreign_role, resource="medical_records", action="view")
        with self.assertRaises(PermissionDenied):
            assert_medical_role_permission(self.doctor, foreign, "medical_records", "view")
        MedicalRoleAssignment.objects.filter(pk=self.assignment.pk).update(business_role=foreign_role)
        with self.assertRaises(PermissionDenied):
            self.check()

    def test_branch_scope_intersects_medical_assignment_and_crm_grant(self):
        def check(branch):
            return assert_medical_branch_permission(self.doctor, self.business, "medical_records", "view", branch=branch)
        check(self.first)
        with self.assertRaises(PermissionDenied):
            check(self.second)
        BranchAccess.objects.filter(pk=self.crm_grant.pk).update(all_branches=False)
        self.crm_grant.branches.add(self.second)
        with self.assertRaises(PermissionDenied):
            check(self.first)
        MedicalRoleAssignment.objects.filter(pk=self.assignment.pk).update(all_branches=True)
        check(self.second)
        with self.assertRaises(PermissionDenied):
            check(self.first)

    def test_archived_branch_can_be_checked_for_history_but_not_current_work(self):
        Branch.objects.filter(pk=self.first.pk).update(is_active=False, archived_at=timezone.now())
        with self.assertRaises(PermissionDenied):
            assert_medical_branch_permission(self.doctor, self.business, "medical_records", "view", branch=self.first)
        assert_medical_branch_permission(self.doctor, self.business, "medical_records", "view",
                                        branch=self.first, require_active=False)

    def test_assistant_cannot_sign_issue_export_or_manage_participation_even_with_rule(self):
        MedicalRoleAssignment.objects.filter(pk=self.assignment.pk).update(kind="assistant")
        self.assertEqual(self.check().kind, "assistant")
        for resource, action in (("medical_documents", "sign"), ("medical_documents", "issue"),
                                 ("medical_files", "export"), ("medical_participation", "manage")):
            RolePermission.objects.create(business_role=self.role, resource=resource, action=action)
            with self.subTest(action=action), self.assertRaises(PermissionDenied):
                self.check(resource=resource, action=action)

    def test_reception_cannot_read_clinical_record_even_with_rule(self):
        MedicalRoleAssignment.objects.filter(pk=self.assignment.pk).update(kind="reception")
        with self.assertRaises(PermissionDenied):
            self.check()

    def test_generic_permission_writer_cannot_create_or_modify_medical_rules(self):
        serializer = RolePermissionSerializer(data={"business_role": self.role.pk,
            "resource": "medical_documents", "action": "sign", "scope": "business", "is_allowed": True})
        self.assertFalse(serializer.is_valid())
        for values in ({"scope": "business"}, {"resource": "clients"}):
            serializer = RolePermissionSerializer(instance=self.permission, data=values, partial=True)
            self.assertFalse(serializer.is_valid())
        normal = RolePermissionSerializer(data={"business_role": self.role.pk,
            "resource": "clients", "action": "view", "scope": "own", "is_allowed": True})
        self.assertTrue(normal.is_valid(), normal.errors)
        normal.save()

    def test_bulk_visibility_cannot_broaden_medical_rules(self):
        with self.assertRaises(ValidationError):
            update_role_visibility(request=SimpleNamespace(user=self.owner), role=self.role,
                                   permission_ids=[self.permission.pk], scope="business")
        self.permission.refresh_from_db()
        self.assertEqual(self.permission.scope, "own")

    def test_generic_permission_save_rechecks_after_initial_validation(self):
        normal = RolePermission.objects.create(business_role=self.role, resource="clients", action="update", scope="own")
        serializer = RolePermissionSerializer(instance=normal, data={"scope": "business"}, partial=True)
        self.assertTrue(serializer.is_valid(), serializer.errors)
        RolePermission.objects.filter(pk=normal.pk).update(resource="medical_patients")
        with self.assertRaises(ValidationError):
            serializer.save()
        normal.refresh_from_db()
        self.assertEqual(normal.scope, "own")

    def test_team_delete_retains_medical_history_but_disabling_membership_still_works(self):
        api = APIClient()
        api.force_authenticate(self.owner)
        for path in (f"/api/team/members/{self.member.pk}/", f"/api/team/roles/{self.role.pk}/"):
            response = api.delete(path)
            self.assertEqual(response.status_code, 409, response.data)
        self.assertTrue(MedicalRoleAssignment.objects.filter(pk=self.assignment.pk).exists())
        response = api.patch(f"/api/team/members/{self.member.pk}/", {"is_active": False}, format="json")
        self.assertEqual(response.status_code, 200, response.data)
        with self.assertRaises(PermissionDenied):
            self.check()

    def test_http_permission_writer_cannot_add_medical_privileges(self):
        api = APIClient()
        api.force_authenticate(self.owner)
        response = api.post("/api/team/role-permissions/", {"business_role": self.role.pk,
            "resource": "medical_documents", "action": "sign", "scope": "business", "is_allowed": True}, format="json")
        self.assertEqual(response.status_code, 400, response.data)
        response = api.patch(f"/api/team/role-permissions/{self.permission.pk}/", {"scope": "business"}, format="json")
        self.assertEqual(response.status_code, 400, response.data)
        self.permission.refresh_from_db()
        self.assertEqual(self.permission.scope, "own")

    def test_self_granted_medical_authority_is_rejected(self):
        MedicalRoleAssignment.objects.filter(pk=self.assignment.pk).update(granted_by=self.doctor)
        with self.assertRaises(PermissionDenied):
            self.check()

    def test_explicit_owner_medical_assignment_does_not_bypass_its_branch_scope(self):
        member = BusinessMember.objects.create(business=self.business, user=self.owner, role="owner")
        assignment = MedicalRoleAssignment.objects.create(member=member, business_role=self.role,
            kind="head", granted_by=self.doctor)
        assignment.branches.add(self.first)
        self.assertEqual(self.check(self.owner).assignment_id, assignment.pk)
        assert_medical_branch_permission(self.owner, self.business, "medical_records", "view", branch=self.first)
        with self.assertRaises(PermissionDenied):
            assert_medical_branch_permission(self.owner, self.business, "medical_records", "view", branch=self.second)

    def test_all_branches_does_not_include_foreign_business(self):
        foreign = Business.objects.create(owner=self.owner, name="Foreign", slug="medical-branch-foreign")
        branch = Branch.objects.create(business=foreign, name="Foreign branch")
        MedicalRoleAssignment.objects.filter(pk=self.assignment.pk).update(all_branches=True)
        with self.assertRaises(PermissionDenied):
            assert_medical_branch_permission(self.doctor, self.business, "medical_records", "view", branch=branch)

    def test_stale_owner_or_platform_flags_cannot_widen_branch_scope(self):
        member = BusinessMember.objects.create(business=self.business, user=self.owner, role="owner")
        assignment = MedicalRoleAssignment.objects.create(member=member, business_role=self.role,
            kind="head", granted_by=self.doctor, all_branches=True)
        Business.objects.filter(pk=self.business.pk).update(owner=self.doctor)
        self.owner.is_superuser = True
        with self.assertRaises(PermissionDenied):
            assert_medical_branch_permission(self.owner, self.business, "medical_records", "view", branch=self.first)
        self.assertTrue(MedicalRoleAssignment.objects.filter(pk=assignment.pk, revoked_at__isnull=True).exists())
