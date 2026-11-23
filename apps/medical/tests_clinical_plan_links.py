from unittest.mock import patch

from django.db import DatabaseError
from django.db.models.deletion import ProtectedError
from django.test import TestCase, override_settings
from rest_framework.exceptions import PermissionDenied
from rest_framework.test import APIClient

from apps.businesses.models import Business, BusinessCapability
from apps.clients.models import Client
from apps.core.domain_errors import InvalidTransition, ModuleDisabled
from apps.payments.models import Payment
from apps.scheduling.models import Appointment, VisitPlan, VisitPlanStep
from . import tests_encounter_services as fixtures
from . import tests_patient_services as crypto_fixtures
from .audit import MedicalAuditUnavailable
from .clinical_plan_links import visit_step_snapshot
from .clinical_plan_reads import list_clinical_visit_steps
from .encounter_content import read_encounter_revision
from .encounter_services import save_primary_encounter_draft
from .identity_crypto import MedicalDataUnavailable
from .models import MedicalEncounterRevision, MedicalPlanStepLink


@override_settings(MEDICAL_DATA_KEYS={"test": crypto_fixtures.key(7)}, MEDICAL_DATA_ACTIVE_KEY_ID="test",
                   MEDICAL_IDENTITY_INDEX_KEY=crypto_fixtures.key(8))
class ClinicalPlanLinkTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        fixtures.PrimaryEncounterDraftTests.setUpTestData.__func__(cls)
        BusinessCapability.objects.create(business=cls.business, module_key="visit_plans", is_enabled=True)
        cls.plan = VisitPlan.objects.create(business=cls.business, client=cls.patient_client,
                                           responsible_user=cls.doctor, created_by=cls.owner)
        cls.step = VisitPlanStep.objects.create(plan=cls.plan, position=1, service=cls.service,
                                               resource=cls.staff, branch=cls.first)

    def setUp(self):
        fixtures.PrimaryEncounterDraftTests.setUp(self)
        self.content = {"plan_steps": [{"id": "00000000-0000-4000-8000-000000000001",
            "description": "Synthetic linked clinical step", "visit_step": visit_step_snapshot(self.step)}]}
        self.api = APIClient()
        self.api.force_authenticate(self.doctor)
        self.scope = dict(business_id=self.business.pk, patient_id=self.patient.pk,
                          encounter_id=self.encounter_record.pk, appointment_id=self.appointment.pk)

    def save(self, **overrides):
        return save_primary_encounter_draft(**(dict(actor=self.doctor, business_id=self.business.pk,
            patient_id=self.patient.pk, encounter_id=self.encounter_record.pk, expected_revision=1,
            content=self.content, idempotency_key="plan-link") | overrides))

    def test_link_replay_preserves_exact_snapshot_without_organizational_effects(self):
        counts = [model.objects.count() for model in (Appointment, VisitPlan, VisitPlanStep, Payment)]
        version, _ = self.save()
        self.assertEqual(read_encounter_revision(version)["content"], self.content)
        self.assertEqual(MedicalPlanStepLink.objects.get().visit_step_id, self.step.pk)
        self.assertTrue(self.save()[1])
        self.assertEqual(MedicalPlanStepLink.objects.count(), 1)
        self.assertEqual([model.objects.count() for model in (Appointment, VisitPlan, VisitPlanStep, Payment)], counts)
        self.plan.refresh_from_db()
        self.assertEqual(self.plan.revision, 1)
        self.assertNotIn("Synthetic", version.content_encrypted)
        with self.assertRaises(ProtectedError):
            self.step.delete()

    def test_existing_link_survives_archival_rename_and_org_permission_removal(self):
        first, _ = self.save()
        VisitPlan.objects.filter(pk=self.plan.pk).update(is_archived=True)
        type(self.service).objects.filter(pk=self.service.pk).update(name="Renamed synthetic service")
        BusinessCapability.objects.filter(business=self.business, module_key="visit_plans").update(is_enabled=False)
        later, _ = self.save(expected_revision=2, idempotency_key="later")
        self.assertEqual(read_encounter_revision(later)["content"], self.content)
        self.assertEqual(read_encounter_revision(first)["content"], self.content)
        unlinked, _ = self.save(expected_revision=3, idempotency_key="unlink", content={"plan_steps": []})
        self.assertEqual(read_encounter_revision(unlinked)["content"], {"plan_steps": []})
        self.assertEqual(MedicalPlanStepLink.objects.count(), 2)
        with self.assertRaises(ModuleDisabled):
            self.save(expected_revision=4, idempotency_key="relink")

    def test_new_link_rejects_stale_label_and_archived_step(self):
        self.content["plan_steps"][0]["visit_step"]["service_name"] = "Forged synthetic label"
        with self.assertRaises(InvalidTransition):
            self.save()
        self.content["plan_steps"][0]["visit_step"] = visit_step_snapshot(self.step)
        VisitPlan.objects.filter(pk=self.plan.pk).update(is_archived=True)
        with self.assertRaises(InvalidTransition):
            self.save()
        self.assertFalse(MedicalPlanStepLink.objects.exists())
        self.assertEqual(MedicalEncounterRevision.objects.count(), 1)

    def test_wrong_patient_link_is_denied_and_existing_corruption_fails_closed(self):
        version, _ = self.save()
        other = Client.objects.create(business=self.business, full_name="Other synthetic patient")
        VisitPlan.objects.filter(pk=self.plan.pk).update(client=other)
        with self.assertRaises(MedicalDataUnavailable):
            read_encounter_revision(version)
        with self.assertRaises(MedicalDataUnavailable):
            self.save(expected_revision=2, idempotency_key="wrong-patient")

    def test_new_link_to_another_patient_is_denied_before_persisting(self):
        other = Client.objects.create(business=self.business, full_name="Other synthetic patient")
        VisitPlan.objects.filter(pk=self.plan.pk).update(client=other)
        with self.assertRaises(PermissionDenied):
            self.save()
        self.assertFalse(MedicalPlanStepLink.objects.exists())
        self.assertEqual(MedicalEncounterRevision.objects.count(), 1)

    def test_new_link_cannot_cross_business_boundaries(self):
        from apps.services.models import Service
        business = Business.objects.create(owner=self.owner, name="Other business", slug="other-plan-business")
        client = Client.objects.create(business=business, full_name="Other synthetic patient")
        service = Service.objects.create(business=business, name="Other private service")
        plan = VisitPlan.objects.create(business=business, client=client, responsible_user=self.owner, created_by=self.owner)
        step = VisitPlanStep.objects.create(plan=plan, position=1, service=service)
        self.content["plan_steps"][0]["visit_step"] = visit_step_snapshot(step)
        with self.assertRaises(PermissionDenied):
            self.save()
        self.assertFalse(MedicalPlanStepLink.objects.exists())

    def test_missing_reference_and_audit_failure_never_return_unbacked_history(self):
        with patch("apps.medical.audit.MedicalAuditEvent.objects.create", side_effect=DatabaseError):
            with self.assertRaises(MedicalAuditUnavailable):
                self.save()
        self.assertFalse(MedicalPlanStepLink.objects.exists())
        self.assertEqual(MedicalEncounterRevision.objects.count(), 1)
        version, _ = self.save()
        MedicalPlanStepLink.objects.all().delete()
        with self.assertRaises(MedicalDataUnavailable):
            read_encounter_revision(version)

    def test_revoked_medical_scope_blocks_replay_and_picker(self):
        self.save()
        self.assignment.branches.clear()
        with self.assertRaises(PermissionDenied):
            self.save()
        with self.assertRaises(PermissionDenied):
            list_clinical_visit_steps(actor=self.doctor, **self.scope)

    def test_picker_is_private_audited_and_omits_money(self):
        url = "/api/medical/encounters/visit-steps/"
        response = self.api.get(url, self.scope)
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data, {"results": [visit_step_snapshot(self.step)], "next_before_id": None})
        self.assertEqual(response["Cache-Control"], "no-store, private")
        with patch("apps.medical.audit.MedicalAuditEvent.objects.create", side_effect=DatabaseError):
            failed = self.api.get(url, self.scope)
        self.assertEqual(failed.status_code, 503)
        self.assertNotIn(self.service.name, failed.content.decode())
        self.api.force_authenticate(self.owner)
        self.assertEqual(self.api.get(url, self.scope).status_code, 403)

    def test_picker_filters_unavailable_steps_and_validates_basis(self):
        VisitPlan.objects.filter(pk=self.plan.pk).update(is_archived=True)
        self.assertEqual(list_clinical_visit_steps(actor=self.doctor, **self.scope)["results"], [])
        url = "/api/medical/encounters/visit-steps/"
        self.assertEqual(self.api.get(url, self.scope | {"correction_access_id": 1}).status_code, 400)
        self.assertEqual(self.api.get(url, self.scope | {"limit": 51}).status_code, 400)
