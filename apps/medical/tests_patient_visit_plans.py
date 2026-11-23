from unittest.mock import patch

from django.db import DatabaseError
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.exceptions import NotFound, PermissionDenied, ValidationError
from rest_framework.test import APIClient

from apps.businesses.models import BusinessCapability, RolePermission
from apps.clients.models import Client
from apps.scheduling.models import VisitPlan, VisitPlanStep
from . import tests_encounter_services as fixtures
from . import tests_patient_services as crypto
from .audit import MedicalAuditUnavailable
from .clinical_plan_reads import list_patient_visit_plans
from .models import MedicalAuditEvent, TreatmentParticipation


@override_settings(MEDICAL_DATA_KEYS={"test": crypto.key(7)}, MEDICAL_DATA_ACTIVE_KEY_ID="test",
                   MEDICAL_IDENTITY_INDEX_KEY=crypto.key(8))
class PatientVisitPlanTests(TestCase):
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
        self.scope = dict(business_id=self.business.pk, patient_id=self.patient.pk,
                          appointment_id=self.appointment.pk)

    def read(self, **overrides):
        return list_patient_visit_plans(actor=self.doctor, **(self.scope | overrides))

    def test_current_patient_projection_has_no_money_or_write_authority(self):
        before = MedicalAuditEvent.objects.count()
        row = self.read()["results"][0]
        self.assertEqual(row["id"], self.plan.pk)
        self.assertEqual(row["steps"][0]["service_name"], self.service.name)
        self.assertEqual(row["steps"][0]["status"], "unscheduled")
        self.assertNotIn("money", row)
        self.assertNotIn("can_change", row)
        self.assertEqual(MedicalAuditEvent.objects.count(), before + 1)

    def test_archive_and_cursor_are_explicit(self):
        newer = VisitPlan.objects.create(business=self.business, client=self.patient_client,
            responsible_user=self.doctor, created_by=self.owner)
        VisitPlanStep.objects.create(plan=newer, position=1, service=self.service,
            resource=self.staff, branch=self.first)
        page = self.read(limit=1)
        self.assertEqual(page["results"][0]["id"], newer.pk)
        self.assertEqual(self.read(before_id=page["next_before_id"])["results"][0]["id"], self.plan.pk)
        VisitPlan.objects.filter(pk=newer.pk).update(is_archived=True)
        self.assertEqual([row["id"] for row in self.read()["results"]], [self.plan.pk])
        self.assertEqual([row["id"] for row in self.read(archived=True)["results"]], [newer.pk])

    def test_participation_rechecked_and_ended_basis_denied_before_audit(self):
        now = timezone.now()
        item = TreatmentParticipation.objects.create(patient=self.patient, member=self.member,
            branch=self.first, proposed_by=self.owner, proposed_at=now, accepted_at=now, state="active")
        self.assertEqual(len(self.read(appointment_id=None, participation_id=item.pk)["results"]), 1)
        TreatmentParticipation.objects.filter(pk=item.pk).update(state="ended", closed_at=now, closed_by=self.owner)
        before = MedicalAuditEvent.objects.count()
        with self.assertRaises(PermissionDenied):
            self.read(appointment_id=None, participation_id=item.pk)
        self.assertEqual(MedicalAuditEvent.objects.count(), before)

    def test_organizational_scope_and_disabled_module_are_not_bypassed(self):
        VisitPlanStep.objects.filter(pk=self.step.pk).update(resource=None)
        self.assertEqual(self.read()["results"], [])

    def test_other_patient_plan_and_invisible_step_are_excluded(self):
        other = Client.objects.create(business=self.business, full_name="Synthetic other patient")
        plan = VisitPlan.objects.create(business=self.business, client=other,
            responsible_user=self.doctor, created_by=self.owner)
        VisitPlanStep.objects.create(plan=plan, position=1, service=self.service,
            resource=self.staff, branch=self.first)
        VisitPlanStep.objects.create(plan=self.plan, position=2, service=self.service,
            resource=None, branch=self.first)
        rows = self.read()["results"]
        self.assertEqual([row["id"] for row in rows], [self.plan.pk])
        self.assertEqual([step["id"] for step in rows[0]["steps"]], [self.step.pk])
        VisitPlanStep.objects.filter(pk=self.step.pk).update(resource=self.staff)
        BusinessCapability.objects.filter(business=self.business, module_key="visit_plans").update(is_enabled=False)
        self.assertEqual(self.read()["results"], [])

    def test_medical_view_and_patient_basis_are_required(self):
        with self.assertRaises(NotFound):
            self.read(patient_id=self.patient.pk + 1000)
        RolePermission.objects.filter(business_role=self.role, resource="medical_records", action="view").update(is_allowed=False)
        with self.assertRaises(PermissionDenied):
            self.read()

    def test_invalid_scope_and_pagination(self):
        for values in ({"limit": 0}, {"before_id": True}, {"archived": "yes"},
                       {"appointment_id": None}, {"participation_id": 1}):
            with self.subTest(values=values), self.assertRaises(ValidationError):
                self.read(**values)

    def test_audit_failure_never_returns_data(self):
        with patch("apps.medical.audit.MedicalAuditEvent.objects.create", side_effect=DatabaseError()):
            with self.assertRaises(MedicalAuditUnavailable):
                self.read()

    def test_api_strict_query_private_cache_and_permission(self):
        api = APIClient()
        api.force_authenticate(self.doctor)
        url = "/api/medical/encounters/patient-plans/"
        response = api.get(url, self.scope)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Cache-Control"], "no-store, private")
        self.assertEqual(api.get(url, self.scope | {"client_id": 123}).status_code, 400)
        api.force_authenticate(self.owner)
        self.assertEqual(api.get(url, self.scope).status_code, 403)
