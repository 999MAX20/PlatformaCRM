from unittest.mock import patch

from django.test import TestCase, override_settings
from rest_framework.exceptions import PermissionDenied

from apps.businesses.models import BusinessCapability
from apps.scheduling.models import Appointment, VisitPlan, VisitPlanStep
from . import tests_correction_access as fixtures
from . import tests_encounter_services as encounter_fixtures
from . import tests_patient_services as crypto_fixtures
from .clinical_plan_links import visit_step_snapshot
from .clinical_plan_reads import list_clinical_visit_steps
from .correction_access_writes import save_correction_target
from .encounter_content import read_encounter_revision


@override_settings(MEDICAL_DATA_KEYS={"test": crypto_fixtures.key(7)}, MEDICAL_DATA_ACTIVE_KEY_ID="test",
                   MEDICAL_IDENTITY_INDEX_KEY=crypto_fixtures.key(8))
class ClinicalPlanCorrectionTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        fixtures.CorrectionAccessTests.setUpTestData.__func__(cls)
        BusinessCapability.objects.create(business=cls.business, module_key="visit_plans", is_enabled=True)
        plan = VisitPlan.objects.create(business=cls.business, client=cls.patient_client,
                                       responsible_user=cls.doctor, created_by=cls.owner)
        cls.step = VisitPlanStep.objects.create(plan=plan, position=1, service=cls.service,
                                               resource=cls.staff, branch=cls.first)

    def test_exact_correction_target_can_link_and_expiry_removes_picker_access(self):
        encounter_fixtures.PrimaryEncounterDraftTests.setUp(self)
        Appointment.objects.filter(pk=self.appointment.pk).update(status="completed")
        grant = fixtures.CorrectionAccessTests.request(self)[0]
        scope = dict(actor=self.doctor, business_id=self.business.pk, patient_id=self.patient.pk,
                     encounter_id=self.encounter_record.pk, correction_access_id=grant.pk)
        with self.assertRaises(PermissionDenied):
            list_clinical_visit_steps(**scope)
        grant = fixtures.CorrectionAccessTests.review(self, grant)[0]
        snapshot = visit_step_snapshot(self.step)
        self.assertEqual(list_clinical_visit_steps(**scope)["results"], [snapshot])
        content = {"plan_steps": [{"id": "00000000-0000-4000-8000-000000000001",
                                   "description": "Synthetic correction step", "visit_step": snapshot}]}
        version, _ = save_correction_target(actor=self.doctor, business_id=self.business.pk, request_id=grant.pk,
            expected_revision=1, content=content, reason="Synthetic correction", idempotency_key="save-link")
        self.assertEqual(read_encounter_revision(version)["content"], content)
        with patch("apps.medical.correction_access_context.timezone.now", return_value=grant.expires_at):
            with self.assertRaises(PermissionDenied):
                list_clinical_visit_steps(**scope)
