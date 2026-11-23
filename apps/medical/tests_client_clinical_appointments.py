from unittest.mock import patch

from django.db import DatabaseError
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework.exceptions import PermissionDenied

from apps.businesses.models import Business
from apps.clients.models import Client
from apps.scheduling.models import Appointment, Resource
from . import tests_appointment_access as fixtures
from .models import MedicalAuditEvent


class ClientClinicalAppointmentsTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        fixtures.AppointmentMedicalBasisTests.setUpTestData.__func__(cls)
        cls.member.role = "admin"
        cls.member.save(update_fields=["role"])

    def setUp(self):
        self.api = APIClient()
        self.api.force_authenticate(self.doctor)

    def read(self, **overrides):
        response = self.api.get("/api/medical/encounters/client-appointments/", {
            "business_id": self.business.pk, "branch_id": self.first.pk,
            "client_id": self.patient_client.pk} | overrides)
        self.assertEqual(response["Cache-Control"], "no-store, private")
        return response

    def test_future_own_appointment_is_immediately_available_without_profile_content(self):
        response = self.read()
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual([row["id"] for row in response.data["results"]], [self.appointment.pk])
        self.assertEqual(set(response.data["results"][0]), {"id", "start_at", "end_at"})
        self.assertIsNone(MedicalAuditEvent.objects.get().patient_id)

    def test_empty_result_does_not_resolve_or_disclose_medical_profile(self):
        self.appointment.delete()
        response = self.read()
        self.assertEqual(response.status_code, 200, response.data)
        self.patient.delete()
        self.assertEqual(self.read().data, response.data)
        self.assertEqual(response.data, {"results": [], "next_before_id": None})

    def test_valid_booking_without_profile_can_be_selected_for_existing_context_flow(self):
        self.patient.delete()
        response = self.read()
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data["results"][0]["id"], self.appointment.pk)

    def test_terminal_archived_other_branch_and_reassigned_bookings_are_excluded(self):
        for status in ("completed", "cancelled", "no_show"):
            Appointment.objects.filter(pk=self.appointment.pk).update(status=status)
            self.assertEqual(self.read().data["results"], [])
        Appointment.objects.filter(pk=self.appointment.pk).update(status="created", is_archived=True)
        self.assertEqual(self.read().data["results"], [])
        Appointment.objects.filter(pk=self.appointment.pk).update(is_archived=False, branch=self.second)
        self.assertEqual(self.read().data["results"], [])
        other = Resource.objects.create(business=self.business, name="Other")
        Appointment.objects.filter(pk=self.appointment.pk).update(branch=self.first, resource=other)
        self.assertEqual(self.read().data["results"], [])

    def test_cursor_is_bounded_and_does_not_repeat_rows(self):
        first_id = self.appointment.pk
        self.appointment.pk = None
        self.appointment.save()
        page = self.read(limit=1)
        self.assertEqual(page.status_code, 200, page.data)
        self.assertEqual(page.data["results"][0]["id"], self.appointment.pk)
        next_page = self.read(limit=1, before_id=page.data["next_before_id"])
        self.assertEqual(next_page.data["results"][0]["id"], first_id)
        self.assertIsNone(next_page.data["next_before_id"])

    def test_owner_assistant_revoked_role_and_branch_deny_without_audit(self):
        self.api.force_authenticate(self.owner)
        self.assertEqual(self.read().status_code, 403)
        self.api.force_authenticate(self.doctor)
        self.assignment.kind = "assistant"
        self.assignment.save(update_fields=["kind"])
        self.assertEqual(self.read().status_code, 403)
        self.assignment.kind, self.assignment.revoked_at = "doctor", timezone.now()
        self.assignment.save(update_fields=["kind", "revoked_at"])
        self.assertEqual(self.read().status_code, 403)
        self.assignment.revoked_at = None
        self.assignment.save(update_fields=["revoked_at"])
        self.assignment.branches.clear()
        self.assertEqual(self.read().status_code, 403)
        self.assertFalse(MedicalAuditEvent.objects.exists())

    def test_foreign_client_and_invalid_scope_are_rejected(self):
        other = Business.objects.create(owner=self.owner, name="Other", slug="client-entry-other")
        client = Client.objects.create(business=other, full_name="Foreign")
        self.assertEqual(self.read(client_id=client.pk).status_code, 404)
        self.assertEqual(self.read(limit=51).status_code, 400)
        self.assertEqual(self.read(patient_id=self.patient.pk).status_code, 400)
        self.assertEqual(self.read(branch_id=999999).status_code, 403)
        self.assertFalse(MedicalAuditEvent.objects.exists())

    def test_audit_failure_does_not_return_booking_identifiers(self):
        with patch("apps.medical.client_clinical_appointments.MedicalAuditEvent.objects.create", side_effect=DatabaseError("Synthetic")):
            response = self.read()
        self.assertEqual(response.status_code, 503)
        self.assertNotIn("results", response.data)

    def test_ordinary_client_access_is_still_required_and_archived_client_is_hidden(self):
        with patch("apps.medical.client_clinical_appointments.assert_can", side_effect=PermissionDenied):
            self.assertEqual(self.read().status_code, 403)
        self.patient_client.is_archived = True
        self.patient_client.save(update_fields=["is_archived"])
        self.assertEqual(self.read().status_code, 404)
        self.assertFalse(MedicalAuditEvent.objects.exists())
