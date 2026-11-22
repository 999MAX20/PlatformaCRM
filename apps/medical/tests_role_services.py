from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone
from rest_framework.exceptions import NotFound, PermissionDenied, ValidationError

from apps.branches.models import Branch, BranchAccess
from apps.businesses.models import Business, BusinessCapability, BusinessMember, BusinessRole, RolePermission
from apps.businesses.serializers import BusinessRoleSerializer
from apps.core.domain_errors import IdempotencyConflict, InvalidTransition, ModuleDisabled
from apps.core.models import AuditLog, CRMCommandIdempotency
from .models import MedicalRoleAssignment
from .role_access import assert_medical_role_permission
from .role_services import assign_medical_role, create_medical_role, revoke_medical_role


class MedicalRoleServiceTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        users = get_user_model()
        cls.owner = users.objects.create_user(username="medical-command-owner", email="medical-command-owner@example.test")
        cls.employee = users.objects.create_user(username="medical-command-user", email="medical-command-user@example.test")
        cls.other = users.objects.create_user(username="medical-command-other", email="medical-command-other@example.test")
        cls.business = Business.objects.create(owner=cls.owner, name="Synthetic clinic", slug="medical-commands",
            business_type="dentistry", profile_key="dentistry", profile_version=2, profile_assigned_at=timezone.now())
        for key in ("medical_records", "clients", "appointments"):
            BusinessCapability.objects.create(business=cls.business, module_key=key, is_enabled=True)
        cls.crm_role = BusinessRole.objects.create(business=cls.business, name="CRM specialist")
        cls.member = BusinessMember.objects.create(business=cls.business, user=cls.employee,
                                                   business_role=cls.crm_role, role="specialist")
        cls.branch = Branch.objects.create(business=cls.business, name="Synthetic branch")
        cls.crm_branches = BranchAccess.objects.create(member=cls.member, all_branches=False)
        cls.crm_branches.branches.add(cls.branch)
        cls.rules = [{"resource": "medical_records", "action": "view", "scope": "own"}]

    def define(self, **overrides):
        return create_medical_role(**{"actor": self.owner, "business_id": self.business.pk, "name": "Doctor",
            "kind": "doctor", "permissions": self.rules, "idempotency_key": "define", **overrides})

    def assign(self, role, **overrides):
        return assign_medical_role(**{"actor": self.owner, "business_id": self.business.pk,
            "member_id": self.member.pk, "role_id": role.pk, "branch_ids": [self.branch.pk],
            "all_branches": False, "expected_revision": 0, "idempotency_key": "assign", **overrides})

    def revoke(self, assignment, **overrides):
        return revoke_medical_role(**{"actor": self.owner, "business_id": self.business.pk,
            "member_id": self.member.pk, "expected_revision": assignment.revision,
            "idempotency_key": "revoke", **overrides})

    def test_definition_assignment_replay_and_audit_do_not_change_crm_role(self):
        role, replayed = self.define()
        self.assertFalse(replayed)
        again, replayed = self.define()
        self.assertTrue(replayed)
        self.assertEqual(again.pk, role.pk)
        assignment, replayed = self.assign(role)
        self.assertFalse(replayed)
        again, replayed = self.assign(role)
        self.assertTrue(replayed)
        self.assertEqual(again.pk, assignment.pk)
        self.assertEqual(again.revision, 1)
        self.member.refresh_from_db()
        self.assertEqual(self.member.business_role_id, self.crm_role.pk)
        self.crm_branches.refresh_from_db()
        self.assertFalse(self.crm_branches.all_branches)
        self.assertEqual(AuditLog.objects.filter(metadata__kind="medical_role_assigned").count(), 1)
        self.assertEqual(AuditLog.objects.filter(metadata__kind="medical_role_defined").count(), 1)
        self.assertEqual(assert_medical_role_permission(self.employee, self.business, "medical_records", "view").assignment_id, assignment.pk)
        with self.assertRaises(PermissionDenied):
            assert_medical_role_permission(self.owner, self.business, "medical_records", "view")

    def test_replay_does_not_restore_revoked_assignment(self):
        role, _ = self.define()
        assignment, _ = self.assign(role)
        revoked, replayed = self.revoke(assignment)
        self.assertFalse(replayed)
        self.assertEqual(revoked.revision, 2)
        current, replayed = self.assign(role)
        self.assertTrue(replayed)
        self.assertIsNotNone(current.revoked_at)
        self.assertEqual(current.revision, 2)
        with self.assertRaises(PermissionDenied):
            assert_medical_role_permission(self.employee, self.business, "medical_records", "view")
        again, replayed = self.revoke(assignment)
        self.assertTrue(replayed)
        self.assertEqual(again.revision, 2)
        self.assertEqual(AuditLog.objects.filter(metadata__kind="medical_role_revoked").count(), 1)

    def test_explicit_regrant_requires_current_revision_and_new_key(self):
        role, _ = self.define()
        assignment, _ = self.assign(role)
        self.revoke(assignment)
        with self.assertRaises(InvalidTransition):
            self.assign(role, idempotency_key="stale-new")
        granted, replayed = self.assign(role, expected_revision=2, idempotency_key="regrant")
        self.assertFalse(replayed)
        self.assertEqual(granted.revision, 3)
        self.assertIsNone(granted.revoked_at)

    def test_same_key_different_payload_conflicts(self):
        self.define()
        with self.assertRaises(IdempotencyConflict):
            self.define(name="Changed")

    def test_assignment_noop_with_current_revision_does_not_repeat_audit(self):
        role, _ = self.define()
        self.assign(role)
        assignment, _ = self.assign(role, expected_revision=1, idempotency_key="same-state")
        self.assertEqual(assignment.revision, 1)
        self.assertEqual(AuditLog.objects.filter(metadata__kind="medical_role_assigned").count(), 1)

    def test_audit_failure_rolls_back_definition_permissions_and_command(self):
        with patch("apps.medical.role_services.write_actor_audit_log", side_effect=RuntimeError("Synthetic audit failure")):
            with self.assertRaises(RuntimeError):
                self.define()
        self.assertFalse(BusinessRole.objects.filter(preset_key="medical_doctor").exists())
        self.assertFalse(RolePermission.objects.filter(resource__startswith="medical_").exists())
        self.assertFalse(CRMCommandIdempotency.objects.exists())

    def test_audit_failure_rolls_back_assignment_and_revoke(self):
        role, _ = self.define()
        with patch("apps.medical.role_services.write_actor_audit_log", side_effect=RuntimeError("Synthetic audit failure")):
            with self.assertRaises(RuntimeError):
                self.assign(role)
        self.assertFalse(MedicalRoleAssignment.objects.exists())
        self.assertFalse(CRMCommandIdempotency.objects.filter(action="medical.role.assign").exists())
        assignment, _ = self.assign(role)
        with patch("apps.medical.role_services.write_actor_audit_log", side_effect=RuntimeError("Synthetic audit failure")):
            with self.assertRaises(RuntimeError):
                self.revoke(assignment)
        assignment.refresh_from_db()
        self.assertIsNone(assignment.revoked_at)
        self.assertEqual(assignment.revision, 1)

    def test_owner_transfer_and_account_disable_rechecked_before_replay(self):
        self.define()
        Business.objects.filter(pk=self.business.pk).update(owner=self.other)
        with self.assertRaises(PermissionDenied):
            self.define()
        Business.objects.filter(pk=self.business.pk).update(owner=self.owner)
        get_user_model().objects.filter(pk=self.owner.pk).update(is_active=False)
        with self.assertRaises(PermissionDenied):
            self.define()

    def test_nonowner_and_platform_owner_cannot_define_roles(self):
        with self.assertRaises(PermissionDenied):
            self.define(actor=self.employee)
        get_user_model().objects.filter(pk=self.owner.pk).update(is_superuser=True)
        with self.assertRaises(PermissionDenied):
            self.define()

    def test_self_assignment_and_inactive_employee_are_rejected(self):
        role, _ = self.define()
        own_member = BusinessMember.objects.create(business=self.business, user=self.owner, role="owner")
        with self.assertRaises(PermissionDenied):
            self.assign(role, member_id=own_member.pk)
        BusinessMember.objects.filter(pk=self.member.pk).update(is_active=False)
        with self.assertRaises(NotFound):
            self.assign(role)

    def test_foreign_member_role_and_branch_are_rejected(self):
        role, _ = self.define()
        foreign = Business.objects.create(owner=self.owner, name="Foreign", slug="medical-command-foreign")
        member = BusinessMember.objects.create(business=foreign, user=self.employee)
        foreign_role = BusinessRole.objects.create(business=foreign, name="Foreign", preset_key="medical_doctor")
        branch = Branch.objects.create(business=foreign, name="Foreign")
        with self.assertRaises(NotFound):
            self.assign(role, member_id=member.pk)
        with self.assertRaises(ValidationError):
            self.assign(foreign_role)
        with self.assertRaises(ValidationError):
            self.assign(role, branch_ids=[branch.pk])

    def test_network_scope_requires_existing_crm_network_grant(self):
        role, _ = self.define()
        with self.assertRaises(ValidationError):
            self.assign(role, branch_ids=[], all_branches=True)
        BranchAccess.objects.filter(pk=self.crm_branches.pk).update(all_branches=True)
        assignment, _ = self.assign(role, branch_ids=[], all_branches=True)
        self.assertTrue(assignment.all_branches)

    def test_revoke_works_with_module_and_employee_disabled(self):
        role, _ = self.define()
        assignment, _ = self.assign(role)
        BusinessCapability.objects.filter(business=self.business, module_key="medical_records").update(is_enabled=False)
        BusinessMember.objects.filter(pk=self.member.pk).update(is_active=False)
        revoked, _ = self.revoke(assignment)
        self.assertIsNotNone(revoked.revoked_at)
        with self.assertRaises(ModuleDisabled):
            self.define(name="Disabled", idempotency_key="disabled")

    def test_invalid_permissions_and_assistant_escalation_rejected(self):
        for rules in ([{"resource": "*", "action": "manage", "scope": "business"}],
                      [{"resource": "medical_records", "action": "view", "scope": "none"}],
                      self.rules * 2, []):
            with self.subTest(rules=rules), self.assertRaises(ValidationError):
                self.define(permissions=rules)
        with self.assertRaises(ValidationError):
            self.define(kind="assistant", permissions=[{"resource": "medical_documents", "action": "sign", "scope": "own"}])
        self.assertFalse(BusinessRole.objects.filter(preset_key__startswith="medical_").exists())

    def test_generic_role_editor_cannot_change_medical_definition(self):
        role, _ = self.define()
        serializer = BusinessRoleSerializer(instance=role, data={"preset_key": "medical_head"}, partial=True)
        self.assertFalse(serializer.is_valid())
        serializer = BusinessRoleSerializer(instance=self.crm_role, data={"preset_key": "medical_doctor"}, partial=True)
        self.assertFalse(serializer.is_valid())

    def test_audit_payload_contains_only_administrative_grant_snapshot(self):
        role, _ = self.define()
        assignment, _ = self.assign(role)
        audit = AuditLog.objects.get(metadata__kind="medical_role_assigned")
        self.assertEqual(audit.metadata["after"]["member"], self.member.pk)
        self.assertEqual(audit.metadata["after"]["revision"], assignment.revision)
        self.assertNotIn(self.employee.email, str(audit.metadata))
        self.assertNotIn(role.name, str(audit.metadata))

    def test_audit_failure_rolls_back_branch_change_and_revision(self):
        role, _ = self.define()
        assignment, _ = self.assign(role)
        second = Branch.objects.create(business=self.business, name="Second")
        self.crm_branches.branches.add(second)
        with patch("apps.medical.role_services.write_actor_audit_log", side_effect=RuntimeError("Synthetic audit failure")):
            with self.assertRaises(RuntimeError):
                self.assign(role, branch_ids=[second.pk], expected_revision=1, idempotency_key="change-branch")
        assignment.refresh_from_db()
        self.assertEqual(assignment.revision, 1)
        self.assertEqual(list(assignment.branches.values_list("pk", flat=True)), [self.branch.pk])
        self.assertFalse(CRMCommandIdempotency.objects.filter(idempotency_key="change-branch").exists())

    def test_generic_role_save_rechecks_reserved_preset_after_validation(self):
        serializer = BusinessRoleSerializer(instance=self.crm_role, data={"is_active": False}, partial=True)
        self.assertTrue(serializer.is_valid(), serializer.errors)
        BusinessRole.objects.filter(pk=self.crm_role.pk).update(preset_key="medical_doctor")
        with self.assertRaises(ValidationError):
            serializer.save()
        self.crm_role.refresh_from_db()
        self.assertTrue(self.crm_role.is_active)

    def test_invalid_identifiers_and_missing_command_key_are_rejected(self):
        for value in (True, None, -1, "1"):
            with self.subTest(value=value), self.assertRaises(ValidationError):
                self.define(business_id=value)
        with self.assertRaises(ValidationError):
            self.define(idempotency_key="")
        role, _ = self.define()
        with self.assertRaises(ValidationError):
            self.assign(role, member_id=True)
