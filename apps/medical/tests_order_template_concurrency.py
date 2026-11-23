from unittest import skipUnless

from django.db import connection
from django.test import TransactionTestCase, override_settings

from . import tests_order_templates as fixtures
from . import tests_order_concurrency as races
from . import tests_patient_services as crypto
from .models import MedicalOrderRevision


@skipUnless(connection.vendor == "postgresql", "Order template races require PostgreSQL row locks")
@override_settings(MEDICAL_DATA_KEYS={"test": crypto.key(7)}, MEDICAL_DATA_ACTIVE_KEY_ID="test",
                   MEDICAL_IDENTITY_INDEX_KEY=crypto.key(8))
class OrderTemplateConcurrencyTests(TransactionTestCase):
    def setUp(self):
        fixtures.OrderTemplateTests.setUpTestData.__func__(self)
        fixtures.OrderTemplateTests.setUp(self)

    save = fixtures.OrderTemplateTests.save
    preview = fixtures.OrderTemplateTests.preview
    parallel = races.OrderConcurrencyTests.parallel

    def test_duplicate_template_application_creates_one_version(self):
        self.assertCountEqual(self.parallel([lambda: self.save()[1], lambda: self.save()[1]]), [False, True])
        self.assertEqual(MedicalOrderRevision.objects.filter(template_version=self.template).count(), 1)

    def test_competing_edits_keep_one_source_and_version(self):
        version, _ = self.save()
        def edit(key):
            return self.save(order_id=version.order_id, expected_order_revision=1, idempotency_key=key)[1]
        self.assertCountEqual(self.parallel([lambda: edit("one"), lambda: edit("two")]), [False, "conflict"])
        self.assertEqual(MedicalOrderRevision.objects.filter(template_version=self.template).count(), 2)
