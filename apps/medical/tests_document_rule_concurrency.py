from unittest import skipUnless

from django.db import connection
from django.test import TransactionTestCase, override_settings

from . import tests_document_rules as fixtures
from . import tests_document_rule_snapshots as snapshot_fixtures
from . import tests_order_concurrency as concurrency
from .document_content import read_document_revision
from .models import MedicalAuditEvent, MedicalDocumentKind, MedicalDocumentRuleRevision
from .tests_document_rules import default_rule
from .tests_patient_services import key


@skipUnless(connection.vendor == "postgresql", "Document rule races require PostgreSQL row locks")
@override_settings(MEDICAL_DATA_KEYS={"test": key(7)}, MEDICAL_DATA_ACTIVE_KEY_ID="test",
                   MEDICAL_IDENTITY_INDEX_KEY=key(8))
class DocumentRuleConcurrencyTests(TransactionTestCase):
    def setUp(self):
        fixtures.DocumentRuleTests.setUpTestData.__func__(self)

    save = fixtures.DocumentRuleTests.save
    parallel = concurrency.OrderConcurrencyTests.parallel

    def test_same_command_creates_one_kind_and_one_version(self):
        self.assertCountEqual(self.parallel([lambda: self.save()[1], lambda: self.save()[1]]), [False, True])
        self.assertEqual(MedicalDocumentKind.objects.count(), 1)
        self.assertEqual(MedicalDocumentRuleRevision.objects.count(), 1)
        self.assertEqual(MedicalAuditEvent.objects.filter(action="document_rules_saved").count(), 1)

    def test_two_kinds_cannot_claim_the_same_template(self):
        self.assertCountEqual(self.parallel([lambda: self.save(idempotency_key="kind-one")[1],
            lambda: self.save(idempotency_key="kind-two")[1]]), [False, "conflict"])
        self.assertEqual(MedicalDocumentKind.objects.count(), 1)
        self.assertEqual(MedicalDocumentRuleRevision.objects.count(), 1)
        self.template.refresh_from_db()
        self.assertEqual(self.template.document_kind_id, MedicalDocumentKind.objects.get().pk)


@skipUnless(connection.vendor == "postgresql", "Rule capture races require PostgreSQL row locks")
@override_settings(MEDICAL_DATA_KEYS={"test": key(7)}, MEDICAL_DATA_ACTIVE_KEY_ID="test",
                   MEDICAL_IDENTITY_INDEX_KEY=key(8))
class DocumentRuleCaptureConcurrencyTests(TransactionTestCase):
    def setUp(self):
        snapshot_fixtures.DocumentRuleSnapshotTests.setUpTestData.__func__(self)
        snapshot_fixtures.DocumentRuleSnapshotTests.setUp(self)

    rules = snapshot_fixtures.DocumentRuleSnapshotTests.rules
    save = snapshot_fixtures.DocumentRuleSnapshotTests.save
    parallel = concurrency.OrderConcurrencyTests.parallel

    def test_rule_change_and_document_capture_keep_one_complete_version(self):
        first = self.rules()
        result = self.parallel([lambda: self.save().pk,
            lambda: self.rules(kind_id=first.kind_id, expected_revision=1, idempotency_key="changed",
                content={"name": "Changed rules", "default": default_rule(), "services": []}).pk])
        from .models import MedicalDocumentRevision
        captured = read_document_revision(MedicalDocumentRevision.objects.get(pk=result[0]))["document_rules"]
        self.assertIn(captured["revision"], (1, 2))
        self.assertEqual(captured["docx_allowed"], captured["revision"] == 1)
        self.assertEqual(captured["name"], "Synthetic consent" if captured["revision"] == 1 else "Changed rules")
