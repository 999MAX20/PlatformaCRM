from decimal import Decimal
from uuid import uuid4

from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import TransactionTestCase
from django.utils import timezone

from apps.accounts.models import User
from apps.businesses.models import Business
from apps.clients.models import Client
from .models import Payment, PlanTerms, PlanAllocation


class PlanMoneyMigrationTests(TransactionTestCase):
    def test_existing_receipt_survives_forward_and_reverse_without_backfill(self):
        owner = User.objects.create_user(username="money-migration")
        business = Business.objects.create(owner=owner, name="Legacy payments", slug="money-migration")
        client = Client.objects.create(business=business, full_name="Legacy client")
        before = ("payments", "0001_initial")
        after = ("payments", "0002_payment_plan_planterms_planallocation_and_more")
        executor = MigrationExecutor(connection)
        executor.migrate([before])
        try:
            OldPayment = executor.loader.project_state([before]).apps.get_model("payments", "Payment")
            row = OldPayment.objects.create(business_id=business.pk, client_id=client.pk, kind="receipt",
                amount="100.25", currency="KZT", method="cash", occurred_at=timezone.now(),
                submission_id=uuid4(), request_hash="legacy", note="Preserved")
            identity, timestamp = row.pk, row.created_at
            MigrationExecutor(connection).migrate([after])
            current = Payment.objects.get(pk=identity)
            self.assertIsNone(current.plan_id)
            self.assertFalse(PlanTerms.objects.exists())
            self.assertFalse(PlanAllocation.objects.exists())
            MigrationExecutor(connection).migrate([before])
        finally:
            MigrationExecutor(connection).migrate([after])
        current = Payment.objects.get(pk=identity)
        self.assertEqual((current.amount, current.note, current.created_at), (Decimal("100.25"), "Preserved", timestamp))
