"""Real row locking for authenticated intake; use disposable PostgreSQL."""
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

from django.db import close_old_connections
from django.test import TransactionTestCase, skipUnlessDBFeature
from rest_framework.test import APIClient

from apps.bots.models import BotMessage
from apps.conversations import tests_message_history


@skipUnlessDBFeature("has_select_for_update")
class MessageIntakeConcurrencyTests(TransactionTestCase):
    def test_parallel_intake_preserves_both_messages_and_unread_count(self):
        fixture = tests_message_history.MessageHistoryBoundaryTests()
        fixture.setUpTestData()
        barrier = Barrier(2)

        def receive(text):
            close_old_connections()
            try:
                api = APIClient()
                api.force_authenticate(fixture.actor)
                barrier.wait(timeout=30)
                response = api.post("/api/bot-messages/", {
                    "conversation": fixture.own.pk, "direction": "inbound", "text": text,
                }, format="json")
                return response.status_code, response.data
            finally:
                close_old_connections()

        with ThreadPoolExecutor(max_workers=2) as pool:
            futures = [pool.submit(receive, text) for text in ("First concurrent", "Second concurrent")]
            results = [future.result(timeout=60) for future in futures]
        self.assertEqual([code for code, _ in results], [201, 201], results)
        self.assertNotEqual(results[0][1]["id"], results[1][1]["id"])
        fixture.own.refresh_from_db()
        self.assertEqual(fixture.own.unread_count, 2)
        self.assertEqual(set(BotMessage.objects.filter(conversation=fixture.own, text__endswith="concurrent").values_list("text", flat=True)),
                         {"First concurrent", "Second concurrent"})
