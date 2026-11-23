from datetime import timedelta

from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from apps.businesses.models import Business, RolePermission
from apps.clients.models import Client
from apps.scheduling.models import Appointment
from .models import MedicalAuditEvent
from . import tests_reception_link as fixtures
from .tests_patient_services import key


@override_settings(MEDICAL_DATA_KEYS={"test": key(7)}, MEDICAL_DATA_ACTIVE_KEY_ID="test",
                   MEDICAL_IDENTITY_INDEX_KEY=key(8))
class ReceptionCandidateTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        fixtures.ReceptionLinkTests.setUpTestData.__func__(cls)

    request = fixtures.ReceptionLinkTests.request
    claim = fixtures.ReceptionLinkTests.claim

    def setUp(self):
        fixtures.ReceptionLinkTests.setUp(self)
        self.api = APIClient()
        self.api.force_authenticate(self.reception)
        self.url = f"/api/reception/booking-requests/{self.item.pk}/candidates/"
        self.scope = {"business_id": self.business.pk}

    def test_matching_projection_pagination_and_linked_exclusion(self):
        second = Appointment.objects.create(business=self.business, client=self.patient.client, service=self.service,
            branch=self.first, resource=self.staff, start_at=self.start + timedelta(days=1),
            end_at=self.start + timedelta(days=1, minutes=30), responsible_user=self.reception)
        response = self.api.get(self.url, self.scope | {"limit": 1})
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response["Cache-Control"], "no-store, private")
        self.assertEqual([row["id"] for row in response.data["results"]], [self.existing.pk])
        self.assertEqual(set(response.data["results"][0]), {"id", "start_at", "end_at", "updated_at", "resource_name"})
        next_page = self.api.get(self.url, self.scope | {"limit": 1, "offset": response.data["next_offset"]})
        self.assertEqual([row["id"] for row in next_page.data["results"]], [second.pk])
        self.assertIsNone(next_page.data["next_offset"])
        self.assertTrue(MedicalAuditEvent.objects.filter(patient=self.patient, action="read").exists())
        fixtures.ReceptionLinkTests.link(self)
        self.assertEqual(self.api.get(self.url, self.scope).data["results"], [])
        self.item, _ = self.request(idempotency_key="candidate-next-request")
        self.claim(idempotency_key="candidate-next-claim")
        next_request = self.api.get(f"/api/reception/booking-requests/{self.item.pk}/candidates/", self.scope)
        self.assertEqual([row["id"] for row in next_request.data["results"]], [second.pk])
        self.assertEqual(Appointment.objects.count(), 3)

    def test_excludes_nonmatching_cancelled_past_archived_and_foreign_candidates(self):
        other = Business.objects.create(name="Synthetic candidate foreign", owner=self.owner)
        client = Client.objects.create(business=self.business, full_name="Synthetic other candidate")
        for changes in ({"client": client}, {"branch": self.second}, {"status": "cancelled"},
                        {"is_archived": True}, {"start_at": timezone.now() - timedelta(days=1)}, {"business": other}):
            with self.subTest(changes=changes):
                Appointment.objects.filter(pk=self.existing.pk).update(**changes)
                self.assertEqual(self.api.get(self.url, self.scope).data["results"], [])
                Appointment.objects.filter(pk=self.existing.pk).update(business=self.business, client=self.patient.client,
                    branch=self.first, status="created", is_archived=False, start_at=self.start)

    def test_current_assignee_role_branch_and_calendar_scope_are_enforced(self):
        for actor in (self.doctor, self.owner, self.colleague):
            self.api.force_authenticate(actor)
            self.assertEqual(self.api.get(self.url, self.scope).status_code, 403)
        self.api.force_authenticate(self.reception)
        other = Business.objects.create(name="Synthetic wrong request tenant", owner=self.owner)
        self.assertEqual(self.api.get(self.url, {"business_id": other.pk}).status_code, 403)
        permission = RolePermission.objects.get(business_role=self.reception_member.business_role,
            resource="appointments", action="update")
        permission.scope = "own"
        permission.save(update_fields=["scope"])
        Appointment.objects.filter(pk=self.existing.pk).update(responsible_user=self.doctor)
        self.assertEqual(self.api.get(self.url, self.scope).data["results"], [])
        permission.is_allowed = False
        permission.save(update_fields=["is_allowed"])
        self.assertEqual(self.api.get(self.url, self.scope).status_code, 403)
        permission.is_allowed = True
        permission.save(update_fields=["is_allowed"])
        self.reception_assignment.branches.remove(self.first)
        response = self.api.get(self.url, self.scope)
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response["Cache-Control"], "no-store, private")

    def test_strict_pagination_and_anonymous(self):
        for changes in ({"limit": 51}, {"offset": -1}, {"patient_id": self.patient.pk}):
            self.assertEqual(self.api.get(self.url, self.scope | changes).status_code, 400)
        self.api.force_authenticate(None)
        self.assertIn(self.api.get(self.url, self.scope).status_code, (401, 403))
