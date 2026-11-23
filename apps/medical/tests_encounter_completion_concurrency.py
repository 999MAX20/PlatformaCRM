from unittest import skipUnless

from django.db import connection
from django.test import TransactionTestCase, override_settings
from rest_framework.exceptions import PermissionDenied

from . import tests_encounter_completion as fixtures
from . import tests_order_concurrency as races
from .encounter_services import save_primary_encounter_draft
from .models import MedicalAuditEvent
from .tests_patient_services import key


@skipUnless(connection.vendor == "postgresql", "Completion races require PostgreSQL row locks")
@override_settings(MEDICAL_DATA_KEYS={"test": key(7)}, MEDICAL_DATA_ACTIVE_KEY_ID="test",
                   MEDICAL_IDENTITY_INDEX_KEY=key(8))
class EncounterCompletionConcurrencyTests(TransactionTestCase):
    parallel = races.OrderConcurrencyTests.parallel
    complete = fixtures.EncounterCompletionTests.complete

    def setUp(self):
        fixtures.EncounterCompletionTests.setUpTestData.__func__(self)
        fixtures.EncounterCompletionTests.setUp(self)

    def attempt(self, command):
        try:
            return command()
        except PermissionDenied:
            return "revoked"

    def test_simultaneous_completion_has_one_effect_and_no_lingering_basis(self):
        results = self.parallel([lambda: self.attempt(lambda: self.complete()[1]),
            lambda: self.attempt(lambda: self.complete()[1])])
        self.assertCountEqual(results, [False, "revoked"])
        self.assertEqual(MedicalAuditEvent.objects.filter(action="encounter_finalized").count(), 1)

    def test_save_and_completion_never_commit_against_different_content(self):
        def save():
            return save_primary_encounter_draft(actor=self.doctor, business_id=self.business.pk,
                patient_id=self.patient.pk, encounter_id=self.encounter_record.pk, expected_revision=2,
                content={"complaints": "New incomplete clinical content"}, idempotency_key="race-save")[1]
        results = self.parallel([lambda: self.attempt(lambda: self.complete()[1]), lambda: self.attempt(save)])
        self.assertEqual(results.count(False), 1)
        self.assertTrue("conflict" in results or "revoked" in results)
        self.encounter_record.refresh_from_db()
        self.appointment.refresh_from_db()
        self.assertEqual(self.appointment.status, "completed" if self.encounter_record.state == "finalized" else "created")
