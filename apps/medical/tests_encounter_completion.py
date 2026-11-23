from unittest.mock import patch

from django.test import TestCase, override_settings
from rest_framework.exceptions import PermissionDenied, NotFound, ValidationError
from rest_framework.test import APIClient

from apps.businesses.models import Business, RolePermission
from apps.core.domain_errors import InvalidTransition
from apps.scheduling.services import complete_appointment
from . import tests_encounter_services as fixtures
from .audit import MedicalAuditUnavailable
from .encounter_completion import complete_primary_encounter, read_encounter_completion
from .encounter_content import CLINICAL_FIELDS, read_encounter_revision
from .encounter_services import save_primary_encounter_draft
from .models import MedicalAuditEvent
from .tests_patient_services import key


@override_settings(MEDICAL_DATA_KEYS={"test": key(7)}, MEDICAL_DATA_ACTIVE_KEY_ID="test",
                   MEDICAL_IDENTITY_INDEX_KEY=key(8))
class EncounterCompletionTests(TestCase):
    setUpTestData = classmethod(fixtures.PrimaryEncounterDraftTests.setUpTestData.__func__)

    def setUp(self):
        fixtures.PrimaryEncounterDraftTests.setUp(self)
        self.saved, _ = save_primary_encounter_draft(actor=self.doctor, business_id=self.business.pk,
            patient_id=self.patient.pk, encounter_id=self.encounter_record.pk, expected_revision=1,
            content={field: "Synthetic clinical content" for field in CLINICAL_FIELDS}, idempotency_key="fill")

    def complete(self, **changes):
        return complete_primary_encounter(**(dict(actor=self.doctor, business_id=self.business.pk,
            patient_id=self.patient.pk, encounter_id=self.encounter_record.pk, expected_revision=2,
            expected_appointment_updated_at=self.appointment.updated_at, reason="Synthetic early completion",
            idempotency_key="complete") | changes))

    def unchanged(self):
        self.encounter_record.refresh_from_db()
        self.appointment.refresh_from_db()
        self.assertEqual((self.encounter_record.state, self.appointment.status), ("draft", "created"))
        self.assertFalse(MedicalAuditEvent.objects.filter(action="encounter_finalized").exists())

    def test_complete_preserves_content_and_revokes_appointment_only_access(self):
        before = read_encounter_revision(self.saved)
        version, replayed = self.complete()
        self.assertFalse(replayed)
        self.assertEqual(version.pk, self.saved.pk)
        self.encounter_record.refresh_from_db()
        self.appointment.refresh_from_db()
        self.assertEqual((self.encounter_record.state, self.appointment.status), ("finalized", "completed"))
        self.assertEqual(read_encounter_revision(version), before)
        self.assertEqual(MedicalAuditEvent.objects.filter(action="encounter_finalized").count(), 1)
        with self.assertRaises(PermissionDenied):
            read_encounter_completion(actor=self.doctor, business_id=self.business.pk,
                patient_id=self.patient.pk, encounter_id=self.encounter_record.pk)
        with self.assertRaises(PermissionDenied):
            self.complete()

    def test_ordinary_calendar_completion_cannot_bypass_clinical_completion(self):
        with self.assertRaises(InvalidTransition):
            complete_appointment(appointment=self.appointment, actor=self.owner, reason="Synthetic")
        self.unchanged()

    def test_incomplete_sections_stale_version_and_missing_early_reason(self):
        for changes in ({"expected_revision": 1}, {"reason": ""}):
            with self.assertRaises((InvalidTransition, ValidationError)):
                self.complete(**changes)
            self.unchanged()
        save_primary_encounter_draft(actor=self.doctor, business_id=self.business.pk,
            patient_id=self.patient.pk, encounter_id=self.encounter_record.pk, expected_revision=2,
            content={"complaints": "Still saved"}, idempotency_key="incomplete")
        with self.assertRaises(InvalidTransition) as caught:
            self.complete(expected_revision=3)
        self.assertIn("diagnosis", caught.exception.errors["missing_fields"])
        self.unchanged()

    def test_role_branch_tenant_and_revoked_permission(self):
        other = Business.objects.create(owner=self.owner, name="Independent completion business")
        for changes in ({"actor": self.owner}, {"business_id": other.pk}):
            with self.assertRaises((PermissionDenied, NotFound)):
                self.complete(**changes)
        self.assignment.branches.clear()
        with self.assertRaises(PermissionDenied):
            self.complete()
        self.assignment.branches.add(self.first)
        RolePermission.objects.filter(business_role=self.role, resource="medical_records", action="update").update(is_allowed=False)
        with self.assertRaises(PermissionDenied):
            self.complete()
        self.unchanged()

    def test_audit_or_downstream_failure_rolls_back_both_states(self):
        for target, error in (("apps.medical.encounter_completion.write_patient_audit", MedicalAuditUnavailable()),
                              ("apps.scheduling.services.schedule_post_service_followup", RuntimeError("Synthetic failure"))):
            with patch(target, side_effect=error), self.assertRaises(type(error)):
                self.complete()
            self.unchanged()

    def test_private_http_readiness_and_completion(self):
        api = APIClient()
        api.force_authenticate(self.doctor)
        url = f"/api/medical/encounters/{self.encounter_record.pk}/"
        scope = {"business_id": self.business.pk, "patient_id": self.patient.pk}
        response = api.get(url + "completion/", scope)
        self.assertEqual(response.status_code, 200, response.data)
        self.assertTrue(response.data["ready"])
        self.assertEqual(response["Cache-Control"], "no-store, private")
        response = api.post(url + "complete/", scope | {"expected_revision": 2,
            "expected_appointment_updated_at": self.appointment.updated_at.isoformat(), "reason": "Synthetic"},
            format="json", HTTP_IDEMPOTENCY_KEY="http-complete")
        self.assertEqual(response.status_code, 200, response.data)
        self.assertNotIn("content", response.data)

    def test_http_denial_is_private_and_audited(self):
        api = APIClient()
        api.force_authenticate(self.owner)
        url = f"/api/medical/encounters/{self.encounter_record.pk}/"
        scope = {"business_id": self.business.pk, "patient_id": self.patient.pk}
        response = api.get(url + "completion/", scope)
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response["Cache-Control"], "no-store, private")
        response = api.post(url + "complete/", scope | {"expected_revision": 2,
            "expected_appointment_updated_at": self.appointment.updated_at.isoformat()},
            format="json", HTTP_IDEMPOTENCY_KEY="denied-complete")
        self.assertEqual(response.status_code, 403)
        self.assertEqual(MedicalAuditEvent.objects.filter(action="access_denied", actor=self.owner).count(), 2)
        self.unchanged()

    def test_medical_business_requires_an_encounter_before_calendar_completion(self):
        from apps.scheduling.models import Appointment
        other = Appointment.objects.create(business=self.business, client=self.patient.client,
            service=self.appointment.service, resource=self.appointment.resource, branch=self.first,
            start_at=self.appointment.start_at, end_at=self.appointment.end_at)
        with self.assertRaises(InvalidTransition):
            complete_appointment(appointment=other, actor=self.owner, reason="Synthetic")
        other.refresh_from_db()
        self.assertEqual(other.status, "created")
