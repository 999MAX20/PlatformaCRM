from unittest import skipUnless

from django.db import connection
from django.test import TransactionTestCase, override_settings
from rest_framework.exceptions import PermissionDenied

from .assistant_invitations import revoke_appointment_assistant
from .models import MedicalAuditEvent, MedicalDocumentRevision
from . import tests_assistant_documents as fixtures
from . import tests_assistant_concurrency as concurrency
from .tests_patient_services import key


@skipUnless(connection.vendor == "postgresql", "Assistant draft/revoke race requires PostgreSQL row locks")
@override_settings(MEDICAL_DATA_KEYS={"test": key(7)}, MEDICAL_DATA_ACTIVE_KEY_ID="test",
                   MEDICAL_IDENTITY_INDEX_KEY=key(8))
class AssistantDocumentConcurrencyTests(TransactionTestCase):
    def setUp(self):
        fixtures.AssistantDocumentTests.setUpTestData.__func__(self)
        fixtures.AssistantDocumentTests.setUp(self)

    save = fixtures.AssistantDocumentTests.save
    parallel = concurrency.AssistantConcurrencyTests.parallel

    def test_save_and_revoke_are_serialized_without_late_write_or_partial_audit(self):
        def revoke():
            revoke_appointment_assistant(actor=self.doctor, business_id=self.business.pk,
                invitation_id=self.invitation.pk, expected_revision=2, idempotency_key="concurrent-revoke")
            return "revoked"
        results = self.parallel([lambda: (self.save(), "saved")[1], revoke])
        self.assertIn("revoked", results)
        self.invitation.refresh_from_db()
        self.assertEqual(self.invitation.state, "revoked")
        count = MedicalDocumentRevision.objects.count()
        self.assertEqual(count, 1 if "saved" in results else 0)
        self.assertEqual(MedicalAuditEvent.objects.filter(action="document_draft_created").count(), count)
        with self.assertRaises(PermissionDenied):
            self.save()
        self.assertEqual(MedicalDocumentRevision.objects.count(), count)
