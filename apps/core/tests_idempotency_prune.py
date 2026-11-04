from concurrent.futures import ThreadPoolExecutor
from threading import Event
from unittest.mock import patch

from django.db import connections
from django.db.models.query import QuerySet
from django.test import TestCase, TransactionTestCase, skipUnlessDBFeature
from django.utils import timezone

from apps.accounts.models import User
from apps.businesses.models import Business
from apps.core.idempotency import (begin_crm_command, canonical_request_hash,
    CRMCommandResult, prune_expired_crm_commands, run_idempotent_crm_command)
from apps.core.models import CRMCommandIdempotency
from apps.tasks.models import Task


class PruneFixture:
    def setUp(self):
        self.actor = User.objects.create_user(username="prune-owner", email="prune@example.test")
        self.business = Business.objects.create(owner=self.actor, name="Prune", slug="prune")
        self.now = timezone.now()
        self.command = dict(business=self.business, actor=self.actor, action="prune.test",
                            idempotency_key="renewed", payload={"value": 1})
        self.record = self.receipt("renewed", self.now - timezone.timedelta(seconds=1))

    def receipt(self, key, expiry):
        return CRMCommandIdempotency.objects.create(business=self.business, actor=self.actor,
            action="prune.test", idempotency_key=key, request_hash=canonical_request_hash({"value": 1}),
            status="succeeded", expires_at=expiry)

    def operation(self):
        task = Task.objects.create(business=self.business, title="Prune race task")
        return CRMCommandResult(data={"task": task.pk}, resource=task, status_code=201)


class IdempotencyPruneTests(PruneFixture, TestCase):
    def interleave(self, renewal):
        original = QuerySet.delete
        def delete(query):
            if query.model is CRMCommandIdempotency:
                renewal()
            return original(query)
        with patch.object(QuerySet, "delete", delete):
            return prune_expired_crm_commands(now=self.now)

    def test_reclaimed_processing_receipt_survives_selection(self):
        original_token = self.record.claim_token
        self.assertEqual(self.interleave(lambda: begin_crm_command(**self.command)), 0)
        self.record.refresh_from_db()
        self.assertNotEqual(self.record.claim_token, original_token)
        self.assertEqual(self.record.status, "processing")
        self.assertEqual(self.record.attempts, 2)

    def test_completed_renewal_preserves_replay_and_does_not_repeat_operation(self):
        self.assertEqual(self.interleave(lambda: run_idempotent_crm_command(**self.command, operation=self.operation)), 0)
        result = run_idempotent_crm_command(**self.command, operation=self.operation)
        self.assertTrue(result.replayed)
        self.assertEqual(Task.objects.filter(title="Prune race task").count(), 1)

    def test_cutoff_limit_and_unchanged_expired_control(self):
        boundary = self.receipt("boundary", self.now)
        future = self.receipt("future", self.now + timezone.timedelta(microseconds=1))
        self.assertEqual(prune_expired_crm_commands(limit=0, now=self.now), 0)
        self.assertEqual(prune_expired_crm_commands(limit=-1, now=self.now), 0)
        self.assertEqual(prune_expired_crm_commands(limit=1, now=self.now), 1)
        self.assertFalse(CRMCommandIdempotency.objects.filter(pk=self.record.pk).exists())
        self.assertTrue(CRMCommandIdempotency.objects.filter(pk=boundary.pk).exists())
        self.assertEqual(prune_expired_crm_commands(now=self.now), 1)
        self.assertTrue(CRMCommandIdempotency.objects.filter(pk=future.pk).exists())
        self.assertEqual(prune_expired_crm_commands(now=self.now), 0)


@skipUnlessDBFeature("has_select_for_update")
class IdempotencyPruneConcurrencyTests(PruneFixture, TransactionTestCase):
    def test_other_connection_renews_selected_receipt_and_replay_survives(self):
        selected, renewed = Event(), Event()
        original = QuerySet.delete
        control = self.receipt("unchanged", self.now - timezone.timedelta(seconds=2))
        def delete(query):
            if query.model is CRMCommandIdempotency:
                selected.set()
                self.assertTrue(renewed.wait(20), "Renewal did not commit")
            return original(query)
        def prune():
            connections.close_all()
            try:
                return prune_expired_crm_commands(now=self.now)
            finally:
                connections.close_all()
        with ThreadPoolExecutor(max_workers=1) as pool, patch.object(QuerySet, "delete", delete):
            future = pool.submit(prune)
            self.assertTrue(selected.wait(20), "Prune did not select candidates")
            try:
                result = run_idempotent_crm_command(**self.command, operation=self.operation)
            finally:
                renewed.set()
            self.assertEqual(future.result(timeout=25), 1)
        self.assertFalse(CRMCommandIdempotency.objects.filter(pk=control.pk).exists())
        replay = run_idempotent_crm_command(**self.command, operation=self.operation)
        self.assertTrue(replay.replayed)
        self.assertEqual(replay.data, result.data)
        self.assertEqual(Task.objects.filter(title="Prune race task").count(), 1)
