from unittest import skipUnless

from django.db import connection
from django.test import TransactionTestCase, override_settings

from apps.scheduling.models import Appointment, VisitPlan
from . import tests_clinical_plan_booking as fixtures
from . import tests_order_concurrency as concurrency_fixtures
from . import tests_patient_services as crypto_fixtures
from .models import MedicalEncounterRevision, MedicalPlanStepLink


@skipUnless(connection.vendor == "postgresql", "Clinical booking races require PostgreSQL row locks")
@override_settings(MEDICAL_DATA_KEYS={"test": crypto_fixtures.key(7)}, MEDICAL_DATA_ACTIVE_KEY_ID="test",
                   MEDICAL_IDENTITY_INDEX_KEY=crypto_fixtures.key(8))
class ClinicalBookingConcurrencyTests(TransactionTestCase):
    def setUp(self):
        fixtures.ClinicalPlanBookingTests.setUpTestData.__func__(self)
        fixtures.ClinicalPlanBookingTests.setUp(self)

    book = fixtures.ClinicalPlanBookingTests.book
    parallel = concurrency_fixtures.OrderConcurrencyTests.parallel

    def test_duplicate_confirmations_book_one_visit(self):
        self.assertCountEqual(self.parallel([lambda: self.book()["replayed"], lambda: self.book()["replayed"]]), [False, True])
        self.assertEqual((Appointment.objects.count(), VisitPlan.objects.count(), MedicalPlanStepLink.objects.count()), (2, 1, 1))

    def test_competing_confirmations_keep_one_calendar_and_clinical_result(self):
        self.assertCountEqual(self.parallel([lambda: self.book(idempotency_key="first")["replayed"],
            lambda: self.book(idempotency_key="second")["replayed"]]), [False, "conflict"])
        self.assertEqual((Appointment.objects.count(), VisitPlan.objects.count(), MedicalEncounterRevision.objects.count()), (2, 1, 3))
