from datetime import timedelta

from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from apps.businesses.models import Business, RolePermission
from apps.scheduling.models import Appointment, Resource
from apps.services.models import Service
from .models import MedicalAuditEvent, ReceptionBookingRequest
from . import tests_reception_booking as fixtures
from .tests_patient_services import key


@override_settings(MEDICAL_DATA_KEYS={"test": key(7)}, MEDICAL_DATA_ACTIVE_KEY_ID="test",
                   MEDICAL_IDENTITY_INDEX_KEY=key(8))
class ReceptionAPITests(TestCase):
    @classmethod
    def setUpTestData(cls):
        fixtures.ReceptionBookingTests.setUpTestData.__func__(cls)

    def setUp(self):
        self.api = APIClient()
        self.api.force_authenticate(self.doctor)
        self.url = "/api/reception/booking-requests/"
        self.scope = {"business_id": self.business.pk, "branch_id": self.first.pk}
        day = timezone.localdate() + timedelta(days=7)
        self.data = {"business_id": self.business.pk, "patient_id": self.patient.pk,
            "encounter_id": self.encounter_record.pk, "expected_revision": 1,
            "service_id": self.service.pk, "preferred_resource_id": self.staff.pk,
            "recommended_from": day.isoformat(), "recommended_until": (day + timedelta(days=7)).isoformat(),
            "patient_in_clinic": True}

    def create(self):
        response = self.api.post(self.url, self.data, format="json", HTTP_IDEMPOTENCY_KEY="http-create")
        self.assertEqual(response.status_code, 201, response.data)
        return response.data["id"]

    def test_follow_up_catalog_without_calendar_or_settings_rights(self):
        self.assertFalse(RolePermission.objects.filter(business_role=self.member.business_role,
            resource__in=["appointments", "settings"], is_allowed=True).exists())
        scope = {"business_id": self.business.pk, "patient_id": self.patient.pk,
            "encounter_id": self.encounter_record.pk, "kind": "service", "limit": 1}
        for name in ("Catalog search A", "Catalog search B"):
            Service.objects.create(business=self.business, name=name)
        Service.objects.create(business=self.business, name="Catalog search inactive", is_active=False)
        Service.objects.create(business=self.business, name="Catalog search archived", is_archived=True)
        other = Business.objects.create(name="Synthetic foreign catalog", owner=self.owner)
        Service.objects.create(business=other, name="Catalog search foreign")
        response = self.api.get(self.url + "catalog/", scope | {"search": "Catalog search"})
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response["Cache-Control"], "no-store, private")
        self.assertEqual(response.data["results"], [{"id": Service.objects.get(name="Catalog search A").pk, "name": "Catalog search A"}])
        self.assertEqual(response.data["default"]["id"], self.service.pk)
        second = self.api.get(self.url + "catalog/", scope | {"search": "Catalog search", "offset": response.data["next_offset"]})
        self.assertEqual([row["name"] for row in second.data["results"]], ["Catalog search B"])
        self.assertIsNone(second.data["next_offset"])
        self.assertEqual(self.api.get(self.url + "catalog/", scope | {"kind": "staff"}).data["default"]["id"], self.staff.pk)
        self.assertTrue(MedicalAuditEvent.objects.filter(patient=self.patient, action="read").exists())
        self.assertEqual(ReceptionBookingRequest.objects.count(), 0)

    def test_follow_up_catalog_filters_staff_and_rechecks_medical_basis(self):
        scope = {"business_id": self.business.pk, "patient_id": self.patient.pk,
            "encounter_id": self.encounter_record.pk, "kind": "staff", "search": "Synthetic hidden"}
        for changes in ({"is_active": False}, {"archived_at": timezone.now()},
                        {"retired_at": timezone.now()}, {"resource_type": "room"}):
            Resource.objects.create(business=self.business, name="Synthetic hidden", **changes)
        foreign = Business.objects.create(name="Synthetic other staff", owner=self.owner)
        Resource.objects.create(business=foreign, name="Synthetic hidden foreign")
        response = self.api.get(self.url + "catalog/", scope)
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data["results"], [])
        for changes in ({"business_id": foreign.pk}, {"patient_id": 999999}):
            self.assertIn(self.api.get(self.url + "catalog/", scope | changes).status_code, [403, 404])
        self.assignment.revoked_at = timezone.now()
        self.assignment.save(update_fields=["revoked_at"])
        denied = self.api.get(self.url + "catalog/", scope)
        self.assertEqual(denied.status_code, 403)
        self.assertEqual(denied["Cache-Control"], "no-store, private")

    def test_doctor_to_reception_booking_flow_and_private_projection(self):
        identifier = self.create()
        primary = self.api.get(self.url + "primary/", {"business_id": self.business.pk,
            "patient_id": self.patient.pk, "encounter_id": self.encounter_record.pk})
        self.assertEqual(primary.status_code, 200, primary.data)
        self.assertEqual(primary.data["results"][0]["id"], identifier)
        self.assertFalse(any(primary.data["results"][0]["actions"].values()))
        self.api.force_authenticate(self.reception)
        queue = self.api.get(self.url, self.scope)
        self.assertEqual(queue.status_code, 200, queue.data)
        self.assertEqual(queue["Cache-Control"], "no-store, private")
        row = queue.data["results"][0]
        self.assertTrue(row["actions"]["claim"])
        self.assertFalse(row["actions"]["book"])
        self.assertEqual(row["client_name"], self.patient.client.full_name)
        self.assertFalse({"iin", "demographics", "content", "diagnoses", "medical_record"} & set(row))
        self.assertTrue(MedicalAuditEvent.objects.filter(patient=self.patient, action="read").exists())
        response = self.api.post(f"{self.url}{identifier}/claim/", {"business_id": self.business.pk,
            "expected_revision": 1}, format="json", HTTP_IDEMPOTENCY_KEY="http-claim")
        self.assertEqual(response.status_code, 200, response.data)
        start = (timezone.now() + timedelta(days=7)).replace(hour=10, minute=0, second=0, microsecond=0)
        payload = {"business_id": self.business.pk, "expected_revision": 2, "resource_id": self.staff.pk,
            "start_at": start.isoformat(), "expected_price": "100.00", "expected_duration_minutes": 30,
            "confirmed": True}
        booked = self.api.post(f"{self.url}{identifier}/book/", payload, format="json", HTTP_IDEMPOTENCY_KEY="http-book")
        self.assertEqual(booked.status_code, 200, booked.data)
        repeated = self.api.post(f"{self.url}{identifier}/book/", payload, format="json", HTTP_IDEMPOTENCY_KEY="http-book")
        self.assertTrue(repeated.data["replayed"])
        self.assertEqual(booked.data["appointment_id"], repeated.data["appointment_id"])
        self.assertEqual(Appointment.objects.count(), 2)
        RolePermission.objects.filter(business_role=self.reception_member.business_role,
            resource="appointments", action="view").update(is_allowed=False)
        hidden = self.api.get(self.url, self.scope).data["results"][0]
        self.assertIsNone(hidden["booked_appointment_id"])
        self.assertIsNone(hidden["appointment_status"])
        self.assertIsNone(hidden["appointment_start_at"])

    def test_invalid_fields_missing_key_and_anonymous_fail_without_mutation(self):
        for data in (self.data | {"state": "booked"}, self.data | {"diagnosis": "private"}):
            response = self.api.post(self.url, data, format="json", HTTP_IDEMPOTENCY_KEY="invalid")
            self.assertEqual(response.status_code, 400)
        self.assertEqual(self.api.post(self.url, self.data, format="json").status_code, 400)
        self.api.force_authenticate(None)
        response = self.api.get(self.url, self.scope)
        self.assertIn(response.status_code, (401, 403))
        self.assertEqual(response["Cache-Control"], "no-store, private")
        self.assertFalse(ReceptionBookingRequest.objects.exists())

    def test_reception_and_doctor_boundaries_and_revoked_role(self):
        self.create()
        self.assertEqual(self.api.get(self.url, self.scope).status_code, 403)
        self.api.force_authenticate(self.reception)
        self.assertEqual(self.api.post(self.url, self.data, format="json", HTTP_IDEMPOTENCY_KEY="reception-create").status_code, 403)
        self.reception_assignment.revoked_at = timezone.now()
        self.reception_assignment.save(update_fields=["revoked_at"])
        response = self.api.get(self.url, self.scope)
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response["Cache-Control"], "no-store, private")

    def test_foreign_branch_and_client_scope_never_enter_queue(self):
        self.create()
        self.api.force_authenticate(self.reception)
        self.assertEqual(self.api.get(self.url, self.scope | {"branch_id": self.second.pk}).status_code, 403)
        foreign = Business.objects.create(owner=self.owner, name="Foreign API", slug="foreign-reception-api")
        self.assertEqual(self.api.get(self.url, self.scope | {"business_id": foreign.pk}).status_code, 403)
        RolePermission.objects.filter(business_role=self.reception_member.business_role,
            resource="clients", action="view").update(scope="own")
        response = self.api.get(self.url, self.scope)
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data["results"], [])

    def test_read_only_reception_has_no_commands_and_pagination_is_bounded(self):
        self.create()
        self.api.force_authenticate(self.reception)
        RolePermission.objects.filter(business_role=self.reception_member.business_role,
            resource="medical_patients", action="update").update(is_allowed=False)
        response = self.api.get(self.url, self.scope | {"limit": 1})
        self.assertEqual(response.status_code, 200)
        self.assertFalse(any(response.data["results"][0]["actions"].values()))
        for query in ({"limit": 51}, {"offset": -1}, {"state": "unknown"}, {"diagnosis": "private"}):
            self.assertEqual(self.api.get(self.url, self.scope | query).status_code, 400)

    def test_existing_appointment_link_http_contract(self):
        identifier = self.create()
        self.api.force_authenticate(self.reception)
        RolePermission.objects.create(business_role=self.reception_member.business_role,
            resource="appointments", action="update", scope="business", is_allowed=True)
        claim = self.api.post(f"{self.url}{identifier}/claim/", {"business_id": self.business.pk,
            "expected_revision": 1}, format="json", HTTP_IDEMPOTENCY_KEY="link-claim")
        self.assertEqual(claim.status_code, 200)
        start = (timezone.now() + timedelta(days=7)).replace(hour=10, minute=0, second=0, microsecond=0)
        appointment = Appointment.objects.create(business=self.business, client=self.patient.client,
            service=self.service, resource=self.staff, branch=self.first,
            start_at=start, end_at=start + timedelta(minutes=30))
        response = self.api.post(f"{self.url}{identifier}/link/", {"business_id": self.business.pk,
            "expected_revision": 2, "appointment_id": appointment.pk,
            "expected_updated_at": appointment.updated_at.isoformat(), "confirmed": True},
            format="json", HTTP_IDEMPOTENCY_KEY="http-link")
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data["appointment_id"], appointment.pk)
        self.assertEqual(Appointment.objects.count(), 2)
