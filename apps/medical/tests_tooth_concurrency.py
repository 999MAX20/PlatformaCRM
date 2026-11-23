from unittest import skipUnless

from django.db import connection
from django.test import TransactionTestCase, override_settings

from . import tests_tooth_services as fixtures
from . import tests_tooth_options as surfaces
from . import tests_order_concurrency as races
from . import tests_patient_services as crypto
from .models import DentalToothHistory, DentalToothState, MedicalAuditEvent
from .tooth_content import read_tooth_history


@skipUnless(connection.vendor == "postgresql", "Tooth-state races require PostgreSQL row locks")
@override_settings(MEDICAL_DATA_KEYS={"test": crypto.key(7)}, MEDICAL_DATA_ACTIVE_KEY_ID="test",
                   MEDICAL_IDENTITY_INDEX_KEY=crypto.key(8))
class ToothConcurrencyTests(TransactionTestCase):
    def setUp(self):
        fixtures.PrimaryToothObservationTests.setUpTestData.__func__(self)

    save = fixtures.PrimaryToothObservationTests.save
    parallel = races.OrderConcurrencyTests.parallel
    policy = surfaces.ToothSurfaceOptionsTests.policy

    def cases(self):
        return ({"surface": ""}, {"surface": "synthetic_a", "surface_reference": "synthetic-v1"})

    def test_duplicate_initial_observation_creates_one_history_and_audit(self):
        with override_settings(MEDICAL_TOOTH_SURFACE_POLICIES=self.policy()):
            for args in self.cases():
                with self.subTest(surface=args["surface"]):
                    command = lambda: self.save(**args, idempotency_key=f"duplicate-{args['surface']}")[1]
                    self.assertCountEqual(self.parallel([command, command]), [False, True])
                    state = DentalToothState.objects.get(patient=self.patient, tooth=11, surface=args["surface"])
                    self.assertEqual(state.revision, 1)
                    self.assertEqual(DentalToothHistory.objects.filter(tooth_state=state).count(), 1)
                    self.assertEqual(MedicalAuditEvent.objects.filter(tooth_history__tooth_state=state).count(), 1)

    def test_competing_initial_observations_conflict_without_duplicate_state(self):
        with override_settings(MEDICAL_TOOTH_SURFACE_POLICIES=self.policy()):
            for args in self.cases():
                with self.subTest(surface=args["surface"]):
                    def command(key):
                        return self.save(**args, observation=key, idempotency_key=f"{key}-{args['surface']}")[1]
                    self.assertCountEqual(self.parallel([lambda: command("first"), lambda: command("second")]), [False, "conflict"])
                    states = DentalToothState.objects.filter(patient=self.patient, tooth=11, surface=args["surface"])
                    self.assertEqual(states.count(), 1)
                    self.assertEqual(DentalToothHistory.objects.filter(tooth_state=states.get()).count(), 1)

    def test_competing_updates_preserve_previous_observation_and_one_successor(self):
        with override_settings(MEDICAL_TOOTH_SURFACE_POLICIES=self.policy()):
            for args in self.cases():
                with self.subTest(surface=args["surface"]):
                    first, _ = self.save(**args, idempotency_key=f"initial-{args['surface']}")
                    original = read_tooth_history(first)
                    def command(key):
                        return self.save(**args, observation=key, expected_tooth_revision=1,
                            idempotency_key=f"{key}-{args['surface']}")[1]
                    self.assertCountEqual(self.parallel([lambda: command("one"), lambda: command("two")]), [False, "conflict"])
                    first.tooth_state.refresh_from_db()
                    self.assertEqual(first.tooth_state.revision, 2)
                    self.assertEqual(DentalToothHistory.objects.filter(tooth_state=first.tooth_state).count(), 2)
                    self.assertEqual(DentalToothHistory.objects.get(tooth_state=first.tooth_state, revision=2).previous_id, first.pk)
                    first.refresh_from_db()
                    self.assertEqual(read_tooth_history(first), original)

    def test_different_teeth_both_commit(self):
        self.assertEqual(self.parallel([lambda: self.save(tooth=11, idempotency_key="eleven")[1],
            lambda: self.save(tooth=12, idempotency_key="twelve")[1]]), [False, False])
        self.assertEqual(DentalToothState.objects.filter(patient=self.patient).count(), 2)
        self.assertEqual(DentalToothHistory.objects.count(), 2)
