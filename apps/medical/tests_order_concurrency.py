from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from unittest import skipUnless

from django.db import close_old_connections, connection, connections
from django.test import TransactionTestCase, override_settings

from apps.core.domain_errors import InvalidTransition
from . import tests_order_services as fixtures
from . import tests_patient_services as crypto_fixtures
from .models import MedicalAuditEvent, MedicalOrderRevision


@skipUnless(connection.vendor == "postgresql", "Order races require PostgreSQL row locks")
@override_settings(MEDICAL_DATA_KEYS={"test": crypto_fixtures.key(7)}, MEDICAL_DATA_ACTIVE_KEY_ID="test",
                   MEDICAL_IDENTITY_INDEX_KEY=crypto_fixtures.key(8))
class OrderConcurrencyTests(TransactionTestCase):
    def setUp(self):
        fixtures.OrderServiceTests.setUpTestData.__func__(self)
        fixtures.OrderServiceTests.setUp(self)

    save = fixtures.OrderServiceTests.save

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

    def test_duplicate_create_replays_once(self):
        self.assertCountEqual(self.parallel([lambda: self.save()[1], lambda: self.save()[1]]), [False, True])
        self.assertEqual(MedicalOrderRevision.objects.count(), 1)
        self.assertEqual(MedicalAuditEvent.objects.filter(action="order_draft_created").count(), 1)

    def test_two_updates_cannot_overwrite_one_version(self):
        first, _ = self.save()
        self.assertCountEqual(self.parallel([
            lambda: self.save(order_id=first.order_id, expected_order_revision=1, idempotency_key="first")[1],
            lambda: self.save(order_id=first.order_id, expected_order_revision=1, idempotency_key="second")[1],
        ]), [False, "conflict"])
        self.assertEqual(MedicalOrderRevision.objects.count(), 2)
        self.assertEqual(MedicalAuditEvent.objects.filter(action="order_draft_saved").count(), 1)
