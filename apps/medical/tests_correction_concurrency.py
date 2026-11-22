from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from unittest import skipUnless

from django.db import close_old_connections, connection, connections
from django.test import TransactionTestCase, override_settings

from apps.core.domain_errors import InvalidTransition
from . import tests_correction_access as fixtures
from . import tests_patient_services as crypto_fixtures
from .correction_access_services import close_correction_access
from .models import MedicalAuditEvent, MedicalCorrectionAccess


@skipUnless(connection.vendor == "postgresql", "Correction races require PostgreSQL row locks")
@override_settings(MEDICAL_DATA_KEYS={"test": crypto_fixtures.key(7)}, MEDICAL_DATA_ACTIVE_KEY_ID="test",
                   MEDICAL_IDENTITY_INDEX_KEY=crypto_fixtures.key(8))
class CorrectionConcurrencyTests(TransactionTestCase):
    def setUp(self):
        fixtures.CorrectionAccessTests.setUpTestData.__func__(self)

    request = fixtures.CorrectionAccessTests.request
    review = fixtures.CorrectionAccessTests.review

    def parallel(self, commands):
        barrier = Barrier(len(commands))

        def execute(command):
            close_old_connections()
            try:
                barrier.wait(timeout=10)
                try:
                    return command()
                except InvalidTransition:
                    return "conflict"
            finally:
                connections.close_all()

        with ThreadPoolExecutor(max_workers=len(commands)) as executor:
            futures = [executor.submit(execute, command) for command in commands]
            return [future.result(timeout=30) for future in futures]

    def test_duplicate_request_replays_once_and_competing_new_request_conflicts(self):
        self.assertCountEqual(self.parallel([lambda: self.request()[1], lambda: self.request()[1]]), [False, True])
        self.assertEqual(MedicalCorrectionAccess.objects.count(), 1)
        self.assertEqual(MedicalAuditEvent.objects.filter(action="correction_access_requested").count(), 1)
        self.assertEqual(self.parallel([lambda: self.request(idempotency_key="other")[1]]), ["conflict"])

    def test_approve_and_reject_cannot_both_win(self):
        item = self.request()[0]
        self.assertCountEqual(self.parallel([
            lambda: self.review(item, decision="approve", idempotency_key="approve")[1],
            lambda: self.review(item, decision="reject", idempotency_key="reject")[1],
        ]), [False, "conflict"])
        self.assertEqual(MedicalAuditEvent.objects.filter(action__in=["correction_access_approved", "correction_access_rejected"]).count(), 1)

    def test_completion_and_revocation_cannot_both_win(self):
        item = self.review(self.request()[0])[0]

        def close(actor, decision):
            return close_correction_access(actor=actor, business_id=self.business.pk, request_id=item.pk,
                expected_revision=2, decision=decision, reason="Synthetic race", idempotency_key=decision)[1]

        self.assertCountEqual(self.parallel([lambda: close(self.doctor, "complete"), lambda: close(self.head, "revoke")]), [False, "conflict"])
        item.refresh_from_db()
        self.assertEqual(item.revision, 3)
