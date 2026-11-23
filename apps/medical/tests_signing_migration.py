from django.db import connection
from django.db.migrations.exceptions import IrreversibleError
from django.db.migrations.executor import MigrationExecutor
from django.test import TransactionTestCase, override_settings
from .tests_signing_sessions import SigningSessionTests as Fixtures
from .tests_order_concurrency import OrderConcurrencyTests
from .tests_patient_services import key
from .models import MedicalSigningSession


@override_settings(MEDICAL_DATA_KEYS={"test": key(7)}, MEDICAL_DATA_ACTIVE_KEY_ID="test",
    MEDICAL_IDENTITY_INDEX_KEY=key(8), USE_S3=False, MEDICAL_SYNTHETIC_SIGNING_ENABLED=True, ENVIRONMENT="test")
class SigningMigrationTests(TransactionTestCase):
    rules = Fixtures.rules
    save = Fixtures.save
    prepare = Fixtures.prepare
    change = Fixtures.change
    confirm = Fixtures.confirm
    render = Fixtures.render
    start = Fixtures.start
    advance = Fixtures.advance
    parallel = OrderConcurrencyTests.parallel

    def setUp(self):
        Fixtures.setUpTestData.__func__(self)
        Fixtures.setUp(self)

    def test_empty_session_roundtrip_preserves_pdf_then_refuses_populated_reverse(self):
        leaves = MigrationExecutor(connection).loader.graph.leaf_nodes()
        self.addCleanup(lambda: MigrationExecutor(connection).migrate(leaves))
        MigrationExecutor(connection).migrate([("medical", "0047_document_signing_rendition")])
        MigrationExecutor(connection).migrate(leaves)
        session, _ = self.start()
        with self.assertRaisesMessage(IrreversibleError, "Signing history exists"):
            MigrationExecutor(connection).migrate([("medical", "0047_document_signing_rendition")])
        self.assertTrue(MedicalSigningSession.objects.filter(pk=session.pk).exists())

    def test_signing_pdf_refuses_lossy_reverse(self):
        with self.assertRaisesMessage(IrreversibleError, "Signing document artifacts exist"):
            MigrationExecutor(connection).migrate([("medical", "0046_document_head_audit")])
        MigrationExecutor(connection).migrate(MigrationExecutor(connection).loader.graph.leaf_nodes())
