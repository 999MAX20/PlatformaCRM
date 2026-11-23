from datetime import time, timedelta
from unittest.mock import patch

from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.test import APIClient

from apps.businesses.models import RolePermission, Business, BusinessRole
from apps.core.domain_errors import InvalidTransition, ScheduleConflict
from apps.core.models import AuditLog, CRMCommandIdempotency
from apps.scheduling.availability import business_zone
from apps.scheduling.models import Appointment, WorkingHours, Resource
from apps.scheduling.record_commands import create_record
from . import tests_encounter_services as fixtures
from .actual_visit_services import create_actual_visit, actual_visit_context, actual_visit_evidence
from .audit import MedicalAuditUnavailable
from .models import MedicalActualVisit
from .tests_patient_services import key


@override_settings(MEDICAL_DATA_KEYS={"test": key(7)}, MEDICAL_DATA_ACTIVE_KEY_ID="test",
                   MEDICAL_IDENTITY_INDEX_KEY=key(8))
class ActualVisitTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        fixtures.PrimaryEncounterDraftTests.setUpTestData.__func__(cls)
        cls.first.uses_business_defaults = True
        cls.first.save(update_fields=["uses_business_defaults"])
        cls.booking_role = BusinessRole.objects.create(business=cls.business, name="Actual visit booking role")
        cls.member.business_role = cls.booking_role
        cls.member.save(update_fields=["business_role"])
        for resource, action, scope in [("clients", "view", "all"), ("appointments", "view", "own"),
                ("appointments", "create", "own"), ("appointments", "update", "own")]:
            RolePermission.objects.create(business_role=cls.booking_role, resource=resource, action=action, scope=scope, is_allowed=True)
        RolePermission.objects.create(business_role=cls.role, resource="medical_records", action="create", scope="own", is_allowed=True)

    def setUp(self):
        fixtures.PrimaryEncounterDraftTests.setUp(self)
        RolePermission.objects.create(business_role=self.role, resource="medical_patients", action="create", scope="own", is_allowed=True)
        self.now = (timezone.now() + timedelta(days=1)).astimezone(business_zone(self.business)).replace(hour=12, minute=30, second=0, microsecond=0)
        clock = patch("django.utils.timezone.now", return_value=self.now)
        clock.start(); self.addCleanup(clock.stop)
        for day in range(7):
            WorkingHours.objects.create(business=self.business, weekday=day, start_time=time(8), end_time=time(20))
        self.start = self.now - timedelta(minutes=30)

    def create(self, **changes):
        return create_actual_visit(**(dict(actor=self.doctor, business_id=self.business.pk,
            client_id=self.patient.client_id, branch_id=self.first.pk, service_id=self.service.pk,
            resource_id=self.staff.pk, start_at=self.start, expected_patient_revision=self.patient.revision,
            expected_price=self.service.price_from, expected_duration_minutes=self.service.duration_minutes,
            idempotency_key="actual", reason="Private synthetic explanation") | changes))

    def test_current_day_actual_visit_replay_encrypted_reason_and_original_booking_preserved(self):
        before = self.appointment.updated_at
        result = self.create()
        self.assertFalse(result["replayed"])
        self.assertEqual(self.create()["id"], result["id"])
        self.assertTrue(self.create()["replayed"])
        item = MedicalActualVisit.objects.get()
        self.assertEqual(item.appointment.start_at, self.start)
        self.assertEqual(actual_visit_evidence(item)["reason"], "Private synthetic explanation")
        self.assertNotIn("Private synthetic", item.evidence_encrypted)
        self.assertNotIn("Private synthetic", str(list(AuditLog.objects.values("metadata"))))
        self.assertNotIn("Private synthetic", str(list(CRMCommandIdempotency.objects.values("response_json", "request_hash"))))
        self.appointment.refresh_from_db()
        self.assertEqual(self.appointment.updated_at, before)

    def test_future_mode_unchanged_and_actual_mode_cannot_record_future(self):
        with self.assertRaises(ValidationError):
            self.create(start_at=self.now + timedelta(hours=1))
        with self.assertRaises(ValidationError):
            create_record(business=self.business, actor=self.doctor, client=self.patient.client,
                service=self.service, resource=self.staff, branch=self.first, start_at=self.start)
        self.assertFalse(MedicalActualVisit.objects.exists())

    def test_earlier_date_requires_head_and_explanation(self):
        earlier = self.start - timedelta(days=1)
        with self.assertRaises(PermissionDenied):
            self.create(start_at=earlier)
        self.assignment.kind = "head"
        self.assignment.save(update_fields=["kind"])
        with self.assertRaises(ValidationError):
            self.create(start_at=earlier, reason="")
        result = self.create(start_at=earlier)
        self.assertEqual(Appointment.objects.get(pk=result["id"]).start_at, earlier)

    def test_role_branch_foreign_reference_revocation_and_stale_patient(self):
        with self.assertRaises(PermissionDenied):
            self.create(actor=self.owner)
        other = Business.objects.create(owner=self.owner, name="Other actual-visit clinic")
        foreign = Resource.objects.create(business=other, name="Other clinician", linked_user=self.doctor)
        with self.assertRaises(PermissionDenied):
            self.create(resource_id=foreign.pk)
        with self.assertRaises(InvalidTransition):
            self.create(expected_patient_revision=999)
        self.assignment.branches.clear()
        with self.assertRaises(PermissionDenied):
            self.create()
        self.assignment.branches.add(self.first)
        self.create()
        RolePermission.objects.filter(business_role=self.role, resource="medical_patients", action="create").update(is_allowed=False)
        with self.assertRaises(PermissionDenied):
            self.create()

    def test_overlap_and_outside_hours_not_overridden_by_medical_mode(self):
        self.create()
        with self.assertRaises(ScheduleConflict):
            self.create(idempotency_key="overlap")
        with self.assertRaises(ScheduleConflict):
            self.create(start_at=self.start.replace(hour=7), idempotency_key="outside")
        self.assertEqual(MedicalActualVisit.objects.count(), 1)

    def test_audit_failure_rolls_back_booking_and_actual_evidence(self):
        count = Appointment.objects.count()
        with patch("apps.medical.actual_visit_services.write_patient_audit", side_effect=MedicalAuditUnavailable()), self.assertRaises(MedicalAuditUnavailable):
            self.create()
        self.assertEqual(Appointment.objects.count(), count)
        self.assertFalse(MedicalActualVisit.objects.exists())

    def test_private_http_context_and_creation(self):
        api = APIClient(); api.force_authenticate(self.doctor)
        scope = {"business_id": self.business.pk, "client_id": self.patient.client_id, "branch_id": self.first.pk}
        response = api.get("/api/medical/encounters/actual-context/", scope)
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data["resource_ids"], [self.staff.pk])
        self.assertFalse(response.data["earlier_allowed"])
        self.assertEqual(response["Cache-Control"], "no-store, private")
        response = api.post("/api/medical/encounters/actual-visit/", scope | {"service_id": self.service.pk,
            "resource_id": self.staff.pk, "start_at": self.start.isoformat(), "expected_patient_revision": self.patient.revision,
            "expected_price": self.service.price_from, "expected_duration_minutes": self.service.duration_minutes},
            format="json", HTTP_IDEMPOTENCY_KEY="http-actual")
        self.assertEqual(response.status_code, 201, response.data)

    def test_encounter_uses_actual_start_and_keeps_recording_time(self):
        from .encounter_services import open_primary_encounter
        result = self.create()
        appointment = Appointment.objects.get(pk=result["id"])
        version, _ = open_primary_encounter(actor=self.doctor, business_id=self.business.pk, patient_id=self.patient.pk,
            record_id=self.record.pk, appointment_id=appointment.pk, expected_patient_revision=self.patient.revision,
            expected_appointment_updated_at=appointment.updated_at, idempotency_key="actual-encounter")
        self.assertEqual(version.encounter.started_at, self.start)
        self.assertEqual(MedicalActualVisit.objects.get().recorded_at, self.now)

    def test_reception_can_record_today_but_cannot_backdate(self):
        from django.contrib.auth import get_user_model
        from apps.branches.models import BranchAccess
        from apps.businesses.models import BusinessMember
        from .models import MedicalRoleAssignment
        reception = get_user_model().objects.create_user(username="actual-reception", email="actual-reception@example.test")
        member = BusinessMember.objects.create(business=self.business, user=reception, role="admin")
        BranchAccess.objects.create(member=member, all_branches=True)
        role = BusinessRole.objects.create(business=self.business, name="Actual reception")
        assignment = MedicalRoleAssignment.objects.create(member=member, business_role=role, kind="reception", granted_by=self.owner)
        assignment.branches.add(self.first)
        RolePermission.objects.create(business_role=role, resource="medical_patients", action="create", scope="business", is_allowed=True)
        with self.assertRaises(PermissionDenied):
            self.create(actor=reception, start_at=self.start - timedelta(days=1))
        self.create(actor=reception)
        self.assertEqual(MedicalActualVisit.objects.get().recorded_by, reception)

    def test_changed_proof_binding_blocks_clinical_open_atomically(self):
        from .encounter_services import open_primary_encounter
        from .identity_crypto import MedicalDataUnavailable
        from .models import MedicalEncounter
        result = self.create()
        appointment = Appointment.objects.get(pk=result["id"])
        MedicalActualVisit.objects.filter(appointment=appointment).update(started_at=self.start - timedelta(minutes=1))
        with self.assertRaises(MedicalDataUnavailable):
            open_primary_encounter(actor=self.doctor, business_id=self.business.pk, patient_id=self.patient.pk,
                record_id=self.record.pk, appointment_id=appointment.pk, expected_patient_revision=self.patient.revision,
                expected_appointment_updated_at=appointment.updated_at, idempotency_key="tampered-actual")
        self.assertFalse(MedicalEncounter.objects.filter(appointment=appointment).exists())
