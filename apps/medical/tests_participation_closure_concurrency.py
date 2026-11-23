from unittest import skipUnless

from django.db import connection
from django.test import TransactionTestCase, override_settings

from . import tests_participation_own_end as fixtures
from . import tests_participation_closure as heads
from . import tests_order_concurrency as races
from .models import MedicalAuditEvent
from .tests_patient_services import key


@skipUnless(connection.vendor == "postgresql", "Participation closure requires PostgreSQL row locks")
@override_settings(MEDICAL_DATA_KEYS={"test": key(7)}, MEDICAL_DATA_ACTIVE_KEY_ID="test", MEDICAL_IDENTITY_INDEX_KEY=key(8))
class ParticipationClosureConcurrencyTests(TransactionTestCase):
    propose = fixtures.OwnParticipationEndTests.propose
    respond = fixtures.OwnParticipationEndTests.respond
    active = fixtures.OwnParticipationEndTests.active
    end = fixtures.OwnParticipationEndTests.end
    close = heads.ParticipationClosureTests.close
    parallel = races.OrderConcurrencyTests.parallel

    def setUp(self):
        fixtures.OwnParticipationEndTests.setUpTestData.__func__(self)
        self.item = self.active()

    def test_duplicate_own_end_has_one_audit_transition(self):
        self.assertCountEqual(self.parallel([lambda: self.end(self.item)[1], lambda: self.end(self.item)[1]]), [False, True])
        self.assertEqual(MedicalAuditEvent.objects.filter(action="participation_ended").count(), 1)

    def test_head_and_own_end_cannot_overwrite_each_other(self):
        self.assertCountEqual(self.parallel([lambda: self.end(self.item)[1], lambda: self.close(self.item)[1]]), [False, "conflict"])
        self.assertEqual(MedicalAuditEvent.objects.filter(action="participation_ended").count(), 1)
