from django.test import TestCase, override_settings

from . import tests_document_finalization as fixtures
from .encounter_completion_requirements import encounter_completion_requirements
from .encounter_content import CLINICAL_FIELDS
from .encounter_services import save_primary_encounter_draft
from .models import MedicalEncounterRevision, MedicalDocumentFinalization
from .identity_crypto import MedicalDataUnavailable
from .tests_document_rules import default_rule
from .tests_patient_services import key


@override_settings(MEDICAL_DATA_KEYS={"test": key(7)}, MEDICAL_DATA_ACTIVE_KEY_ID="test",
    MEDICAL_IDENTITY_INDEX_KEY=key(8), USE_S3=False, MEDICAL_SYNTHETIC_SIGNING_ENABLED=True, ENVIRONMENT="test")
class CompletionDocumentTests(TestCase):
    setUpTestData = classmethod(fixtures.DocumentFinalizationTests.setUpTestData.__func__)
    rules = fixtures.DocumentFinalizationTests.rules
    save = fixtures.DocumentFinalizationTests.save
    change = fixtures.DocumentFinalizationTests.change
    confirm = fixtures.DocumentFinalizationTests.confirm
    render = fixtures.DocumentFinalizationTests.render
    start = fixtures.DocumentFinalizationTests.start
    advance = fixtures.DocumentFinalizationTests.advance
    finalize = fixtures.DocumentFinalizationTests.finalize
    sign_all = fixtures.DocumentFinalizationTests.sign_all

    def prepare(self):
        self.rule_version = self.rules(content={"name": "Synthetic completion consent", "services": [],
            "default": default_rule(required_at="before_completion", reviewers=["primary_clinician", "medical_head"],
                signers=["primary_clinician", "medical_head", "patient_or_representative"])})
        self.version = self.save()
        self.change()

    def setUp(self):
        fixtures.DocumentFinalizationTests.setUp(self)
        self.clinical, _ = save_primary_encounter_draft(actor=self.doctor, business_id=self.business.pk,
            patient_id=self.patient.pk, encounter_id=self.encounter_record.pk, expected_revision=1,
            content={field: "Synthetic clinical content" for field in CLINICAL_FIELDS}, idempotency_key="fill")

    def readiness(self):
        return encounter_completion_requirements(MedicalEncounterRevision.objects.get(pk=self.clinical.pk))

    def test_required_signed_document_blocks_until_exact_finalization(self):
        self.assertFalse(self.readiness()["ready"])
        self.sign_all()
        self.assertFalse(self.readiness()["ready"])
        self.finalize()
        self.assertTrue(self.readiness()["ready"])

    def test_corrupt_finalization_never_allows_completion(self):
        self.sign_all()
        item, _ = self.finalize()
        MedicalDocumentFinalization.objects.filter(pk=item.pk).update(evidence_encrypted="invalid")
        with self.assertRaises(MedicalDataUnavailable):
            self.readiness()

    def test_quarantined_final_pdf_is_not_a_ready_required_document(self):
        from apps.core.models import FileAttachment
        self.sign_all()
        self.finalize()
        FileAttachment.objects.filter(pk=self.artifact.attachment_id).update(scan_status="infected")
        self.assertFalse(self.readiness()["ready"])
