from unittest import skipUnless

from django.db import connection
from django.test import TransactionTestCase, override_settings

from apps.core.domain_errors import ScheduleConflict
from . import tests_actual_visits as fixtures
from . import tests_order_concurrency as races
from .models import MedicalActualVisit
from .tests_patient_services import key


@skipUnless(connection.vendor == "postgresql", "Actual visit races require PostgreSQL row locks")
@override_settings(MEDICAL_DATA_KEYS={"test": key(7)}, MEDICAL_DATA_ACTIVE_KEY_ID="test", MEDICAL_IDENTITY_INDEX_KEY=key(8))
class ActualVisitConcurrencyTests(TransactionTestCase):
    parallel = races.OrderConcurrencyTests.parallel
    create = fixtures.ActualVisitTests.create

    def setUp(self):
        fixtures.ActualVisitTests.setUpTestData.__func__(self)
        fixtures.ActualVisitTests.setUp(self)

    def attempt(self, key):
        try:
            return self.create(idempotency_key=key)["replayed"]
        except ScheduleConflict:
            return "conflict"

    def test_duplicate_creates_one_visit(self):
        self.assertCountEqual(self.parallel([lambda: self.attempt("same"), lambda: self.attempt("same")]), [False, True])
        self.assertEqual(MedicalActualVisit.objects.count(), 1)

    def test_overlapping_distinct_commands_have_one_winner(self):
        self.assertCountEqual(self.parallel([lambda: self.attempt("one"), lambda: self.attempt("two")]), [False, "conflict"])
        self.assertEqual(MedicalActualVisit.objects.count(), 1)
