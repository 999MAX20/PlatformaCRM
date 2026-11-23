from datetime import timedelta
from unittest.mock import patch
from uuid import uuid4

from django.db import DatabaseError
from django.test import TestCase, override_settings
from rest_framework.exceptions import NotFound, PermissionDenied, ValidationError
from rest_framework.test import APIClient

from . import tests_encounter_services as fixtures
from . import tests_patient_services as crypto_fixtures
from .audit import MedicalAuditUnavailable
from .clinical_plan_teeth import read_tooth_plan_steps
from .encounter_content import read_encounter_revision, validate_clinical_draft
from .identity_crypto import MedicalDataUnavailable
from .models import DentalToothState, MedicalPlanToothLink, MedicalEncounterRevision


@override_settings(MEDICAL_DATA_KEYS={"test": crypto_fixtures.key(7)}, MEDICAL_DATA_ACTIVE_KEY_ID="test",
                   MEDICAL_IDENTITY_INDEX_KEY=crypto_fixtures.key(8))
class ClinicalPlanTeethTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        fixtures.PrimaryEncounterDraftTests.setUpTestData.__func__(cls)

    def setUp(self):
        fixtures.PrimaryEncounterDraftTests.setUp(self)
        self.content = {"plan_steps": [{"id": str(uuid4()), "description": "Synthetic tooth plan", "teeth": [11, 51]}]}
        self.scope = dict(actor=self.doctor, business_id=self.business.pk, patient_id=self.patient.pk,
                          appointment_id=self.appointment.pk, tooth=11)

    def save(self, **overrides):
        return fixtures.PrimaryEncounterDraftTests.save(self, **({"content": self.content} | overrides))

    def test_save_replay_and_latest_unlink_preserve_as_of_and_exact_history(self):
        version, _ = self.save()
        self.assertTrue(self.save()[1])
        self.assertEqual(MedicalPlanToothLink.objects.count(), 2)
        self.assertFalse(DentalToothState.objects.exists())
        self.assertEqual(read_tooth_plan_steps(**self.scope)["results"][0]["step"], self.content["plan_steps"][0])
        self.assertEqual(read_tooth_plan_steps(**(self.scope | {"tooth": 51}))["results"][0]["version_id"], version.pk)
        self.save(content={"plan_steps": []}, expected_revision=2, idempotency_key="unlinked")
        self.assertEqual(read_tooth_plan_steps(**self.scope)["results"], [])
        self.assertEqual(read_tooth_plan_steps(**self.scope, as_of=version.created_at)["results"][0]["version_id"], version.pk)
        self.assertEqual(read_tooth_plan_steps(**self.scope, as_of=version.created_at - timedelta(seconds=1))["results"], [])
        self.assertEqual(read_encounter_revision(version)["content"], self.content)

    def test_invalid_and_duplicate_teeth_never_persist(self):
        for teeth in ([0], [19], [59], [11, 11], [True], ["11"], None, {"11": True}):
            with self.subTest(teeth=teeth), self.assertRaises(ValidationError):
                validate_clinical_draft({"plan_steps": [{**self.content["plan_steps"][0], "teeth": teeth}]})
        self.assertFalse(MedicalPlanToothLink.objects.exists())

    def test_index_tamper_fails_closed_on_exact_and_tooth_read(self):
        version, _ = self.save()
        MedicalPlanToothLink.objects.filter(version=version, tooth=11).update(step_id=uuid4())
        with self.assertRaises(MedicalDataUnavailable):
            read_encounter_revision(version)
        with self.assertRaises(MedicalDataUnavailable):
            read_tooth_plan_steps(**self.scope)

    def test_cross_patient_and_business_cannot_use_current_appointment_basis(self):
        from apps.businesses.models import Business
        from apps.clients.models import Client
        from .models import PatientProfile
        self.save()
        other_client = Client.objects.create(business=self.business, full_name="Other synthetic patient")
        other_patient = PatientProfile.objects.create(business=self.business, client=other_client, created_by=self.owner)
        with self.assertRaises(PermissionDenied):
            read_tooth_plan_steps(**(self.scope | {"patient_id": other_patient.pk}))
        other_business = Business.objects.create(owner=self.owner, name="Other synthetic business", slug="other-tooth-plan")
        with self.assertRaises((NotFound, PermissionDenied)):
            read_tooth_plan_steps(**(self.scope | {"business_id": other_business.pk}))

    def test_audit_failure_rolls_back_index_and_blocks_read(self):
        with patch("apps.medical.audit.MedicalAuditEvent.objects.create", side_effect=DatabaseError):
            with self.assertRaises(MedicalAuditUnavailable):
                self.save()
        self.assertFalse(MedicalPlanToothLink.objects.exists())
        self.assertEqual(MedicalEncounterRevision.objects.count(), 1)
        self.save()
        with patch("apps.medical.audit.MedicalAuditEvent.objects.create", side_effect=DatabaseError):
            with self.assertRaises(MedicalAuditUnavailable):
                read_tooth_plan_steps(**self.scope)

    def test_private_api_pagination_invalid_and_current_access(self):
        self.content["plan_steps"].append({"id": str(uuid4()), "description": "Second synthetic step", "teeth": [11]})
        self.save()
        api = APIClient(); api.force_authenticate(self.doctor)
        scope = {key: value for key, value in self.scope.items() if key != "actor"}
        url = "/api/medical/encounters/tooth-plan/"
        first = api.get(url, scope | {"limit": 1})
        self.assertEqual(first.status_code, 200, first.data)
        self.assertEqual(first["Cache-Control"], "no-store, private")
        self.assertEqual(first.data["results"][0]["step"], self.content["plan_steps"][0])
        second = api.get(url, scope | {"limit": 1, "before_id": first.data["next_before_id"],
                                      "as_of": first.data["as_of"].isoformat()})
        self.assertNotEqual(first.data["results"][0]["id"], second.data["results"][0]["id"])
        self.assertIsNone(second.data["next_before_id"])
        self.assertEqual(api.get(url, scope | {"tooth": 19}).status_code, 400)
        api.force_authenticate(self.owner)
        self.assertEqual(api.get(url, scope).status_code, 403)
        self.assignment.branches.clear()
        with self.assertRaises(PermissionDenied):
            read_tooth_plan_steps(**self.scope)
        with self.assertRaises(PermissionDenied):
            self.save()
