from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from unittest import skipUnless

from django.contrib.auth import get_user_model
from django.db import close_old_connections, connection, connections
from django.test import TransactionTestCase

from apps.businesses.models import Business
from apps.core.domain_errors import IdempotencyConflict
from apps.support.messages import append_message, mark_read
from apps.support.models import ReadState, SupportCase
from apps.support.services import SupportVersionConflict, assign_case, create_case


@skipUnless(connection.vendor == "postgresql", "Real row locking requires the isolated PostgreSQL gate.")
class SupportConcurrencyTests(TransactionTestCase):
    def setUp(self):
        self.owner = get_user_model().objects.create(username="support-pg-owner", email="support-pg-owner@example.com", role="business_owner")
        self.staff = get_user_model().objects.create(username="support-pg-staff", email="support-pg-staff@example.com", role="platform_manager")
        self.business = Business.objects.create(owner=self.owner, name="Support PG", slug="support-pg")
        result = create_case(actor=self.owner, business_id=self.business.pk, subject="Concurrent", text="Initial message", idempotency_key="initial")
        self.case_id = result.data["case_id"]

    def race(self, action):
        barrier = Barrier(2)

        def run(index):
            close_old_connections()
            try:
                barrier.wait(timeout=10)
                return action(index)
            finally:
                connections.close_all()

        with ThreadPoolExecutor(max_workers=2) as workers:
            futures = [workers.submit(run, index) for index in range(2)]
            return [future.result(timeout=30) for future in futures]

    def test_competing_assignments_do_not_overwrite_the_winner(self):
        def assign(index):
            try:
                assign_case(actor=self.staff, case_id=self.case_id, assignee_id=self.staff.pk if index else None, version=1)
                return "success"
            except SupportVersionConflict:
                return "conflict"

        self.assertCountEqual(self.race(assign), ["success", "conflict"])
        case = SupportCase.objects.get(pk=self.case_id)
        self.assertEqual(case.version, 2)
        self.assertEqual(case.events.filter(kind="assigned").count(), 1)

    def test_concurrent_duplicate_message_then_retry_creates_one_message(self):
        kwargs = dict(actor=self.staff, case_id=self.case_id, text="Only once", idempotency_key="duplicate", platform=True)

        def append(_):
            try:
                return append_message(**kwargs).data["message_id"]
            except IdempotencyConflict:
                return "processing"

        results = self.race(append)
        final = append_message(**kwargs)
        self.assertIn(final.data["message_id"], results)
        self.assertEqual(SupportCase.objects.get(pk=self.case_id).public_messages.filter(text="Only once").count(), 1)

    def test_independent_messages_and_out_of_order_reads_are_not_lost(self):
        def append(index):
            return append_message(actor=self.staff, case_id=self.case_id, text=f"Reply {index}", idempotency_key=f"reply-{index}", platform=True).data["message_id"]

        ids = self.race(append)
        self.assertEqual(len(set(ids)), 2)
        self.race(lambda index: mark_read(actor=self.owner, case_id=self.case_id, through_id=ids[index]).last_read_message_id)
        self.assertEqual(ReadState.objects.get(user=self.owner).last_read_message_id, max(ids))
        self.assertEqual(SupportCase.objects.get(pk=self.case_id).public_messages.count(), 3)
