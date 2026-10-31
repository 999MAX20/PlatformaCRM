from datetime import timedelta

from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import TransactionTestCase
from django.utils import timezone

from apps.accounts.models import User
from apps.businesses.models import Business
from apps.clients.models import Client
from apps.scheduling.models import Appointment
from apps.services.models import Service


class RecordMigrationTests(TransactionTestCase):
    def test_existing_nullable_specialist_visit_and_history_are_preserved(self):
        owner = User.objects.create_user(username="legacy-record", email="legacy-record@example.test")
        business = Business.objects.create(owner=owner, name="Legacy", slug="legacy-record")
        client = Client.objects.create(business=business, full_name="Legacy Client")
        service = Service.objects.create(business=business, name="Service", duration_minutes=30)
        previous = ("scheduling", "0009_appointment_booked_duration_minutes_and_more")
        latest = ("scheduling", "0010_appointment_responsible_user_and_more")
        executor = MigrationExecutor(connection)
        executor.migrate([previous])
        try:
            old = executor.loader.project_state([previous]).apps.get_model("scheduling", "Appointment")
            start = timezone.now() - timedelta(days=7)
            row = old.objects.create(business_id=business.pk, client_id=client.pk, service_id=service.pk,
                start_at=start, end_at=start + timedelta(minutes=30), status="completed", notes="Retained history", resource_id=None)
            identity = row.pk
            created_at, updated_at = row.created_at, row.updated_at
        finally:
            MigrationExecutor(connection).migrate([latest])
        row = Appointment.objects.get(pk=identity)
        self.assertEqual((row.status, row.notes, row.resource_id), ("completed", "Retained history", None))
        self.assertEqual((row.created_at, row.updated_at), (created_at, updated_at))
        self.assertIsNone(row.responsible_user_id)
        self.assertIsNone(row.source_conversation_id)
