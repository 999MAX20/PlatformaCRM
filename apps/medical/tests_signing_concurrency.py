from unittest import skipUnless

from django.db import connection
from django.test import TransactionTestCase, override_settings

from .tests_signing_sessions import SigningSessionTests as Fixtures
from .tests_order_concurrency import OrderConcurrencyTests
from .tests_patient_services import key
from .models import MedicalSigningSession, MedicalSigningEvent


@skipUnless(connection.vendor == "postgresql", "Signing races require PostgreSQL row locks")
@override_settings(MEDICAL_DATA_KEYS={"test": key(7)}, MEDICAL_DATA_ACTIVE_KEY_ID="test",
    MEDICAL_IDENTITY_INDEX_KEY=key(8), USE_S3=False, MEDICAL_SYNTHETIC_SIGNING_ENABLED=True, ENVIRONMENT="test")
class SigningConcurrencyTests(TransactionTestCase):
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

    def test_duplicate_start_and_sign_replay_once(self):
        self.assertCountEqual(self.parallel([lambda: self.start()[1], lambda: self.start()[1]]), [False, True])
        self.assertEqual(MedicalSigningSession.objects.count(), 1)
        session = MedicalSigningSession.objects.get()
        self.assertCountEqual(self.parallel([lambda: self.advance(session)[1], lambda: self.advance(session)[1]]), [False, True])
        self.assertEqual(MedicalSigningEvent.objects.filter(action="signed").count(), 1)

    def test_distinct_sign_vs_cancel_has_one_winner(self):
        session, _ = self.start()
        self.assertCountEqual(self.parallel([lambda: self.advance(session)[1],
            lambda: self.advance(session, action="cancel", idempotency_key="cancel")[1]]), [False, "conflict"])
        session.refresh_from_db()
        self.assertEqual(session.revision, 2)
        self.assertEqual(session.events.count(), 2)
