"""Single-visit races on real PostgreSQL row locks."""
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

from django.db import connections
from django.test import TransactionTestCase, skipUnlessDBFeature
from rest_framework.test import APIClient

from apps.scheduling.models import Appointment
from apps.scheduling import tests_record_commands as record_tests


@skipUnlessDBFeature("has_select_for_update")
class RecordConcurrencyTests(TransactionTestCase):
    def setUp(self):
        record_tests.RecordCommandTests.setUpTestData.__func__(type(self))
        record_tests.RecordCommandTests.setUp(self)

    def parallel(self, operations):
        barrier = Barrier(len(operations))

        def execute(operation):
            connections.close_all()
            try:
                api = APIClient()
                api.force_authenticate(self.owner)
                barrier.wait(timeout=20)
                response = operation(api)
                return response.status_code, response.data
            finally:
                connections.close_all()

        with ThreadPoolExecutor(max_workers=len(operations)) as pool:
            futures = [pool.submit(execute, op) for op in operations]
            return [future.result(timeout=45) for future in futures]

    def test_last_slot_has_only_one_winner(self):
        results = self.parallel([lambda api: api.post("/api/appointments/create-record/", self.payload, format="json")] * 2)
        self.assertEqual(sorted(code for code, _ in results), [201, 409], results)
        self.assertEqual(Appointment.objects.count(), 1)

    def test_same_key_creates_once_and_can_be_replayed(self):
        def send(api):
            return api.post("/api/appointments/create-record/", self.payload, format="json", HTTP_IDEMPOTENCY_KEY="concurrent-record")
        results = self.parallel([send, send])
        self.assertIn(201, [code for code, _ in results], results)
        self.assertTrue(all(code in (201, 409) for code, _ in results), results)
        self.assertEqual(Appointment.objects.count(), 1)
        replay = send(self.api)
        self.assertEqual(replay.status_code, 201, replay.data)
        self.assertEqual(replay.data["id"], Appointment.objects.get().pk)

    def test_two_actions_on_same_version_do_not_both_apply(self):
        created = self.api.post("/api/appointments/create-record/", self.payload, format="json")
        self.assertEqual(created.status_code, 201, created.data)
        url = f"/api/appointments/{created.data['id']}/"
        version = created.data["updated_at"]
        results = self.parallel([
            lambda api: api.post(url + "confirm/", {"expected_updated_at": version}, format="json"),
            lambda api: api.post(url + "cancel/", {"expected_updated_at": version, "reason": "Changed plan"}, format="json"),
        ])
        self.assertEqual(sorted(code for code, _ in results), [200, 409], results)
