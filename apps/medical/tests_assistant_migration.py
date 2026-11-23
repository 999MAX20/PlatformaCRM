from django.db import connection
from django.db.migrations.exceptions import IrreversibleError
from django.db.migrations.executor import MigrationExecutor
from django.test import TransactionTestCase
from django.utils import timezone
from apps.notifications.models import Notification

from .models import AppointmentAssistant
from . import tests_assistant_models as fixtures


class AssistantMigrationTests(TransactionTestCase):
    def setUp(self):
        fixtures.AssistantInvitationIntegrityTests.setUpTestData.__func__(self)
        self.leaves = MigrationExecutor(connection).loader.graph.leaf_nodes()
        self.addCleanup(lambda: MigrationExecutor(connection).migrate(self.leaves))

    invitation = fixtures.AssistantInvitationIntegrityTests.invitation

    def test_notification_link_prevents_destructive_reverse(self):
        notice = Notification.objects.create(business=self.business, recipient=self.assistant,
            channel="system", category="system", kind="work", text="", send_at=timezone.now(), status="sent")
        item = self.invitation(invitation_notification=notice)
        item.save()
        with self.assertRaisesMessage(IrreversibleError, "Assistant notification links exist"):
            MigrationExecutor(connection).migrate([("medical", "0041_appointment_assistant")])
        self.assertEqual(AppointmentAssistant.objects.get(pk=item.pk).invitation_notification_id, notice.pk)

    def test_empty_roundtrip_preserves_existing_appointment_and_patient(self):
        appointment_id, patient_id = self.appointment.pk, self.patient.pk
        MigrationExecutor(connection).migrate([("medical", "0040_document_review_confirmation")])
        MigrationExecutor(connection).migrate(self.leaves)
        self.appointment.refresh_from_db()
        self.patient.refresh_from_db()
        self.assertEqual((self.appointment.pk, self.patient.pk), (appointment_id, patient_id))
        item = self.invitation()
        item.full_clean()
        item.save()

    def test_history_prevents_destructive_reverse(self):
        item = self.invitation()
        item.save()
        with self.assertRaisesMessage(IrreversibleError, "Assistant invitation history exists"):
            MigrationExecutor(connection).migrate([("medical", "0040_document_review_confirmation")])
        self.assertTrue(AppointmentAssistant.objects.filter(pk=item.pk).exists())
