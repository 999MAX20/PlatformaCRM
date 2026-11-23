from django.test import TestCase, override_settings

from . import tests_document_rule_snapshots as fixtures
from .encounter_completion_requirements import encounter_completion_requirements
from .encounter_content import CLINICAL_FIELDS
from .encounter_services import save_primary_encounter_draft
from .models import MedicalEncounterRevision
from .tests_document_rules import default_rule
from .tests_patient_services import key


@override_settings(MEDICAL_DATA_KEYS={"test": key(7)}, MEDICAL_DATA_ACTIVE_KEY_ID="test",
                   MEDICAL_IDENTITY_INDEX_KEY=key(8))
class EncounterCompletionRequirementsTests(TestCase):
    setUpTestData = classmethod(fixtures.DocumentRuleSnapshotTests.setUpTestData.__func__)
    setUp = fixtures.DocumentRuleSnapshotTests.setUp
    rules = fixtures.DocumentRuleSnapshotTests.rules
    save = fixtures.DocumentRuleSnapshotTests.save

    def readiness(self):
        self.encounter_record.refresh_from_db()
        return encounter_completion_requirements(MedicalEncounterRevision.objects.get(
            encounter=self.encounter_record, revision=self.encounter_record.revision))

    def fill(self, **changes):
        return save_primary_encounter_draft(actor=self.doctor, business_id=self.business.pk,
            patient_id=self.patient.pk, encounter_id=self.encounter_record.pk, expected_revision=1,
            content={field: "Synthetic clinical content" for field in CLINICAL_FIELDS} | changes,
            idempotency_key="complete-clinical-fields")

    def test_missing_sections_reported_and_not_applicable_reason_counts(self):
        self.assertFalse(self.readiness()["ready"])
        self.fill(epicrisis="", not_applicable={"epicrisis": "Synthetic consultation"})
        self.assertTrue(self.readiness()["ready"])

    def test_required_service_document_missing_then_draft_not_ready(self):
        rule = self.rules()
        self.assertEqual(self.readiness()["documents"], [{"kind_id": rule.kind_id,
            "name": "Synthetic consent", "version_id": None, "ready": False, "blocker": "document_missing"}])
        document = self.save()
        self.assertEqual(self.readiness()["documents"][0]["version_id"], document.pk)
        self.assertEqual(self.readiness()["documents"][0]["blocker"], "document_not_finalized")

    def test_captured_required_rule_cannot_be_relaxed_by_later_matrix(self):
        rule = self.rules()
        self.save()
        self.rules(kind_id=rule.kind_id, expected_revision=1, idempotency_key="relax",
            content={"name": "New optional matrix", "default": default_rule(), "services": []})
        self.assertEqual(self.readiness()["documents"][0]["blocker"], "document_not_finalized")

    def test_optional_captured_rule_not_replaced_with_later_requirement(self):
        rule = self.rules(content={"name": "Optional", "default": default_rule(), "services": []})
        self.save()
        self.rules(kind_id=rule.kind_id, expected_revision=1, idempotency_key="tighten")
        self.fill()
        self.assertTrue(self.readiness()["ready"])

    def test_before_issue_does_not_block_completion(self):
        self.rules(content={"name": "Issue later", "services": [],
            "default": default_rule(required_at="before_issue", issuable=True)})
        self.fill()
        self.assertTrue(self.readiness()["ready"])
