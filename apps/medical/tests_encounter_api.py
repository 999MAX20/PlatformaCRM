from unittest.mock import patch

from django.db import DatabaseError
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from apps.businesses.models import Business
from apps.clients.models import Client
from . import tests_encounter_open as fixtures
from . import tests_patient_services as crypto_fixtures
from .models import MedicalAuditEvent, MedicalEncounter, MedicalEncounterRevision, PatientProfile


@override_settings(MEDICAL_DATA_KEYS={"test": crypto_fixtures.key(7)}, MEDICAL_DATA_ACTIVE_KEY_ID="test",
                   MEDICAL_IDENTITY_INDEX_KEY=crypto_fixtures.key(8))
class MedicalEncounterAPITests(TestCase):
    @classmethod
    def setUpTestData(cls):
        fixtures.OpenPrimaryEncounterTests.setUpTestData.__func__(cls)

    def setUp(self):
        self.api = APIClient()
        self.api.force_authenticate(self.doctor)
        self.url = "/api/medical/encounters/"
        self.scope = {"business_id": self.business.pk, "patient_id": self.patient.pk}
        self.payload = {**self.scope, "record_id": self.record.pk, "appointment_id": self.appointment.pk,
            "expected_patient_revision": 1, "expected_appointment_updated_at": self.appointment.updated_at.isoformat(),
            "content": {"complaints": "Private synthetic API complaint"}}

    def open(self, **overrides):
        return self.api.post(self.url, self.payload | overrides, format="json", HTTP_IDEMPOTENCY_KEY="api-open")

    def read(self, version_id, **overrides):
        return self.api.get(f"{self.url}versions/{version_id}/",
            {**self.scope, "appointment_id": self.appointment.pk} | overrides)

    def assert_private(self, response):
        self.assertEqual(response["Cache-Control"], "no-store, private")
        self.assertEqual(response["Pragma"], "no-cache")

    def test_open_save_read_and_historical_version_through_http(self):
        opened = self.open()
        self.assertEqual(opened.status_code, 201, opened.data)
        self.assert_private(opened)
        self.assertEqual(set(opened.data), {"id", "version_id", "revision", "replayed"})
        saved = self.api.post(f"{self.url}{opened.data['id']}/draft/", {**self.scope,
            "expected_revision": 1, "content": {"plan": "  Оқу жоспары\n"}},
            format="json", HTTP_IDEMPOTENCY_KEY="api-save")
        self.assertEqual(saved.status_code, 200, saved.data)
        self.assert_private(saved)
        latest = self.read(saved.data["version_id"])
        self.assertEqual(latest.status_code, 200, latest.data)
        self.assertEqual(latest.data["content"], {"plan": "  Оқу жоспары\n"})
        self.assert_private(latest)
        old = self.read(opened.data["version_id"])
        self.assertEqual(old.data["content"], self.payload["content"])
        self.assertEqual(MedicalAuditEvent.objects.count(), 4)
        self.appointment.refresh_from_db()
        self.assertEqual(self.appointment.status, "created")

    def test_replay_and_changed_payload_conflict_without_clinical_echo(self):
        opened = self.open()
        replay = self.open()
        self.assertEqual(replay.status_code, 200, replay.data)
        self.assertTrue(replay.data["replayed"])
        self.assertEqual(replay.data["version_id"], opened.data["version_id"])
        conflict = self.open(content={"complaints": "Different secret"})
        self.assertEqual(conflict.status_code, 409, conflict.data)
        self.assertNotIn("Different secret", conflict.content.decode())
        self.assert_private(conflict)
        self.assertEqual(MedicalEncounter.objects.count(), 1)

    def test_structured_plan_versions_replay_and_revocation_without_booking_effects(self):
        from apps.scheduling.models import Appointment, VisitPlan, VisitPlanStep
        from apps.payments.models import Payment
        models = (Appointment, VisitPlan, VisitPlanStep, Payment)
        counts = [model.objects.count() for model in models]
        steps = [{"id": "00000000-0000-4000-8000-000000000001", "description": "Synthetic plan step"}]
        opened = self.open(content={"plan_steps": steps})
        self.assertEqual(opened.status_code, 201, opened.data)
        self.assertEqual(self.read(opened.data["version_id"]).data["content"], {"plan_steps": steps})
        replay = self.open(content={"plan_steps": steps})
        self.assertTrue(replay.data["replayed"])
        payload = {**self.scope, "expected_revision": 1, "content": {"plan_steps": []}}
        url = f"{self.url}{opened.data['id']}/draft/"
        saved = self.api.post(url, payload, format="json", HTTP_IDEMPOTENCY_KEY="plan-save")
        self.assertEqual(saved.status_code, 200, saved.data)
        self.assertEqual(self.read(saved.data["version_id"]).data["content"], {"plan_steps": []})
        self.assertEqual(self.read(opened.data["version_id"]).data["content"], {"plan_steps": steps})
        self.assertEqual([model.objects.count() for model in models], counts)
        self.assignment.branches.clear()
        denied = self.api.post(url, payload, format="json", HTTP_IDEMPOTENCY_KEY="plan-save")
        self.assertEqual(denied.status_code, 403)
        self.assert_private(denied)
        self.assertEqual(self.read(opened.data["version_id"]).status_code, 403)

    def test_risk_fields_are_versioned_private_and_not_inferred_for_old_records(self):
        opened = self.open()
        risks = {"allergies": "Synthetic allergy — оқу", "contraindications": "Synthetic contraindication"}
        saved = self.api.post(f"{self.url}{opened.data['id']}/draft/", {**self.scope,
            "expected_revision": 1, "content": risks}, format="json", HTTP_IDEMPOTENCY_KEY="risk-save")
        self.assertEqual(saved.status_code, 200, saved.data)
        self.assertEqual(self.read(saved.data["version_id"]).data["content"], risks)
        self.assertNotIn("allergies", self.read(opened.data["version_id"]).data["content"])
        version = MedicalEncounterRevision.objects.get(pk=saved.data["version_id"])
        for value in risks.values():
            self.assertNotIn(value, version.content_encrypted)
        invalid = self.api.post(f"{self.url}{opened.data['id']}/draft/", {**self.scope,
            "expected_revision": 2, "content": {"allergies": {"absent": True}}},
            format="json", HTTP_IDEMPOTENCY_KEY="invalid-risk")
        self.assertEqual(invalid.status_code, 400)
        self.assert_private(invalid)
        self.assignment.branches.clear()
        denied = self.read(saved.data["version_id"])
        self.assertEqual(denied.status_code, 403)
        self.assert_private(denied)
        self.assertNotIn(risks["allergies"], denied.content.decode())

    def test_explicit_non_applicability_roundtrip_and_conflict_are_private(self):
        content = {"not_applicable": {"procedures": "Synthetic no procedure at consultation"}}
        opened = self.open(content=content)
        self.assertEqual(opened.status_code, 201, opened.data)
        self.assertEqual(self.read(opened.data["version_id"]).data["content"], content)
        replay = self.open(content=content)
        self.assertEqual(replay.status_code, 200, replay.data)
        self.assertTrue(replay.data["replayed"])
        invalid = self.api.post(f"{self.url}{opened.data['id']}/draft/", {**self.scope,
            "expected_revision": 1, "content": {**content, "procedures": "Synthetic procedure"}},
            format="json", HTTP_IDEMPOTENCY_KEY="contradiction")
        self.assertEqual(invalid.status_code, 400, invalid.data)
        self.assert_private(invalid)
        self.assertEqual(MedicalEncounterRevision.objects.count(), 1)
        self.assignment.branches.clear()
        self.assertEqual(self.read(opened.data["version_id"]).status_code, 403)
        self.assertEqual(self.open(content=content).status_code, 403)

    def test_stale_save_returns_409_without_advancing_revision(self):
        opened = self.open()
        response = self.api.post(f"{self.url}{opened.data['id']}/draft/", {**self.scope,
            "expected_revision": 9, "content": {"diagnosis": "Not saved"}},
            format="json", HTTP_IDEMPOTENCY_KEY="stale")
        self.assertEqual(response.status_code, 409, response.data)
        self.assert_private(response)
        self.assertEqual(MedicalEncounterRevision.objects.count(), 1)

    def test_extra_author_fields_and_invalid_clinical_values_are_rejected(self):
        for values in ({"author_id": self.owner.pk}, {"branch_id": self.second.pk},
                       {"content": {"diagnosis": 123}}, {"content": {"unsupported": "Secret"}}):
            response = self.open(**values)
            self.assertEqual(response.status_code, 400, response.data)
            self.assert_private(response)
            self.assertNotIn("Secret", response.content.decode())
        missing = self.api.post(self.url, self.payload, format="json")
        self.assertEqual(missing.status_code, 400, missing.data)
        self.assertFalse(MedicalEncounter.objects.exists())

    def test_anonymous_owner_and_revoked_role_fail_closed(self):
        opened = self.open()
        self.api.force_authenticate(None)
        response = self.read(opened.data["version_id"])
        self.assertIn(response.status_code, (401, 403))
        self.assert_private(response)
        self.api.force_authenticate(self.owner)
        response = self.read(opened.data["version_id"])
        self.assertEqual(response.status_code, 403)
        self.assert_private(response)
        self.api.force_authenticate(self.doctor)
        self.assignment.revoked_at = timezone.now()
        self.assignment.save(update_fields=["revoked_at"])
        response = self.open()
        self.assertEqual(response.status_code, 403)
        self.assert_private(response)

    def test_foreign_patient_and_business_are_rejected(self):
        opened = self.open()
        foreign = Business.objects.create(owner=self.owner, name="Foreign", slug="encounter-api-foreign")
        client = Client.objects.create(business=foreign, full_name="Foreign synthetic patient")
        patient = PatientProfile.objects.create(business=foreign, client=client, created_by=self.owner)
        for values, expected in (({"patient_id": patient.pk}, 404), ({"business_id": foreign.pk}, 403)):
            response = self.read(opened.data["version_id"], **values)
            self.assertEqual(response.status_code, expected, response.data)
            self.assert_private(response)
            self.assertNotIn("Private synthetic", response.content.decode())

    def test_audit_failure_returns_503_and_retry_creates_once(self):
        with patch("apps.medical.audit.MedicalAuditEvent.objects.create", side_effect=DatabaseError("synthetic")):
            response = self.open()
        self.assertEqual(response.status_code, 503, response.data)
        self.assert_private(response)
        self.assertFalse(MedicalEncounter.objects.exists())
        response = self.open()
        self.assertEqual(response.status_code, 201, response.data)
        with patch("apps.medical.audit.MedicalAuditEvent.objects.create", side_effect=DatabaseError("synthetic")):
            read = self.read(response.data["version_id"])
        self.assertEqual(read.status_code, 503, read.data)
        self.assertNotIn("Private synthetic", read.content.decode())
        self.assert_private(read)

    def test_missing_read_basis_and_mutating_methods_are_not_available(self):
        opened = self.open()
        response = self.api.get(f"{self.url}versions/{opened.data['version_id']}/", self.scope)
        self.assertEqual(response.status_code, 400, response.data)
        self.assert_private(response)
        response = self.api.delete(self.url)
        self.assertEqual(response.status_code, 405)
        self.assert_private(response)
