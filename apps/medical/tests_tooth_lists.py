from datetime import timedelta, datetime, timezone as dt_timezone
from unittest.mock import patch

from django.db import DatabaseError
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.test import APIClient

from . import tests_tooth_services as fixtures
from .tests_patient_services import key
from apps.businesses.models import Business
from .models import DentalToothState, DentalToothHistory, MedicalAuditEvent
from .audit import MedicalAuditUnavailable
from .identity_crypto import MedicalDataUnavailable
from .tooth_reads import read_tooth_snapshot, read_tooth_revision_history


@override_settings(MEDICAL_DATA_KEYS={"test": key(7)}, MEDICAL_DATA_ACTIVE_KEY_ID="test",
                   MEDICAL_IDENTITY_INDEX_KEY=key(8), MEDICAL_TOOTH_SURFACE_POLICIES="")
class ToothListTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        fixtures.PrimaryToothObservationTests.setUpTestData.__func__(cls)

    save = fixtures.PrimaryToothObservationTests.save

    def scope(self):
        return dict(actor=self.doctor, business_id=self.business.pk, patient_id=self.patient.pk,
                    appointment_id=self.appointment.pk)

    def snapshot(self, **kwargs):
        return read_tooth_snapshot(**(self.scope() | kwargs))

    def history(self, state, **kwargs):
        return read_tooth_revision_history(**(self.scope() | dict(tooth_state_id=state.pk) | kwargs))

    def test_empty_snapshot_is_audited_without_invented_healthy_teeth(self):
        result = self.snapshot()
        self.assertEqual(result["observations"], [])
        self.assertIsNone(result["next_after_state_id"])
        self.assertEqual(MedicalAuditEvent.objects.get().action, "read")

    def test_snapshot_boundary_and_historical_revision(self):
        first, _ = self.save()
        second, _ = self.save(expected_tooth_revision=1, observation="Later", idempotency_key="later")
        self.assertEqual(self.snapshot(as_of=first.observed_at - timedelta(microseconds=1))["observations"], [])
        row = self.snapshot(as_of=first.observed_at)["observations"][0]
        self.assertEqual((row["history_id"], row["current_revision"]), (first.pk, 2))
        self.assertEqual(row["observation"], "Private synthetic tooth observation")
        self.assertEqual(self.snapshot()["observations"][0]["history_id"], second.pk)

    def test_location_paging_does_not_lose_later_locations(self):
        first, _ = self.save()
        second, _ = self.save(tooth=51, idempotency_key="milk")
        page = self.snapshot(limit=1)
        self.assertEqual([x["tooth"] for x in page["observations"]], [11])
        tail = self.snapshot(limit=1, after_state_id=page["next_after_state_id"], as_of=page["as_of"])
        self.assertEqual([x["tooth"] for x in tail["observations"]], [51])
        self.assertIsNone(tail["next_after_state_id"])
        before = self.snapshot(limit=1, as_of=first.observed_at-timedelta(seconds=1))
        self.assertEqual(before["observations"], [])
        self.assertIsNotNone(before["next_after_state_id"])

    def test_history_pagination_and_author_without_clinical_text(self):
        first, _ = self.save()
        second, _ = self.save(expected_tooth_revision=1, idempotency_key="later")
        page = self.history(first.tooth_state, limit=1)
        self.assertEqual(page["versions"][0]["history_id"], second.pk)
        self.assertEqual(page["versions"][0]["author_id"], self.doctor.pk)
        self.assertNotIn("observation", page["versions"][0])
        tail = self.history(first.tooth_state, limit=1, before_revision=page["next_before_revision"])
        self.assertEqual(tail["versions"][0]["history_id"], first.pk)
        self.assertIsNone(tail["next_before_revision"])

    def test_invalid_filters(self):
        for args in ({"limit": 51}, {"limit": True}, {"after_state_id": 0}, {"as_of": datetime(2026, 1, 1)}):
            with self.subTest(args=args), self.assertRaises(ValidationError):
                self.snapshot(**args)

    def test_revoked_role_denies_both_reads(self):
        history, _ = self.save()
        type(self.assignment).objects.filter(pk=self.assignment.pk).update(revoked_at=timezone.now())
        for read in (self.snapshot, lambda: self.history(history.tooth_state)):
            with self.assertRaises(PermissionDenied):
                read()

    def test_missing_current_revision_is_not_silently_replaced(self):
        history, _ = self.save()
        DentalToothState.objects.filter(pk=history.tooth_state_id).update(revision=2)
        for read in (self.snapshot, lambda: self.history(history.tooth_state)):
            with self.assertRaises(MedicalDataUnavailable):
                read()
        self.assertEqual(MedicalAuditEvent.objects.count(), 1)

    def test_audit_failure_does_not_decrypt(self):
        self.save()
        with patch("apps.medical.audit.MedicalAuditEvent.objects.create", side_effect=DatabaseError):
            with patch("apps.medical.tooth_reads.read_tooth_history") as decrypt:
                with self.assertRaises(MedicalAuditUnavailable):
                    self.snapshot()
                decrypt.assert_not_called()

    def test_http_snapshot_history_and_strict_filters(self):
        history, _ = self.save()
        api = APIClient()
        api.force_authenticate(self.doctor)
        scope = self.scope()
        scope.pop("actor")
        root = "/api/medical/tooth-observations/"
        response = api.get(root+"snapshot/", scope | {"as_of": history.observed_at.isoformat()})
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data["observations"][0]["history_id"], history.pk)
        response = api.get(root+"history/", scope | {"tooth_state_id": history.tooth_state_id})
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response["Cache-Control"], "no-store, private")
        for args in ({"as_of": "invalid"}, {"limit": 51}, {"author_id": self.doctor.pk}):
            response = api.get(root+"snapshot/", scope | args)
            self.assertEqual(response.status_code, 400, response.data)
            self.assertEqual(response["Cache-Control"], "no-store, private")

    def test_same_instant_with_timezone_offset_selects_same_version(self):
        history, _ = self.save()
        shifted = history.observed_at.astimezone(dt_timezone(timedelta(hours=5)))
        self.assertEqual(self.snapshot(as_of=shifted)["observations"][0]["history_id"], history.pk)

    def test_foreign_business_cannot_list_patient_or_history(self):
        history, _ = self.save()
        foreign = Business.objects.create(owner=self.owner, name="Foreign", slug="tooth-list-foreign")
        for read in (lambda: self.snapshot(business_id=foreign.pk),
                     lambda: self.history(history.tooth_state, business_id=foreign.pk)):
            with self.assertRaises(PermissionDenied):
                read()
        self.assertEqual(MedicalAuditEvent.objects.count(), 1)

    def test_corrupt_observation_rolls_back_entire_snapshot_audit(self):
        first, _ = self.save()
        second, _ = self.save(tooth=51, idempotency_key="milk")
        DentalToothHistory.objects.filter(pk=second.pk).update(content_encrypted="invalid")
        with self.assertRaises(MedicalDataUnavailable):
            self.snapshot()
        self.assertEqual(MedicalAuditEvent.objects.count(), 2)
