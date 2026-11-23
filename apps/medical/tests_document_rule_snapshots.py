import json

from django.test import TestCase, override_settings

from . import tests_document_template_source as fixtures
from .document_content import append_document_text_correction, read_document_revision
from .document_rule_services import save_document_rules
from .identity_crypto import decrypt_medical_value, encrypt_medical_value
from .tests_document_rules import default_rule
from .tests_patient_services import key


@override_settings(MEDICAL_DATA_KEYS={"test": key(7)}, MEDICAL_DATA_ACTIVE_KEY_ID="test",
                   MEDICAL_IDENTITY_INDEX_KEY=key(8))
class DocumentRuleSnapshotTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        fixtures.DocumentTemplateSourceTests.setUpTestData.__func__(cls)

    def setUp(self):
        fixtures.DocumentTemplateSourceTests.setUp(self)
        fixtures.DocumentTemplateSourceTests.approve(self)

    def rules(self, **changes):
        return save_document_rules(**(dict(actor=self.head, business_id=self.business.pk,
            content={"name": "Synthetic consent", "docx_allowed": True, "default": default_rule(), "services": [
                {"service_id": self.appointment.service_id, "rule": default_rule(required_at="before_completion",
                    required_fields=["patient.full_name"], signers=["primary_clinician"], issuable=True)}]},
            template_ids=[self.template.template_id], reason="Synthetic configuration", idempotency_key="rules") | changes))[0]

    def save(self, **changes):
        return fixtures.DocumentTemplateSourceTests.save(self, **changes)[0]

    def test_new_document_captures_service_rule_and_edit_keeps_it_after_rule_change(self):
        initial = self.rules()
        document = self.save()
        snapshot = read_document_revision(document)["document_rules"]
        self.assertEqual(snapshot["version_id"], initial.pk)
        self.assertEqual(snapshot["rule"]["required_at"], "before_completion")
        self.assertEqual(snapshot["service_id"], self.appointment.service_id)
        self.assertTrue(snapshot["docx_allowed"])
        changed = self.rules(kind_id=initial.kind_id, expected_revision=1, idempotency_key="rules-changed",
            content={"name": "Changed rules", "default": default_rule(), "services": []})
        edited = self.save(document_id=document.document_id, expected_document_revision=1,
            document_text="Changed synthetic text", reason="Synthetic correction", idempotency_key="edit")
        self.assertEqual(read_document_revision(edited)["document_rules"], snapshot)
        self.assertEqual(read_document_revision(document)["document_rules"], snapshot)
        new = self.save(idempotency_key="new-document")
        new_snapshot = read_document_revision(new)["document_rules"]
        self.assertEqual(new_snapshot["version_id"], changed.pk)
        self.assertEqual(new_snapshot["rule"], default_rule())
        self.assertFalse(new_snapshot["docx_allowed"])

    def test_unconfigured_and_legacy_documents_do_not_gain_new_permissions(self):
        document = self.save()
        self.assertIsNone(read_document_revision(document)["document_rules"])
        payload = json.loads(decrypt_medical_value(document.snapshot_encrypted, business_id=self.business.pk,
            subject_id=document.pk, purpose="document_snapshot"))
        payload["schema"] = 4
        del payload["snapshot"]["document_rules"]
        document.snapshot_encrypted = encrypt_medical_value(json.dumps(payload), business_id=self.business.pk,
            subject_id=document.pk, purpose="document_snapshot")
        document.save(update_fields=["snapshot_encrypted"])
        before = read_document_revision(document)
        self.assertNotIn("document_rules", before)
        self.rules()
        edited = self.save(document_id=document.document_id, expected_document_revision=1,
            document_text="Legacy edit", reason="Synthetic edit", idempotency_key="legacy-edit")
        self.assertIsNone(read_document_revision(edited)["document_rules"])
        self.assertEqual(read_document_revision(document), before)

    def test_text_correction_preserves_rules_and_unbinding_affects_only_new_documents(self):
        rules = self.rules()
        document = self.save()
        snapshot = read_document_revision(document)["document_rules"]
        document.document.refresh_from_db()
        corrected = append_document_text_correction(document=document.document, author=self.doctor,
            document_text="Narrow synthetic correction", reason="Synthetic correction")
        self.assertEqual(read_document_revision(corrected)["document_rules"], snapshot)
        self.rules(kind_id=rules.kind_id, expected_revision=1, template_ids=[], idempotency_key="unbind")
        self.assertEqual(read_document_revision(document)["document_rules"], snapshot)
        self.assertIsNone(read_document_revision(self.save(idempotency_key="unbound-new"))["document_rules"])
