from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from unittest import skipUnless

from django.db import close_old_connections, connection, connections
from django.test import TransactionTestCase, override_settings

from apps.core.domain_errors import InvalidTransition
from . import tests_document_review as fixtures
from .models import MedicalAuditEvent, MedicalDocumentReviewTransition
from .tests_patient_services import key


@skipUnless(connection.vendor == "postgresql", "Review/edit races require PostgreSQL row locks")
@override_settings(MEDICAL_DATA_KEYS={"test": key(7)}, MEDICAL_DATA_ACTIVE_KEY_ID="test",
                   MEDICAL_IDENTITY_INDEX_KEY=key(8))
class DocumentReviewConcurrencyTests(TransactionTestCase):
    def setUp(self):
        fixtures.DocumentReviewTests.setUpTestData.__func__(self)
        fixtures.DocumentReviewTests.setUp(self)

    change = fixtures.DocumentReviewTests.change
    append = fixtures.DocumentReviewTests.append

    def parallel(self, commands):
        barrier = Barrier(2)
        def execute(command):
            close_old_connections()
            try:
                barrier.wait(timeout=10)
                try:
                    return command()
                except InvalidTransition:
                    return "stale"
            finally:
                connections.close_all()
        with ThreadPoolExecutor(max_workers=2) as executor:
            return [f.result(timeout=30) for f in [executor.submit(execute, command) for command in commands]]

    def test_duplicate_submission_is_one_event(self):
        results = self.parallel([lambda: self.change()[1], lambda: self.change()[1]])
        self.assertCountEqual(results, [False, True])
        self.assertEqual(MedicalDocumentReviewTransition.objects.count(), 1)
        self.assertEqual(MedicalAuditEvent.objects.filter(action="document_review_submitted").count(), 1)

    def test_edit_and_submission_cannot_both_win(self):
        results = self.parallel([lambda: (self.change(), "submitted")[1], lambda: (self.append(), "edited")[1]])
        self.assertEqual(results.count("stale"), 1)
        self.version.document.refresh_from_db()
        self.assertIn((self.version.document.state, self.version.document.revision),
            [("draft", 2), ("ready_for_review", 1)])

    def test_confirmation_and_return_cannot_both_win(self):
        self.change()
        results = self.parallel([
            lambda: self.change(target="reviewed", expected_state_revision=2, idempotency_key="confirm")[1],
            lambda: self.change(target="draft", expected_state_revision=2, reason="Return", idempotency_key="return")[1],
        ])
        self.assertCountEqual(results, [False, "stale"])
        self.assertEqual(MedicalDocumentReviewTransition.objects.count(), 2)
