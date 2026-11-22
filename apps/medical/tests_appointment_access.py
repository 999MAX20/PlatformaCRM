from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied

from apps.branches.models import Branch, BranchAccess
from apps.businesses.models import Business, BusinessMember
from apps.clients.models import Client
from apps.scheduling.models import Appointment, AppointmentResource, Resource
from apps.services.models import Service
from .appointment_access import assert_appointment_medical_basis
from .models import MedicalRoleAssignment, PatientProfile
from . import tests_role_access as role_fixtures


class AppointmentMedicalBasisTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        role_fixtures.MedicalRoleAccessTests.setUpTestData.__func__(cls)
        cls.patient_client = Client.objects.create(business=cls.business, full_name="Synthetic patient")
        cls.patient = PatientProfile.objects.create(business=cls.business, client=cls.patient_client, created_by=cls.owner)
        cls.service = Service.objects.create(business=cls.business, name="Synthetic service")
        cls.staff = Resource.objects.create(business=cls.business, name="Specialist", linked_user=cls.doctor)
        cls.appointment = Appointment.objects.create(business=cls.business, branch=cls.first,
            client=cls.patient_client, service=cls.service, resource=cls.staff,
            start_at=timezone.now() + timedelta(days=90), end_at=timezone.now() + timedelta(days=90, hours=1))

    def basis(self, **overrides):
        return assert_appointment_medical_basis(**dict(actor=self.doctor, business=self.business,
            patient_id=self.patient.pk, appointment_id=self.appointment.pk) | overrides)

    def test_future_booking_gives_immediate_basis_without_24_hour_cutoff(self):
        result = self.basis()
        self.assertEqual((result.patient_id, result.appointment_id, result.branch_id, result.assignment_id),
                         (self.patient.pk, self.appointment.pk, self.first.pk, self.assignment.pk))
        self.assertFalse(hasattr(result, "demographics"))

    def test_current_and_rescheduled_booking_use_current_crm_status_contract(self):
        for status in ("created", "confirmed", "rescheduled"):
            with self.subTest(status=status):
                Appointment.objects.filter(pk=self.appointment.pk).update(status=status,
                    start_at=timezone.now() - timedelta(minutes=10), end_at=timezone.now() + timedelta(minutes=20))
                self.basis()

    def test_terminal_or_archived_appointment_does_not_leave_access(self):
        for values in ({"status": "completed"}, {"status": "cancelled"}, {"status": "no_show"},
                       {"status": "unknown"}, {"status": "created", "is_archived": True}):
            with self.subTest(values=values):
                Appointment.objects.filter(pk=self.appointment.pk).update(**values)
                with self.assertRaises(PermissionDenied):
                    self.basis()

    def test_reassignment_removes_only_this_basis_and_old_objects_do_not_restore_it(self):
        self.basis()
        other = Resource.objects.create(business=self.business, name="Other specialist")
        Appointment.objects.filter(pk=self.appointment.pk).update(resource=other)
        with self.assertRaises(PermissionDenied):
            self.basis()

    def test_responsible_user_and_physical_reservation_are_not_doctor_assignment(self):
        Appointment.objects.filter(pk=self.appointment.pk).update(resource=None, responsible_user=self.doctor)
        AppointmentResource.objects.create(appointment=self.appointment, resource=self.staff, resource_name="Malformed reservation")
        with self.assertRaises(PermissionDenied):
            self.basis()

    def test_wrong_resource_type_and_changed_account_link_are_rejected(self):
        for values in ({"resource_type": "room"}, {"resource_type": "staff", "linked_user": self.owner}):
            Resource.objects.filter(pk=self.staff.pk).update(**values)
            with self.subTest(values=values), self.assertRaises(PermissionDenied):
                self.basis()

    def test_specialist_booking_availability_is_not_account_revocation(self):
        Resource.objects.filter(pk=self.staff.pk).update(is_active=False)
        self.basis()
        get_user_model().objects.filter(pk=self.doctor.pk).update(is_active=False)
        with self.assertRaises(PermissionDenied):
            self.basis()

    def test_membership_and_medical_role_are_rechecked(self):
        BusinessMember.objects.filter(pk=self.member.pk).update(is_active=False)
        with self.assertRaises(PermissionDenied):
            self.basis()
        BusinessMember.objects.filter(pk=self.member.pk).update(is_active=True)
        MedicalRoleAssignment.objects.filter(pk=self.assignment.pk).update(revoked_at=timezone.now())
        with self.assertRaises(PermissionDenied):
            self.basis()

    def test_assistant_reception_and_owner_cannot_use_doctor_basis(self):
        for kind in ("assistant", "reception"):
            MedicalRoleAssignment.objects.filter(pk=self.assignment.pk).update(kind=kind)
            with self.subTest(kind=kind), self.assertRaises(PermissionDenied):
                self.basis()
        with self.assertRaises(PermissionDenied):
            self.basis(actor=self.owner)

    def test_medical_and_crm_branch_revocations_are_observed(self):
        self.assignment.branches.clear()
        with self.assertRaises(PermissionDenied):
            self.basis()
        self.assignment.branches.add(self.first)
        BranchAccess.objects.filter(pk=self.crm_grant.pk).update(all_branches=False)
        with self.assertRaises(PermissionDenied):
            self.basis()

    def test_missing_inactive_or_foreign_branch_does_not_supply_basis(self):
        Appointment.objects.filter(pk=self.appointment.pk).update(branch=None)
        with self.assertRaises(PermissionDenied):
            self.basis()
        Appointment.objects.filter(pk=self.appointment.pk).update(branch=self.first)
        Branch.objects.filter(pk=self.first.pk).update(is_active=False)
        with self.assertRaises(PermissionDenied):
            self.basis()

    def test_foreign_or_mismatched_patient_is_rejected(self):
        foreign = Business.objects.create(owner=self.owner, name="Foreign", slug="basis-foreign")
        other = Client.objects.create(business=self.business, full_name="Other patient")
        profile = PatientProfile.objects.create(business=self.business, client=other, created_by=self.owner)
        with self.assertRaises(PermissionDenied):
            self.basis(patient_id=profile.pk)
        PatientProfile.objects.filter(pk=self.patient.pk).update(business=foreign)
        with self.assertRaises(PermissionDenied):
            self.basis()

    def test_corrupt_tenant_links_cannot_open_medical_content(self):
        foreign = Business.objects.create(owner=self.owner, name="Foreign", slug="corrupt-basis")
        for model, entity in ((Client, self.patient_client), (Service, self.service), (Resource, self.staff),
                              (Branch, self.first), (Appointment, self.appointment)):
            with self.subTest(model=model.__name__):
                model.objects.filter(pk=entity.pk).update(business=foreign)
                with self.assertRaises(PermissionDenied):
                    self.basis()
                model.objects.filter(pk=entity.pk).update(business=self.business)

    def test_invalid_identifiers_and_interval_fail_closed(self):
        for overrides in ({"patient_id": True}, {"appointment_id": "1"}, {"appointment_id": 999999}):
            with self.subTest(overrides=overrides), self.assertRaises(PermissionDenied):
                self.basis(**overrides)
        Appointment.objects.filter(pk=self.appointment.pk).update(end_at=self.appointment.start_at)
        with self.assertRaises(PermissionDenied):
            self.basis()
