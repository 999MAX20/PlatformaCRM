from datetime import timedelta
from django.db import connection
from django.db.migrations.exceptions import IrreversibleError
from django.db.migrations.executor import MigrationExecutor
from django.test import TransactionTestCase
from django.utils import timezone
from .models import ReceptionDuty
from . import tests_reception_models as fixtures


class ReceptionDutyMigrationTests(TransactionTestCase):
    def test_empty_roundtrip_and_existing_duty_guard(self):
        fixtures.ReceptionRequestIntegrityTests.setUpTestData.__func__(self)
        leaves=MigrationExecutor(connection).loader.graph.leaf_nodes()
        self.addCleanup(lambda: MigrationExecutor(connection).migrate(leaves))
        MigrationExecutor(connection).migrate([("medical","0054_reception_contact_cycle")])
        MigrationExecutor(connection).migrate(leaves)
        self.patient.refresh_from_db()
        now=timezone.now()
        item=ReceptionDuty.objects.create(business=self.business,branch=self.first,lead=self.member,starts_at=now,ends_at=now+timedelta(hours=8))
        with self.assertRaisesMessage(IrreversibleError,"Reception duties or notices exist"):
            MigrationExecutor(connection).migrate([("medical","0054_reception_contact_cycle")])
        self.assertTrue(ReceptionDuty.objects.filter(pk=item.pk).exists())
