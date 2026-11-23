from datetime import time, timedelta
from decimal import Decimal
from unittest.mock import patch
from uuid import uuid4

from django.db import DatabaseError
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.test import APIClient

from apps.businesses.models import Business, BusinessCapability, BusinessRole, RolePermission
from apps.core.domain_errors import InvalidTransition, ScheduleConflict
from apps.core.idempotency import CRMCommandConflict
from apps.integrations.models import BusinessEvent
from apps.notifications.models import Notification
from apps.payments.models import Payment
from apps.scheduling.models import Appointment, VisitPlan, VisitPlanStep, WorkingHours
from apps.services.models import Service
from . import tests_encounter_services as fixtures
from . import tests_patient_services as crypto_fixtures
from .audit import MedicalAuditUnavailable
from .clinical_plan_booking import book_clinical_plan_step
from .clinical_plan_links import visit_step_snapshot
from .encounter_content import read_encounter_revision
from .models import MedicalAuditEvent, MedicalEncounterRevision, MedicalPlanStepLink


@override_settings(MEDICAL_DATA_KEYS={"test": crypto_fixtures.key(7)}, MEDICAL_DATA_ACTIVE_KEY_ID="test",
                   MEDICAL_IDENTITY_INDEX_KEY=crypto_fixtures.key(8))
class ClinicalPlanBookingTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        fixtures.PrimaryEncounterDraftTests.setUpTestData.__func__(cls)
        BusinessCapability.objects.create(business=cls.business, module_key="visit_plans", is_enabled=True)
        cls.business.timezone = "UTC"; cls.business.save(update_fields=["timezone"])
        cls.first.uses_business_defaults = True; cls.first.save(update_fields=["uses_business_defaults"])
        cls.service.price_from = Decimal("100.00"); cls.service.duration_minutes = 30
        cls.service.save(update_fields=["price_from", "duration_minutes"])
        cls.booking_role = BusinessRole.objects.create(business=cls.business, name="Synthetic booking role")
        cls.member.business_role = cls.booking_role; cls.member.save(update_fields=["business_role"])
        for resource, action, scope in [("clients", "view", "all"), ("appointments", "view", "own"),
                ("appointments", "create", "own"), ("appointments", "update", "own")]:
            RolePermission.objects.create(business_role=cls.booking_role, resource=resource, action=action,
                                          scope=scope, is_allowed=True)
        for weekday in range(7):
            WorkingHours.objects.create(business=cls.business, weekday=weekday, start_time=time(8), end_time=time(20))

    def setUp(self):
        fixtures.PrimaryEncounterDraftTests.setUp(self)
        self.step_id = str(uuid4())
        self.content = {"plan_steps": [{"id": self.step_id, "description": "Private synthetic clinical plan", "teeth": [11]}]}
        self.source = fixtures.PrimaryEncounterDraftTests.save(self, content=self.content)[0]
        self.start = (timezone.now() + timedelta(days=2)).replace(hour=10, minute=0, second=0, microsecond=0)

    def book(self, **overrides):
        return book_clinical_plan_step(**(dict(actor=self.doctor, business_id=self.business.pk,
            patient_id=self.patient.pk, encounter_id=self.encounter_record.pk, expected_revision=2,
            step_id=self.step_id, service_id=self.service.pk, resource_id=self.staff.pk, branch_id=self.first.pk,
            start_at=self.start, expected_price=Decimal("100.00"), expected_duration_minutes=30,
            confirmed=True, idempotency_key="book-clinical-step") | overrides))

    def test_confirmed_booking_replay_links_one_appointment_without_payment_or_clinical_note_copy(self):
        result = self.book()
        self.assertFalse(result["replayed"])
        self.assertTrue(self.book()["replayed"])
        self.assertEqual((VisitPlan.objects.count(), VisitPlanStep.objects.count(), Appointment.objects.count(), Payment.objects.count()), (1, 1, 2, 0))
        appointment = Appointment.objects.get(pk=result["appointment_id"])
        self.assertEqual(appointment.notes, "")
        self.assertEqual(appointment.booked_price, Decimal("100.00"))
        self.assertEqual(read_encounter_revision(self.source)["content"], self.content)
        saved = read_encounter_revision(MedicalEncounterRevision.objects.get(pk=result["version_id"]))["content"]
        self.assertEqual(saved["plan_steps"][0]["teeth"], [11])
        self.assertEqual(saved["plan_steps"][0]["visit_step"]["id"], result["visit_step_id"])

    def test_existing_unscheduled_step_is_used_without_another_plan(self):
        plan = VisitPlan.objects.create(business=self.business, client=self.patient_client, responsible_user=self.doctor, created_by=self.doctor)
        step = VisitPlanStep.objects.create(plan=plan, service=self.service, resource=self.staff, branch=self.first, position=1)
        self.content["plan_steps"][0]["visit_step"] = visit_step_snapshot(step)
        fixtures.PrimaryEncounterDraftTests.save(self, content=self.content, expected_revision=2, idempotency_key="link-first")
        result = self.book(expected_revision=3, expected_plan_revision=1)
        self.assertEqual((result["plan_id"], result["visit_step_id"]), (plan.pk, step.pk))
        self.assertEqual(VisitPlan.objects.count(), 1)

    def test_stale_price_revision_and_unconfirmed_requests_have_no_side_effects(self):
        for overrides, error in [({"expected_price": Decimal("99")}, InvalidTransition),
                ({"expected_revision": 1}, InvalidTransition), ({"confirmed": False}, ValidationError)]:
            with self.subTest(overrides=overrides), self.assertRaises(error):
                self.book(**overrides)
        self.assertFalse(VisitPlan.objects.exists())
        self.assertEqual(Appointment.objects.count(), 1)

    def test_overlap_rolls_back_new_plan_and_medical_link(self):
        Appointment.objects.create(business=self.business, client=self.patient_client, service=self.service,
            resource=self.staff, branch=self.first, start_at=self.start, end_at=self.start + timedelta(minutes=30))
        with self.assertRaises(ScheduleConflict):
            self.book()
        self.assertFalse(VisitPlan.objects.exists())
        self.assertFalse(MedicalPlanStepLink.objects.exists())

    def test_late_medical_audit_failure_rolls_back_booking_and_index(self):
        effects = (BusinessEvent.objects.count(), Notification.objects.count())
        original = MedicalAuditEvent.objects.create
        def fail_saved(**kwargs):
            if kwargs.get("action") == "encounter_draft_saved":
                raise DatabaseError("synthetic audit failure")
            return original(**kwargs)
        with patch("apps.medical.audit.MedicalAuditEvent.objects.create", side_effect=fail_saved):
            with self.assertRaises(MedicalAuditUnavailable):
                self.book()
        self.assertFalse(VisitPlan.objects.exists())
        self.assertFalse(MedicalPlanStepLink.objects.exists())
        self.assertEqual((Appointment.objects.count(), MedicalEncounterRevision.objects.count()), (1, 2))
        self.assertEqual((BusinessEvent.objects.count(), Notification.objects.count()), effects)

    def test_changed_payload_and_second_booking_cannot_duplicate_appointment(self):
        self.book()
        with self.assertRaises(CRMCommandConflict):
            self.book(start_at=self.start + timedelta(hours=1))
        with self.assertRaises(InvalidTransition):
            self.book(idempotency_key="another-command")
        self.assertEqual((Appointment.objects.count(), VisitPlan.objects.count()), (2, 1))

    def test_current_crm_and_medical_revocation_each_block_replay(self):
        self.book()
        permission = RolePermission.objects.get(business_role=self.booking_role, resource="appointments", action="create")
        permission.is_allowed = False; permission.save(update_fields=["is_allowed"])
        with self.assertRaises(PermissionDenied):
            self.book()
        permission.is_allowed = True; permission.save(update_fields=["is_allowed"])
        self.assignment.branches.clear()
        with self.assertRaises(PermissionDenied):
            self.book()
        self.assertEqual(Appointment.objects.count(), 2)

    def test_foreign_service_and_owner_cannot_book_medical_step(self):
        other = Business.objects.create(owner=self.owner, name="Other", slug="other-med-booking")
        service = Service.objects.create(business=other, name="Foreign private service")
        for overrides in ({"service_id": service.pk}, {"actor": self.owner}):
            with self.subTest(overrides=overrides), self.assertRaises(PermissionDenied):
                self.book(**overrides)
        self.assertFalse(VisitPlan.objects.exists())

    def test_private_api_replay_and_correction_scope_rejection(self):
        api = APIClient(); api.force_authenticate(self.doctor)
        payload = dict(business_id=self.business.pk, patient_id=self.patient.pk, expected_revision=2,
            step_id=self.step_id, service_id=self.service.pk, resource_id=self.staff.pk, branch_id=self.first.pk,
            start_at=self.start.isoformat(), expected_price="100.00", expected_duration_minutes=30, confirmed=True)
        url = f"/api/medical/encounters/{self.encounter_record.pk}/book-plan-step/"
        response = api.post(url, payload, format="json", HTTP_IDEMPOTENCY_KEY="api-book")
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(response["Cache-Control"], "no-store, private")
        self.assertEqual(api.post(url, payload, format="json", HTTP_IDEMPOTENCY_KEY="api-book").status_code, 200)
        self.assertEqual(api.post(url, payload | {"correction_access_id": 1}, format="json", HTTP_IDEMPOTENCY_KEY="correction-book").status_code, 400)
