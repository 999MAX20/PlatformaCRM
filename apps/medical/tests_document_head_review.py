from unittest.mock import patch

from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied
from rest_framework.test import APIClient

from apps.branches.models import BranchAccess
from apps.businesses.models import Business, RolePermission
from apps.core.domain_errors import InvalidTransition
from . import tests_document_rule_snapshots as fixtures
from .audit import MedicalAuditUnavailable
from .document_head_review import confirm_document_by_head, current_review_submission, read_document_head_review
from .document_review_services import transition_document_review, read_document_review
from .models import MedicalDocumentHeadConfirmation, MedicalRoleAssignment
from .tests_document_rules import default_rule
from .tests_patient_services import key


@override_settings(MEDICAL_DATA_KEYS={"test": key(7)}, MEDICAL_DATA_ACTIVE_KEY_ID="test",
                   MEDICAL_IDENTITY_INDEX_KEY=key(8))
class DocumentHeadReviewTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        fixtures.DocumentRuleSnapshotTests.setUpTestData.__func__(cls)
        cls.head_assignment = MedicalRoleAssignment.objects.get(member__user=cls.head)
        cls.head_assignment.branches.add(cls.first)
        BranchAccess.objects.create(member=cls.head_assignment.member, all_branches=True)
        RolePermission.objects.create(business_role=cls.head_assignment.business_role,
            resource="medical_records", action="view", scope="business", is_allowed=True)

    def setUp(self):
        fixtures.DocumentRuleSnapshotTests.setUp(self)

    rules = fixtures.DocumentRuleSnapshotTests.rules
    save = fixtures.DocumentRuleSnapshotTests.save

    def prepare(self, reviewers=None):
        self.rule_version = self.rules(content={"name": "Synthetic head review", "services": [], "default": default_rule(
            reviewers=reviewers or ["primary_clinician", "medical_head"])})
        self.version = self.save()
        self.change()

    def change(self, **changes):
        return transition_document_review(**(dict(actor=self.doctor, business_id=self.business.pk,
            patient_id=self.patient.pk, version_id=self.version.pk, appointment_id=self.appointment.pk,
            expected_state_revision=1, target="ready_for_review", reason="", idempotency_key="submit") | changes))

    def confirm(self, **changes):
        return confirm_document_by_head(**(dict(actor=self.head, business_id=self.business.pk,
            patient_id=self.patient.pk, version_id=self.version.pk, head_branch_id=self.first.pk,
            expected_state_revision=2, idempotency_key="head") | changes))

    def test_confirmation_is_exact_cycle_and_does_not_replace_primary_review(self):
        self.prepare()
        first, replayed = self.confirm()
        self.assertFalse(replayed)
        self.assertEqual(self.confirm()[0].pk, first.pk)
        self.version.document.refresh_from_db()
        self.assertEqual(self.version.document.state, "ready_for_review")
        self.change(target="reviewed", expected_state_revision=2, idempotency_key="doctor")
        self.version.document.refresh_from_db()
        self.assertEqual(current_review_submission(self.version).pk, first.submission_id)
        self.change(target="draft", expected_state_revision=3, reason="Synthetic correction", idempotency_key="return")
        self.version.document.refresh_from_db()
        self.assertIsNone(current_review_submission(self.version))
        self.assertTrue(MedicalDocumentHeadConfirmation.objects.filter(pk=first.pk).exists())
        history = read_document_review(actor=self.head, business_id=self.business.pk,
            patient_id=self.patient.pk, version_id=self.version.pk, head_branch_id=self.first.pk)
        saved = next(event for event in history["results"] if event["id"] == first.submission_id)
        self.assertEqual(saved["head_confirmation"]["id"], first.pk)
        self.change(expected_state_revision=4, idempotency_key="resubmit")
        second, _ = self.confirm(expected_state_revision=5, idempotency_key="second-head")
        self.assertNotEqual(first.submission_id, second.submission_id)

    def test_confirmation_after_primary_and_duplicate_conflict(self):
        self.prepare()
        self.change(target="reviewed", expected_state_revision=2, idempotency_key="doctor")
        with self.assertRaises(InvalidTransition):
            self.confirm()
        self.confirm(expected_state_revision=3)
        with self.assertRaises(InvalidTransition):
            self.confirm(expected_state_revision=3, idempotency_key="duplicate")

    def test_saved_rules_required_and_current_matrix_cannot_grant_review(self):
        self.prepare(reviewers=["primary_clinician"])
        self.rules(kind_id=self.rule_version.kind_id, expected_revision=1, idempotency_key="new-rules",
            content={"name": "Later rule", "services": [], "default": default_rule(
                reviewers=["primary_clinician", "medical_head"])})
        with self.assertRaises(InvalidTransition):
            self.confirm()

    def test_old_version_and_closed_cycle_cannot_gain_confirmation(self):
        self.prepare()
        self.change(target="draft", expected_state_revision=2, reason="Synthetic correction", idempotency_key="return")
        with self.assertRaises(InvalidTransition):
            self.confirm(expected_state_revision=3)
        self.save(document_id=self.version.document_id, expected_document_revision=1,
            document_text="New exact version", reason="Synthetic correction", idempotency_key="new-version")
        with self.assertRaises(InvalidTransition):
            self.confirm(expected_state_revision=3)

    def test_http_private_strict_confirm_read_and_withdrawal(self):
        self.prepare()
        api = APIClient(); api.force_authenticate(self.head)
        path = f"/api/medical/documents/versions/{self.version.pk}/"
        scope = dict(business_id=self.business.pk, patient_id=self.patient.pk, head_branch_id=self.first.pk)
        response = api.get(path + "head-review/", scope)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data["can_confirm"])
        self.assertEqual(response["Cache-Control"], "no-store, private")
        self.assertEqual(api.post(path + "head-confirm/", scope | {"expected_state_revision": 2, "signed": True},
            format="json", HTTP_IDEMPOTENCY_KEY="http").status_code, 400)
        response = api.post(path + "head-confirm/", scope | {"expected_state_revision": 2},
            format="json", HTTP_IDEMPOTENCY_KEY="http")
        self.assertEqual(response.status_code, 200)
        self.assertFalse(api.get(path + "head-review/", scope).data["can_confirm"])
        self.assertEqual(api.get(path + "head-review/", scope).data["confirmation"]["id"], response.data["id"])
        self.change(target="draft", expected_state_revision=2, reason="Synthetic return", idempotency_key="return")
        self.assertIsNone(api.get(path + "head-review/", scope).data["confirmation"])
        api.force_authenticate(self.owner)
        self.assertEqual(api.get(path + "head-review/", scope).status_code, 403)

    def test_read_audit_failure_releases_no_confirmation(self):
        self.prepare()
        with patch("apps.medical.document_head_review.write_patient_audit", side_effect=MedicalAuditUnavailable):
            with self.assertRaises(MedicalAuditUnavailable):
                read_document_head_review(actor=self.head, business_id=self.business.pk, patient_id=self.patient.pk,
                    version_id=self.version.pk, head_branch_id=self.first.pk)

    def test_role_branch_tenant_denial_and_revoked_replay(self):
        self.prepare()
        foreign = Business.objects.create(owner=self.owner, name="Synthetic other", slug="head-review-other")
        for changes in ({"actor": self.owner}, {"actor": self.doctor}, {"head_branch_id": self.second.pk},
                        {"business_id": foreign.pk}):
            with self.assertRaises(PermissionDenied):
                self.confirm(**changes)
        self.confirm()
        self.head_assignment.revoked_at = timezone.now()
        self.head_assignment.save(update_fields=["revoked_at"])
        with self.assertRaises(PermissionDenied):
            self.confirm()

    def test_audit_failure_rolls_back_and_retry_succeeds(self):
        self.prepare()
        with patch("apps.medical.document_head_review.write_patient_audit", side_effect=MedicalAuditUnavailable):
            with self.assertRaises(MedicalAuditUnavailable):
                self.confirm()
        self.assertFalse(MedicalDocumentHeadConfirmation.objects.exists())
        self.assertFalse(self.confirm()[1])

    def test_approve_permission_revocation_blocks_replay(self):
        self.prepare()
        self.confirm()
        RolePermission.objects.filter(business_role=self.head_assignment.business_role,
            resource="medical_documents", action="approve").update(is_allowed=False)
        with self.assertRaises(PermissionDenied):
            self.confirm()
