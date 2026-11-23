from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from unittest import skipUnless

from django.db import close_old_connections, connection, connections
from django.test import TransactionTestCase, override_settings
from rest_framework.exceptions import PermissionDenied

from apps.core.domain_errors import InvalidTransition
from apps.core.models import AuditLog
from apps.notifications.models import Notification
from apps.scheduling.services import cancel_appointment
from .models import AppointmentAssistant
from . import tests_assistant_revoke as fixtures
from .tests_patient_services import key


@skipUnless(connection.vendor == "postgresql", "Assistant lifecycle races require PostgreSQL row locks")
@override_settings(MEDICAL_DATA_KEYS={"test": key(7)}, MEDICAL_DATA_ACTIVE_KEY_ID="test",
                   MEDICAL_IDENTITY_INDEX_KEY=key(8))
class AssistantConcurrencyTests(TransactionTestCase):
    def setUp(self):
        fixtures.AssistantRevokeTests.setUpTestData.__func__(self)
        fixtures.AssistantRevokeTests.setUp(self)

    invite = fixtures.AssistantRevokeTests.invite
    accept = fixtures.AssistantRevokeTests.accept
    revoke = fixtures.AssistantRevokeTests.revoke

    def parallel(self, commands):
        barrier = Barrier(2)
        def execute(command):
            close_old_connections()
            try:
                barrier.wait(timeout=10)
                try:
                    return command()
                except InvalidTransition:
                    return "stale"
                except PermissionDenied:
                    return "denied"
            finally:
                connections.close_all()
        with ThreadPoolExecutor(max_workers=2) as executor:
            return [future.result(timeout=30) for future in [executor.submit(execute, command) for command in commands]]

    def test_duplicate_acceptance_is_one_audit_and_transition(self):
        self.assertCountEqual(self.parallel([lambda: self.accept()[1], lambda: self.accept()[1]]), [False, True])
        self.invitation.refresh_from_db()
        self.assertEqual((self.invitation.state, self.invitation.revision), ("active", 2))
        self.assertEqual(AuditLog.objects.filter(entity_type="AppointmentAssistant", entity_id=str(self.invitation.pk),
            metadata__kind="medical_assistant_accepted").count(), 1)

    def test_new_invitation_requests_cannot_duplicate_open_scope(self):
        self.revoke()
        results = self.parallel([lambda: self.invite(idempotency_key="first-new")[1],
                                 lambda: self.invite(idempotency_key="second-new")[1]])
        self.assertCountEqual(results, [False, "stale"])
        self.assertEqual(AppointmentAssistant.objects.filter(appointment=self.appointment, state="pending").count(), 1)
        pending = AppointmentAssistant.objects.get(appointment=self.appointment, state="pending")
        self.assertIsNotNone(pending.invitation_notification_id)
        self.assertEqual(Notification.objects.filter(recipient=self.assistant).count(), 2)

    def test_cancellation_leaves_no_active_or_pending_invitation(self):
        def cancel():
            cancel_appointment(appointment=self.appointment, actor=self.owner, reason="Synthetic race")
            return "cancelled"
        results = self.parallel([lambda: self.accept()[1], cancel])
        self.assertIn("cancelled", results)
        self.invitation.refresh_from_db()
        self.assertEqual(self.invitation.state, "ended")
        with self.assertRaises(PermissionDenied):
            self.accept()

    def test_acceptance_and_revoke_cannot_both_apply_to_same_revision(self):
        results = self.parallel([lambda: self.accept()[1], lambda: self.revoke()[1]])
        self.assertEqual(results.count(False), 1)
        self.assertTrue("stale" in results or "denied" in results)
        self.invitation.refresh_from_db()
        self.assertEqual(self.invitation.revision, 2)
        self.assertIn(self.invitation.state, ["active", "revoked"])
