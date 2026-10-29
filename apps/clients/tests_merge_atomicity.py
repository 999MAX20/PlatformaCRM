from unittest.mock import patch
from uuid import uuid4

from django.test import TransactionTestCase
from django.utils import timezone

from apps.activities.models import ActivityEvent, Note, Tag, TaggedObject
from apps.activities.taxonomy import ActivityEvents
from apps.clients.models import Client, ClientMergeLog
from apps.clients import tests as client_tests
from apps.core.audit import write_audit_log
from apps.core.models import AuditLog, CustomFieldDefinition, CustomFieldValue
from apps.leads.models import Lead
from apps.payments.models import Payment
from apps.tasks.models import Task


class ClientMergeAtomicityTests(TransactionTestCase):
    """Exercise the real HTTP boundary without a TestCase outer transaction."""

    def setUp(self):
        client_tests.DuplicateDetectionFoundationTests.setUp(self)
        self.lead = Lead.objects.create(business=self.business, client=self.duplicate)
        Task.objects.create(business=self.business, client=self.duplicate, title="Follow up")
        Note.objects.create(business=self.business, client=self.duplicate, text="Keep history")
        self.payment = Payment.objects.create(
            business=self.business, client=self.duplicate, kind="receipt", amount="125.00",
            currency="KZT", occurred_at=timezone.now(), method="cash", created_by=self.owner,
            submission_id=uuid4(),
        )
        tag = Tag.objects.create(business=self.business, name="Shared")
        definition = CustomFieldDefinition.objects.create(
            business=self.business, entity_type="client", key="merge_test", label="Merge test", field_type="text",
        )
        for client in (self.target, self.duplicate):
            TaggedObject.objects.create(business=self.business, tag=tag, entity_type="client", entity_id=str(client.pk))
            CustomFieldValue.objects.create(business=self.business, definition=definition,
                                           entity_type="client", entity_id=str(client.pk), value_json=client.full_name)
        self.models = (Client, Lead, Task, Note, Payment, TaggedObject, CustomFieldValue,
                       ClientMergeLog, ActivityEvent, AuditLog)

    def snapshot(self):
        return {model.__name__: list(model.objects.order_by("pk").values()) for model in self.models}

    def merge(self):
        return self.api.post(f"/api/clients/{self.target.pk}/merge/",
                             {"duplicate_client_id": self.duplicate.pk}, format="json")

    def test_audit_failure_rolls_back_all_rows_then_retry_succeeds_once(self):
        before = self.snapshot()
        with patch("apps.clients.views.write_audit_log", side_effect=RuntimeError("audit unavailable")):
            self.assertEqual(self.merge().status_code, 500)
        self.assertEqual(self.snapshot(), before)
        response = self.merge()
        self.assertEqual(response.status_code, 200)
        self.duplicate.refresh_from_db()
        self.payment.refresh_from_db()
        self.lead.refresh_from_db()
        self.assertTrue(self.duplicate.is_archived)
        self.assertEqual(self.payment.client_id, self.target.pk)
        self.assertEqual(self.lead.client_id, self.target.pk)
        self.assertEqual(str(self.payment.amount), "125.00")
        self.assertEqual(ClientMergeLog.objects.count(), 1)
        self.assertEqual(AuditLog.objects.filter(metadata__kind="merge").count(), 1)
        self.assertEqual(ActivityEvent.objects.filter(event_type=ActivityEvents.CLIENT_MERGED).count(), 1)

    def test_self_merge_rejected_without_writes(self):
        before = self.snapshot()
        response = self.api.post(f"/api/clients/{self.target.pk}/merge/",
                                 {"duplicate_client_id": self.target.pk}, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(self.snapshot(), before)

    def test_failure_after_audit_insert_rolls_back_audit_and_merge(self):
        before = self.snapshot()

        def insert_then_fail(*args, **kwargs):
            write_audit_log(*args, **kwargs)
            raise RuntimeError("audit post-write failure")

        with patch("apps.clients.views.write_audit_log", side_effect=insert_then_fail):
            self.assertEqual(self.merge().status_code, 500)
        self.assertEqual(self.snapshot(), before)

    def test_activity_failure_rolls_back_before_request_audit(self):
        before = self.snapshot()
        with patch("apps.clients.services.create_activity_event", side_effect=RuntimeError("activity unavailable")):
            with patch("apps.clients.views.write_audit_log") as audit:
                self.assertEqual(self.merge().status_code, 500)
                audit.assert_not_called()
        self.assertEqual(self.snapshot(), before)
