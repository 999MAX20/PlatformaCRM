from unittest import skipUnless

from django.db import connection
from django.test import TransactionTestCase, override_settings

from . import tests_clinical_plan_links as fixtures
from . import tests_patient_services as crypto_fixtures
from .models import MedicalEncounterRevision, MedicalPlanStepLink
from . import tests_order_concurrency as concurrency_fixtures


@skipUnless(connection.vendor == "postgresql", "Clinical plan races require PostgreSQL row locks")
@override_settings(MEDICAL_DATA_KEYS={"test": crypto_fixtures.key(7)}, MEDICAL_DATA_ACTIVE_KEY_ID="test",
                   MEDICAL_IDENTITY_INDEX_KEY=crypto_fixtures.key(8))
class ClinicalPlanConcurrencyTests(TransactionTestCase):
    def setUp(self):
        fixtures.ClinicalPlanLinkTests.setUpTestData.__func__(self)
        fixtures.ClinicalPlanLinkTests.setUp(self)

    save = fixtures.ClinicalPlanLinkTests.save
    parallel = concurrency_fixtures.OrderConcurrencyTests.parallel

    def test_duplicate_command_creates_one_link_version(self):
        self.assertCountEqual(self.parallel([lambda: self.save()[1], lambda: self.save()[1]]), [False, True])
        self.assertEqual(MedicalPlanStepLink.objects.count(), 1)
        self.assertEqual(MedicalEncounterRevision.objects.count(), 2)

    def test_competing_links_cannot_replace_one_encounter_revision(self):
        self.assertCountEqual(self.parallel([
            lambda: self.save(idempotency_key="first")[1], lambda: self.save(idempotency_key="second")[1],
        ]), [False, "conflict"])
        self.assertEqual(MedicalPlanStepLink.objects.count(), 1)
        self.assertEqual(MedicalEncounterRevision.objects.count(), 2)
