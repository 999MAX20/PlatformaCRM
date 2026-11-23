from unittest import skipUnless

from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.db.migrations.exceptions import IrreversibleError
from django.test import TransactionTestCase, override_settings

from .tests_document_issuance import DocumentIssuanceTests as fixtures
from .tests_order_concurrency import OrderConcurrencyTests
from .tests_patient_services import key
from .models import MedicalDocumentGrant, MedicalDocumentGrantEvent


class IssuanceFixture:
    rules, save, prepare = fixtures.rules, fixtures.save, fixtures.prepare
    change, confirm, render = fixtures.change, fixtures.confirm, fixtures.render
    finalize, create, activate, login = fixtures.finalize, fixtures.create, fixtures.activate, fixtures.login

    def setUp(self):
        fixtures.setUpTestData.__func__(self)
        fixtures.setUp(self)
        self.finalize()


@override_settings(MEDICAL_DATA_KEYS={"test": key(7)}, MEDICAL_DATA_ACTIVE_KEY_ID="test",
    MEDICAL_IDENTITY_INDEX_KEY=key(8), USE_S3=False, MEDICAL_SYNTHETIC_SIGNING_ENABLED=True,
    MEDICAL_SYNTHETIC_ISSUANCE_ENABLED=True, ENVIRONMENT="test")
@skipUnless(connection.vendor == "postgresql", "Issuance races require PostgreSQL row locks")
class IssuanceConcurrencyTests(IssuanceFixture, TransactionTestCase):
    parallel = OrderConcurrencyTests.parallel

    def test_duplicate_creation_reveals_one_secret_and_one_grant(self):
        results = self.parallel([lambda: self.create(), lambda: self.create()])
        self.assertCountEqual([result[2] for result in results], [False, True])
        self.assertEqual(sum(result[1] is not None for result in results), 1)
        self.assertEqual(MedicalDocumentGrant.objects.count(), 1)

    def test_duplicate_activation_does_not_extend_deadline(self):
        grant, _, _ = self.create()
        results = self.parallel([lambda: self.activate(grant), lambda: self.activate(grant)])
        self.assertCountEqual([result[1] for result in results], [False, True])
        self.assertEqual(results[0][0].expires_at, results[1][0].expires_at)
        self.assertEqual(MedicalDocumentGrantEvent.objects.filter(action="activated").count(), 1)

    def test_activation_and_revocation_cannot_both_commit_same_revision(self):
        grant, _, _ = self.create()
        results = self.parallel([lambda: self.activate(grant)[1], lambda: self.activate(grant,
            action="revoke", reason="Withdraw", idempotency_key="revoke")[1]])
        self.assertCountEqual(results, [False, "conflict"])
        grant.refresh_from_db(); self.assertEqual(grant.revision, 2)


@override_settings(MEDICAL_DATA_KEYS={"test": key(7)}, MEDICAL_DATA_ACTIVE_KEY_ID="test",
    MEDICAL_IDENTITY_INDEX_KEY=key(8), USE_S3=False, MEDICAL_SYNTHETIC_SIGNING_ENABLED=True,
    MEDICAL_SYNTHETIC_ISSUANCE_ENABLED=True, ENVIRONMENT="test")
class IssuanceMigrationTests(IssuanceFixture, TransactionTestCase):
    def test_empty_roundtrip_and_populated_history_guard(self):
        leaves = MigrationExecutor(connection).loader.graph.leaf_nodes()
        self.addCleanup(lambda: MigrationExecutor(connection).migrate(leaves))
        MigrationExecutor(connection).migrate([("medical", "0052_document_correction_lineage")])
        MigrationExecutor(connection).migrate(leaves)
        grant, _, _ = self.create()
        proof = grant.evidence_encrypted
        with self.assertRaisesMessage(IrreversibleError, "Document issuance history exists"):
            MigrationExecutor(connection).migrate([("medical", "0052_document_correction_lineage")])
        self.assertEqual(MedicalDocumentGrant.objects.get().evidence_encrypted, proof)
