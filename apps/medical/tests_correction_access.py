from datetime import timedelta
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.db import DatabaseError, IntegrityError, transaction
from django.test import TestCase, override_settings
from rest_framework.exceptions import PermissionDenied

from apps.branches.models import BranchAccess
from apps.businesses.models import BusinessMember, RolePermission
from apps.core.domain_errors import InvalidTransition
from apps.core.models import CRMCommandIdempotency
from . import tests_encounter_services as fixtures
from . import tests_patient_services as crypto_fixtures
from .audit import MedicalAuditUnavailable
from .correction_access_context import assert_correction_access, observe_correction_access_expiry
from .correction_access_services import close_correction_access, request_correction_access, review_correction_access
from .correction_access_reads import read_correction_request, read_correction_target
from .encounter_services import save_primary_encounter_draft
from .models import MedicalAuditEvent, MedicalCorrectionAccess, MedicalRoleAssignment


@override_settings(MEDICAL_DATA_KEYS={"test": crypto_fixtures.key(7)}, MEDICAL_DATA_ACTIVE_KEY_ID="test",
                   MEDICAL_IDENTITY_INDEX_KEY=crypto_fixtures.key(8))
class CorrectionAccessTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        fixtures.PrimaryEncounterDraftTests.setUpTestData.__func__(cls)
        cls.head = get_user_model().objects.create_user(username="correction-head", email="correction-head@example.test")
        cls.head_member = BusinessMember.objects.create(business=cls.business, user=cls.head, role="specialist")
        cls.head_assignment = MedicalRoleAssignment.objects.create(member=cls.head_member, business_role=cls.role,
            kind="head", granted_by=cls.owner)
        cls.head_assignment.branches.add(cls.first)
        BranchAccess.objects.create(member=cls.head_member, all_branches=True)
        RolePermission.objects.create(business_role=cls.role, resource="medical_records", action="manage", scope="business")

    def request(self, **overrides):
        return request_correction_access(**(dict(actor=self.doctor, business_id=self.business.pk,
            encounter_id=self.encounter_record.pk, expected_patient_revision=self.patient.revision,
            expected_target_revision=1, reason="Synthetic private request", idempotency_key="request") | overrides))

    def review(self, item, **overrides):
        return review_correction_access(**(dict(actor=self.head, business_id=self.business.pk, request_id=item.pk,
            expected_revision=1, decision="approve", reason="Synthetic review", idempotency_key="review") | overrides))

    def allowed(self, item, **overrides):
        return assert_correction_access(**(dict(actor=self.doctor, business=self.business, request_id=item.pk,
            encounter_id=self.encounter_record.pk) | overrides))

    def test_request_has_no_access_approval_exactly_24_hours_and_private_replay(self):
        item, replayed = self.request()
        self.assertFalse(replayed)
        with self.assertRaises(PermissionDenied):
            self.allowed(item)
        self.assertTrue(self.request()[1])
        item, _ = self.review(item)
        self.assertEqual(item.expires_at - item.reviewed_at, timedelta(hours=24))
        self.assertEqual(self.allowed(item).pk, item.pk)
        self.assertTrue(self.review(item)[1])
        self.assertEqual(list(MedicalAuditEvent.objects.order_by("pk").values_list("correction_access_revision", flat=True)), [1, 2])
        self.assertNotIn("Synthetic private request", item.reason_encrypted)
        self.assertNotIn("Synthetic", str(list(CRMCommandIdempotency.objects.values())))

    def test_boundary_expires_and_observation_is_idempotent(self):
        item = self.review(self.request()[0])[0]
        with patch("apps.medical.correction_access_context.timezone.now", return_value=item.expires_at - timedelta(microseconds=1)):
            self.allowed(item)
        with patch("apps.medical.correction_access_context.timezone.now", return_value=item.expires_at):
            with self.assertRaises(PermissionDenied):
                self.allowed(item)
            self.assertTrue(observe_correction_access_expiry(actor=self.doctor, business_id=self.business.pk, request_id=item.pk))
            self.assertFalse(observe_correction_access_expiry(actor=self.doctor, business_id=self.business.pk, request_id=item.pk))
        item.refresh_from_db()
        self.assertEqual((item.state, item.closed_at, item.revision), ("expired", item.expires_at, 3))
        self.assertEqual(MedicalAuditEvent.objects.filter(action="correction_access_expired").count(), 1)

    def test_current_role_and_branch_override_active_access_and_replay(self):
        item = self.review(self.request()[0])[0]
        self.assignment.branches.clear()
        with self.assertRaises(PermissionDenied):
            self.allowed(item)
        with self.assertRaises(PermissionDenied):
            self.request()

    def test_doctor_owner_self_review_and_other_target_denied(self):
        item = self.request()[0]
        for actor in (self.doctor, self.owner):
            with self.subTest(actor=actor.pk), self.assertRaises(PermissionDenied):
                self.review(item, actor=actor)
        MedicalRoleAssignment.objects.filter(pk=self.assignment.pk).update(kind="head")
        with self.assertRaises(PermissionDenied):
            self.review(item, actor=self.doctor)
        self.review(item)
        with self.assertRaises(PermissionDenied):
            self.allowed(item, encounter_id=self.encounter_record.pk + 999)

    def test_duplicate_stale_source_and_requester_revocation_prevent_approval(self):
        item = self.request()[0]
        with self.assertRaises(InvalidTransition):
            self.request(idempotency_key="duplicate")
        type(self.encounter_record).objects.filter(pk=self.encounter_record.pk).update(revision=2)
        with self.assertRaises(InvalidTransition):
            self.review(item)
        type(self.encounter_record).objects.filter(pk=self.encounter_record.pk).update(revision=1)
        BusinessMember.objects.filter(pk=self.member.pk).update(is_active=False)
        with self.assertRaises(PermissionDenied):
            self.review(item)

    def test_close_variants_and_terminal_state_cannot_be_reopened(self):
        for decision in ("withdraw", "complete", "revoke"):
            with self.subTest(decision=decision):
                item = self.request(idempotency_key="request-" + decision)[0]
                if decision != "withdraw":
                    item = self.review(item, idempotency_key="review-" + decision)[0]
                kwargs = dict(actor=self.head if decision == "revoke" else self.doctor, business_id=self.business.pk,
                    request_id=item.pk, expected_revision=item.revision, decision=decision,
                    reason="Synthetic close", idempotency_key="close-" + decision)
                closed, _ = close_correction_access(**kwargs)
                self.assertIn(closed.state, {"withdrawn", "completed", "revoked"})
                self.assertTrue(close_correction_access(**kwargs)[1])
                with self.assertRaises(InvalidTransition):
                    self.review(closed, expected_revision=closed.revision, idempotency_key="reopen-" + decision)
                with self.assertRaises(PermissionDenied):
                    self.allowed(closed)

    def test_audit_failure_rolls_back_request_and_approval(self):
        with patch("apps.medical.audit.MedicalAuditEvent.objects.create", side_effect=DatabaseError), self.assertRaises(MedicalAuditUnavailable):
            self.request()
        self.assertFalse(MedicalCorrectionAccess.objects.exists())
        self.assertFalse(CRMCommandIdempotency.objects.exists())
        item = self.request()[0]
        with patch("apps.medical.audit.MedicalAuditEvent.objects.create", side_effect=DatabaseError), self.assertRaises(MedicalAuditUnavailable):
            self.review(item)
        item.refresh_from_db()
        self.assertEqual((item.state, item.revision), ("pending", 1))

    def test_database_rejects_longer_interval_and_incomplete_active_state(self):
        item = self.request()[0]
        with self.assertRaises(IntegrityError), transaction.atomic():
            MedicalCorrectionAccess.objects.filter(pk=item.pk).update(state="active")
        item = self.review(item)[0]
        with self.assertRaises(IntegrityError), transaction.atomic():
            MedicalCorrectionAccess.objects.filter(pk=item.pk).update(expires_at=item.expires_at + timedelta(seconds=1))

    def test_closed_booking_correction_uses_existing_versioned_writer_and_rechecks_expiry(self):
        fixtures.PrimaryEncounterDraftTests.setUp(self)
        type(self.appointment).objects.filter(pk=self.appointment.pk).update(status="completed")
        item = self.review(self.request()[0])[0]
        kwargs = dict(actor=self.doctor, business_id=self.business.pk, patient_id=self.patient.pk,
            encounter_id=self.encounter_record.pk, expected_revision=1,
            content={"plan": "Corrected synthetic plan", "allergies": "Corrected synthetic allergy",
                     "contraindications": "Corrected synthetic contraindication",
                     "not_applicable": {"procedures": "Synthetic consultation only"}},
            reason="Synthetic correction", idempotency_key="save", correction_access_id=item.pk)
        version, _ = save_primary_encounter_draft(**kwargs)
        self.assertEqual(version.revision, 2)
        from .encounter_content import read_encounter_revision
        self.assertEqual(read_encounter_revision(version)["content"], kwargs["content"])
        self.assertEqual(MedicalAuditEvent.objects.get(action="encounter_draft_saved").correction_access_id, item.pk)
        self.assertTrue(save_primary_encounter_draft(**kwargs)[1])
        with patch("apps.medical.correction_access_context.timezone.now", return_value=item.expires_at):
            with self.assertRaises(PermissionDenied):
                save_primary_encounter_draft(**kwargs)

    def test_target_only_read_requires_approval_and_audit_before_decryption(self):
        fixtures.PrimaryEncounterDraftTests.setUp(self)
        item = self.request()[0]
        self.assertEqual(read_correction_request(actor=self.head, business_id=self.business.pk,
            request_id=item.pk, head=True)["reason"], "Synthetic private request")
        with self.assertRaises(PermissionDenied):
            read_correction_target(actor=self.doctor, business_id=self.business.pk, request_id=item.pk)
        self.review(item)
        result = read_correction_target(actor=self.doctor, business_id=self.business.pk, request_id=item.pk)
        self.assertEqual(result["version_id"], self.first_version.pk)
        self.assertIn("plan", result["content"]["content"])
        with patch("apps.medical.audit.MedicalAuditEvent.objects.create", side_effect=DatabaseError), self.assertRaises(MedicalAuditUnavailable):
            read_correction_target(actor=self.doctor, business_id=self.business.pk, request_id=item.pk)

    def test_valid_roles_in_another_business_cannot_read_review_or_request_this_target(self):
        from django.utils import timezone
        from apps.businesses.models import Business, BusinessCapability, BusinessRole
        from apps.branches.models import Branch
        other = Business.objects.create(owner=self.owner, name="Other synthetic clinic", slug="other-correction",
            business_type="dentistry", profile_key="dentistry", profile_version=2, profile_assigned_at=timezone.now())
        for key in ("medical_records", "clients", "appointments"):
            BusinessCapability.objects.create(business=other, module_key=key, is_enabled=True)
        branch = Branch.objects.create(business=other, name="Other branch")
        role = BusinessRole.objects.create(business=other, name="Other medical role")
        for action in ("view", "update", "manage"):
            RolePermission.objects.create(business_role=role, resource="medical_records", action=action, scope="business")
        for actor, kind in ((self.doctor, "doctor"), (self.head, "head")):
            member = BusinessMember.objects.create(business=other, user=actor, role="admin")
            assignment = MedicalRoleAssignment.objects.create(member=member, business_role=role, kind=kind, granted_by=self.owner)
            assignment.branches.add(branch)
            BranchAccess.objects.create(member=member, all_branches=True)
        item = self.request()[0]
        with self.assertRaises(PermissionDenied):
            self.request(business_id=other.pk)
        with self.assertRaises(PermissionDenied):
            self.review(item, business_id=other.pk)
        with self.assertRaises(PermissionDenied):
            read_correction_request(actor=self.head, business_id=other.pk, request_id=item.pk, head=True)
        item.refresh_from_db()
        self.assertEqual(item.state, "pending")
