import json
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.db import DatabaseError
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied, ValidationError

from apps.businesses.models import Business, BusinessCapability, BusinessMember, BusinessRole, RolePermission
from apps.core.domain_errors import InvalidTransition, ModuleDisabled
from apps.core.idempotency import CRMCommandConflict
from apps.core.models import CRMCommandIdempotency
from . import tests_template_services as fixtures
from . import tests_patient_services as crypto_fixtures
from .audit import MedicalAuditUnavailable
from .identity_crypto import MedicalDataUnavailable, MedicalKeyUnavailable, decrypt_medical_value, encrypt_medical_value
from .models import MedicalAuditEvent, MedicalDocumentTemplate, MedicalDocumentTemplateRevision, MedicalRoleAssignment, MedicalTemplateReview
from .template_services import save_personal_template_draft
from .template_reviews import submit_personal_template, decide_template_review, read_submitted_template, list_pending_template_reviews


@override_settings(MEDICAL_DATA_KEYS={"test": crypto_fixtures.key(7)}, MEDICAL_DATA_ACTIVE_KEY_ID="test",
                   MEDICAL_IDENTITY_INDEX_KEY=crypto_fixtures.key(8))
class TemplateReviewTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        fixtures.PersonalTemplateServiceTests.setUpTestData.__func__(cls)
        cls.head = get_user_model().objects.create_user(username="template-head", email="template-head@example.test")
        cls.head_member = BusinessMember.objects.create(business=cls.business, user=cls.head)
        cls.head_role = BusinessRole.objects.create(business=cls.business, name="Template reviewer")
        cls.head_assignment = MedicalRoleAssignment.objects.create(member=cls.head_member,
            business_role=cls.head_role, kind="head", granted_by=cls.owner)
        for action in ("approve", "view"):
            RolePermission.objects.create(business_role=cls.head_role, resource="medical_documents",
                action=action, scope="business", is_allowed=True)

    def setUp(self):
        self.version, _ = save_personal_template_draft(actor=self.doctor, business_id=self.business.pk,
            title="Synthetic private template", text="Synthetic text", reason="", idempotency_key="initial")

    def submit(self, **overrides):
        return submit_personal_template(**(dict(actor=self.doctor, business_id=self.business.pk,
            version_id=self.version.pk, idempotency_key="submit") | overrides))

    def decide(self, **overrides):
        return decide_template_review(**(dict(actor=self.head, business_id=self.business.pk,
            version_id=self.version.pk, decision="approved", reason="Synthetic private decision", idempotency_key="approve") | overrides))

    def read(self, **overrides):
        return read_submitted_template(**(dict(actor=self.head, business_id=self.business.pk,
            version_id=self.version.pk) | overrides))

    def next_version(self):
        return save_personal_template_draft(actor=self.doctor, business_id=self.business.pk,
            template_id=self.version.template_id, expected_revision=1, title="Changed", text="New text",
            idempotency_key="second")[0]

    def test_submit_approve_and_private_receipt_preserve_exact_version(self):
        before = self.version.snapshot_encrypted
        review, replayed = self.submit()
        self.assertFalse(replayed)
        self.assertEqual(review.state, "pending")
        self.assertEqual(self.read()["template"]["text"], "Synthetic text")
        decided, replayed = self.decide()
        self.assertFalse(replayed)
        self.assertEqual(decided.pk, review.pk)
        self.assertEqual(decided.state, "approved")
        self.assertEqual(decided.decided_by_id, self.head.pk)
        self.assertNotIn("Synthetic", decided.decision_encrypted)
        for actor in (self.head, self.doctor):
            result = self.read(actor=actor)
            self.assertEqual(result["decision_reason"], "Synthetic private decision")
            self.assertEqual(result["version_id"], self.version.pk)
        self.version.refresh_from_db()
        self.assertEqual(self.version.snapshot_encrypted, before)
        event = MedicalAuditEvent.objects.get(action="template_approved")
        self.assertEqual(event.template_version_id, self.version.pk)
        self.assertIsNone(event.patient_id)
        for command in CRMCommandIdempotency.objects.all():
            self.assertNotIn("Synthetic", str(command.__dict__))

    def test_head_cannot_read_or_approve_unsubmitted_private_version(self):
        for operation in (self.read, self.decide):
            with self.assertRaises(PermissionDenied):
                operation()
        self.assertFalse(MedicalTemplateReview.objects.exists())

    def test_only_owner_can_submit_personal_version(self):
        for actor in (self.head, self.owner):
            with self.assertRaises(PermissionDenied):
                self.submit(actor=actor)
        self.assertFalse(MedicalTemplateReview.objects.exists())

    def test_reject_requires_reason_and_preserves_it(self):
        self.submit()
        with self.assertRaises(ValidationError):
            self.decide(decision="rejected", reason="  ")
        self.decide(decision="rejected", reason="Synthetic revision required")
        self.assertEqual(self.read(actor=self.doctor)["decision_reason"], "Synthetic revision required")
        self.assertEqual(self.read()["state"], "rejected")
        with self.assertRaises(InvalidTransition):
            self.decide(idempotency_key="another")

    def test_replays_do_not_duplicate_reviews_or_decisions(self):
        submitted, _ = self.submit()
        self.assertEqual(self.submit()[0].pk, submitted.pk)
        self.assertTrue(self.submit()[1])
        self.decide()
        self.assertTrue(self.decide()[1])
        with self.assertRaises(CRMCommandConflict):
            self.decide(reason="Changed private decision")
        self.assertEqual(MedicalTemplateReview.objects.count(), 1)
        self.assertEqual(MedicalAuditEvent.objects.filter(action="template_submitted").count(), 1)
        self.assertEqual(MedicalAuditEvent.objects.filter(action="template_approved").count(), 1)

    def test_new_draft_does_not_inherit_approval_and_old_receipt_stays_readable(self):
        self.submit()
        self.decide()
        second = self.next_version()
        self.assertFalse(MedicalTemplateReview.objects.filter(version=second).exists())
        self.assertEqual(self.read()["template"]["text"], "Synthetic text")
        self.assertTrue(self.decide()[1])
        with self.assertRaises(PermissionDenied):
            self.read(version_id=second.pk)

    def test_stale_version_cannot_be_submitted_or_decided(self):
        self.submit()
        second = self.next_version()
        with self.assertRaises(InvalidTransition):
            self.decide()
        with self.assertRaises(InvalidTransition):
            self.submit(idempotency_key="stale-submit")
        self.submit(version_id=second.pk, idempotency_key="submit-second")
        self.decide(version_id=second.pk, idempotency_key="approve-second")
        self.assertEqual(self.read(version_id=second.pk)["state"], "approved")

    def test_doctor_cannot_approve_even_with_forged_permission(self):
        self.submit()
        RolePermission.objects.create(business_role=self.role, resource="medical_documents",
            action="approve", scope="business", is_allowed=True)
        for actor in (self.doctor, self.owner):
            with self.assertRaises(PermissionDenied):
                self.decide(actor=actor)
        self.assertEqual(MedicalTemplateReview.objects.get().state, "pending")

    def test_head_needs_current_explicit_business_scope(self):
        self.submit()
        for action in ("view", "approve"):
            permission = RolePermission.objects.get(business_role=self.head_role, resource="medical_documents", action=action)
            for scope in ("own", "team"):
                permission.scope = scope
                permission.save(update_fields=["scope"])
                with self.assertRaises(PermissionDenied):
                    self.decide()
            permission.scope = "business"
            permission.save(update_fields=["scope"])
        self.head_assignment.revoked_at = timezone.now()
        self.head_assignment.save(update_fields=["revoked_at"])
        with self.assertRaises(PermissionDenied):
            self.decide()

    def test_replay_rechecks_role_membership_and_module(self):
        self.submit()
        self.decide()
        self.head_member.is_active = False
        self.head_member.save(update_fields=["is_active"])
        with self.assertRaises(PermissionDenied):
            self.decide()
        self.head_member.is_active = True
        self.head_member.save(update_fields=["is_active"])
        BusinessCapability.objects.filter(business=self.business, module_key="medical_records").update(is_enabled=False)
        with self.assertRaises(ModuleDisabled):
            self.decide()

    def test_foreign_business_version_is_denied(self):
        other = Business.objects.create(owner=self.owner, name="Other", slug="review-other")
        self.submit()
        for operation in (self.submit, self.decide, self.read):
            with self.assertRaises(PermissionDenied):
                operation(business_id=other.pk)
        foreign = MedicalDocumentTemplate.objects.create(business=other, code="foreign", revision=1)
        foreign_version = MedicalDocumentTemplateRevision.objects.create(template=foreign, revision=1,
            author=self.doctor, snapshot_encrypted="foreign")
        for operation in (self.submit, self.decide, self.read):
            with self.assertRaises(PermissionDenied):
                operation(version_id=foreign_version.pk)

    def test_audit_failure_rolls_back_submission_and_decision(self):
        with patch("apps.medical.template_audit.MedicalAuditEvent.objects.create", side_effect=DatabaseError):
            with self.assertRaises(MedicalAuditUnavailable):
                self.submit()
        self.assertFalse(MedicalTemplateReview.objects.exists())
        self.submit()
        with patch("apps.medical.template_audit.MedicalAuditEvent.objects.create", side_effect=DatabaseError):
            with self.assertRaises(MedicalAuditUnavailable):
                self.decide()
        self.assertEqual(MedicalTemplateReview.objects.get().state, "pending")
        self.assertFalse(CRMCommandIdempotency.objects.filter(action="medical.template.decide").exists())

    def test_key_failure_and_receipt_tampering_are_fail_closed(self):
        self.submit()
        with override_settings(MEDICAL_DATA_KEYS={}):
            with self.assertRaises(MedicalKeyUnavailable):
                self.decide()
        self.assertEqual(MedicalTemplateReview.objects.get().state, "pending")
        self.decide()
        MedicalTemplateReview.objects.update(decision_encrypted="corrupt")
        with self.assertRaises(MedicalDataUnavailable):
            self.read()

    def test_approval_receipt_detects_even_validly_encrypted_content_replacement(self):
        self.submit()
        self.decide()
        payload = json.loads(decrypt_medical_value(self.version.snapshot_encrypted,
            business_id=self.business.pk, subject_id=self.version.pk, purpose="document_template"))
        payload["content"]["text"] = "Replaced after approval"
        changed = encrypt_medical_value(json.dumps(payload), business_id=self.business.pk,
            subject_id=self.version.pk, purpose="document_template")
        MedicalDocumentTemplateRevision.objects.filter(pk=self.version.pk).update(snapshot_encrypted=changed)
        with self.assertRaises(MedicalDataUnavailable):
            self.read()

    def test_copied_decision_receipt_cannot_approve_another_version(self):
        self.submit()
        review, _ = self.decide()
        second = self.next_version()
        self.submit(version_id=second.pk, idempotency_key="submit-second")
        other, _ = self.decide(version_id=second.pk, idempotency_key="approve-second")
        MedicalTemplateReview.objects.filter(pk=other.pk).update(decision_encrypted=review.decision_encrypted)
        with self.assertRaises(MedicalDataUnavailable):
            self.read(version_id=second.pk)

    def test_invalid_inputs_and_pending_state_constraint(self):
        for decision in ({}, [], "invalid"):
            with self.assertRaises(ValidationError):
                self.decide(decision=decision)
        review, _ = self.submit()
        review.state = "approved"
        from django.core.exceptions import ValidationError as ModelValidationError
        with self.assertRaises(ModelValidationError):
            review.full_clean()
        review.state = "pending"
        outsider = get_user_model().objects.create_user(username="review-outsider", email="review-outsider@example.test")
        review.submitted_by = outsider
        with self.assertRaises(ModelValidationError):
            review.full_clean()

    def test_queue_requires_head_and_excludes_unsubmitted_and_stale_versions(self):
        def queue(actor=None, **kwargs):
            return list_pending_template_reviews(actor=actor or self.head, business_id=self.business.pk, **kwargs)
        self.assertEqual(queue()["results"], [])
        self.submit()
        self.assertEqual(queue()["results"][0]["version_id"], self.version.pk)
        for actor in (self.doctor, self.owner):
            with self.assertRaises(PermissionDenied):
                queue(actor)
        self.next_version()
        self.assertEqual(queue()["results"], [])

    def test_queue_pages_audits_and_removes_decided_versions(self):
        first, _ = self.submit()
        second, _ = save_personal_template_draft(actor=self.doctor, business_id=self.business.pk,
            title="Second", text="", idempotency_key="new-template")
        self.submit(version_id=second.pk, idempotency_key="submit-new")
        before = MedicalAuditEvent.objects.filter(action="read").count()
        page = list_pending_template_reviews(actor=self.head, business_id=self.business.pk, limit=1)
        self.assertEqual([row["version_id"] for row in page["results"]], [second.pk])
        self.assertEqual(MedicalAuditEvent.objects.filter(action="read").count(), before + 1)
        page = list_pending_template_reviews(actor=self.head, business_id=self.business.pk,
            before_id=page["next_before_id"], limit=1)
        self.assertEqual(page["results"][0]["review_id"], first.pk)
        self.assertIsNone(page["next_before_id"])
        self.decide()
        page = list_pending_template_reviews(actor=self.head, business_id=self.business.pk)
        self.assertEqual([row["version_id"] for row in page["results"]], [second.pk])

    def test_queue_denial_and_audit_failure_do_not_release_content(self):
        self.submit()
        with patch("apps.medical.template_reviews.write_template_audit", side_effect=MedicalAuditUnavailable):
            with self.assertRaises(MedicalAuditUnavailable):
                list_pending_template_reviews(actor=self.head, business_id=self.business.pk)
        self.head_assignment.revoked_at = timezone.now()
        self.head_assignment.save(update_fields=["revoked_at"])
        with self.assertRaises(PermissionDenied):
            list_pending_template_reviews(actor=self.head, business_id=self.business.pk)
