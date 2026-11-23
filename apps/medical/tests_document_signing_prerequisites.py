from django.test import TestCase, override_settings

from apps.core.domain_errors import InvalidTransition
from . import tests_document_head_review as fixtures
from .document_signing_prerequisites import document_signing_prerequisites, assert_document_signing_prerequisites
from .tests_document_rules import default_rule
from .tests_patient_services import key


@override_settings(MEDICAL_DATA_KEYS={"test": key(7)}, MEDICAL_DATA_ACTIVE_KEY_ID="test",
                   MEDICAL_IDENTITY_INDEX_KEY=key(8))
class DocumentSigningPrerequisiteTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        fixtures.DocumentHeadReviewTests.setUpTestData.__func__(cls)

    def setUp(self):
        fixtures.DocumentHeadReviewTests.setUp(self)

    rules = fixtures.DocumentHeadReviewTests.rules
    save = fixtures.DocumentHeadReviewTests.save
    prepare = fixtures.DocumentHeadReviewTests.prepare
    change = fixtures.DocumentHeadReviewTests.change
    confirm = fixtures.DocumentHeadReviewTests.confirm

    def read(self):
        self.version.refresh_from_db()
        return document_signing_prerequisites(self.version)

    def primary(self, revision=2, command="primary"):
        self.change(target="reviewed", expected_state_revision=revision, idempotency_key=command)

    def test_both_reviews_required_and_head_does_not_replace_primary(self):
        self.prepare()
        self.assertEqual(self.read()["blockers"], ["primary_review_missing", "head_review_missing"])
        self.confirm()
        self.assertEqual(self.read()["blockers"], ["primary_review_missing"])
        with self.assertRaises(InvalidTransition):
            assert_document_signing_prerequisites(self.version)
        self.primary()
        self.assertTrue(self.read()["ready"])
        self.assertEqual(assert_document_signing_prerequisites(self.version)["blockers"], [])

    def test_return_and_resubmit_do_not_reuse_old_head_confirmation(self):
        self.prepare(); self.confirm(); self.primary()
        old = self.read()["submission_id"]
        self.change(target="draft", expected_state_revision=3, reason="Correction", idempotency_key="return")
        self.assertFalse(self.read()["ready"])
        self.change(expected_state_revision=4, idempotency_key="new-submit")
        self.primary(5, "new-primary")
        value = self.read()
        self.assertNotEqual(value["submission_id"], old)
        self.assertEqual(value["blockers"], ["head_review_missing"])

    def test_captured_order_and_optional_head_ignore_later_rule_changes(self):
        original = self.rules(content={"name": "Synthetic ordered signers", "services": [],
            "default": default_rule(signers=["patient_or_representative", "primary_clinician"])})
        self.version = self.save(); self.change(); self.primary()
        self.rules(kind_id=original.kind_id, expected_revision=1, idempotency_key="later-rule",
            content={"name": "Changed rules", "services": [], "default": default_rule(
                reviewers=["primary_clinician", "medical_head"], signers=["medical_head"])})
        value = self.read()
        self.assertTrue(value["ready"])
        self.assertEqual(value["signers"], ["patient_or_representative", "primary_clinician"])
        self.assertEqual(value["rule_version_id"], original.pk)

    def test_missing_frozen_fields_block_even_after_current_data_is_filled(self):
        self.business.legal_name = ""
        self.business.save(update_fields=["legal_name"])
        self.rules(content={"name": "Required legal name", "services": [],
            "default": default_rule(required_fields=["clinic.legal_name"])})
        self.version = self.save(); self.change(); self.primary()
        self.business.legal_name = "Synthetic later legal name"
        self.business.save(update_fields=["legal_name"])
        value = self.read()
        self.assertFalse(value["ready"])
        self.assertEqual(value["missing_fields"], ["clinic.legal_name"])

    def test_unconfigured_document_and_stale_version_do_not_become_ready(self):
        self.version = self.save(); self.change(); self.primary()
        self.assertEqual(self.read()["blockers"], ["rules_missing"])
        self.change(target="draft", expected_state_revision=3, reason="Correction", idempotency_key="return")
        self.save(document_id=self.version.document_id, expected_document_revision=1,
            document_text="New revision", reason="Correction", idempotency_key="new-version")
        self.assertIn("version_outdated", self.read()["blockers"])

    def test_encounter_completion_does_not_erase_document_reviews(self):
        self.prepare(); self.confirm(); self.primary()
        encounter = self.version.document.encounter
        from django.utils import timezone
        encounter.state = "finalized"
        encounter.ended_at = encounter.finalized_at = timezone.now()
        encounter.finalized_by = self.doctor
        encounter.save(update_fields=["state", "ended_at", "finalized_at", "finalized_by"])
        self.assertTrue(self.read()["ready"])
