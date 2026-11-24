from django.db import connection
from django.db.migrations.exceptions import IrreversibleError
from django.db.migrations.executor import MigrationExecutor
from django.test import TransactionTestCase
from .models import ReceptionBookingRequest
from . import tests_reception_models as fixtures


class ReceptionAdministrationMigrationTests(TransactionTestCase):
    request=fixtures.ReceptionRequestIntegrityTests.request

    def test_legacy_preserved_and_administrative_origin_blocks_reverse(self):
        fixtures.ReceptionRequestIntegrityTests.setUpTestData.__func__(self)
        leaves=MigrationExecutor(connection).loader.graph.leaf_nodes()
        self.addCleanup(lambda:MigrationExecutor(connection).migrate(leaves))
        item=self.request();item.save()
        MigrationExecutor(connection).migrate([("medical","0055_reception_duty_notices")])
        MigrationExecutor(connection).migrate(leaves)
        item.refresh_from_db();self.assertEqual(item.referring_clinician_id,self.member.pk)
        ReceptionBookingRequest.objects.filter(pk=item.pk).update(referring_clinician=None,referring_resource=self.staff)
        with self.assertRaisesMessage(IrreversibleError,"Administrative referral authorship exists"):
            MigrationExecutor(connection).migrate([("medical","0055_reception_duty_notices")])
        item.refresh_from_db();self.assertEqual(item.referring_resource_id,self.staff.pk)
