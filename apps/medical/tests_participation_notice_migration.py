from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import TransactionTestCase, override_settings

from apps.notifications.models import Notification
from apps.notifications.personal_selectors import personal_states
from . import tests_participation_notifications as fixtures
from .models import MedicalAuditEvent, MedicalParticipationNotice, TreatmentParticipation
from .tests_patient_services import key


@override_settings(MEDICAL_DATA_KEYS={"test": key(7)}, MEDICAL_DATA_ACTIVE_KEY_ID="test",
                   MEDICAL_IDENTITY_INDEX_KEY=key(8))
class ParticipationNoticeMigrationTests(TransactionTestCase):
    propose = fixtures.ParticipationNotificationTests.propose

    def test_notice_schema_roundtrip_preserves_domain_and_does_not_resend(self):
        fixtures.ParticipationNotificationTests.setUpTestData.__func__(type(self))
        item, _ = self.propose()
        notification = Notification.objects.get()
        event = MedicalAuditEvent.objects.get(action="participation_proposed")
        executor = MigrationExecutor(connection)
        leaves = executor.loader.graph.leaf_nodes()
        try:
            executor.migrate([("medical", "0015_participation_source")])
            self.assertEqual(Notification.objects.count(), 1)
            old_apps = executor.loader.project_state([("medical", "0015_participation_source")]).apps
            old_participation = old_apps.get_model("medical", "TreatmentParticipation")
            self.assertEqual(old_participation.objects.get(pk=item.pk).state, "pending")
            self.assertTrue(MedicalAuditEvent.objects.filter(pk=event.pk).exists())
            MigrationExecutor(connection).migrate(leaves)
            self.assertFalse(MedicalParticipationNotice.objects.exists())
            self.assertTrue(Notification.objects.filter(pk=notification.pk).exists())
            self.assertFalse(personal_states(actor=self.recipient, business=self.business).exists())
        finally:
            MigrationExecutor(connection).migrate(leaves)
