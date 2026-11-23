from unittest.mock import patch

from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from apps.businesses.models import Business, RolePermission
from . import tests_order_services as fixtures
from . import tests_patient_services as crypto_fixtures
from .audit import MedicalAuditUnavailable
from .models import MedicalOrderRevision, TreatmentParticipation


@override_settings(MEDICAL_DATA_KEYS={"test": crypto_fixtures.key(7)}, MEDICAL_DATA_ACTIVE_KEY_ID="test",
                   MEDICAL_IDENTITY_INDEX_KEY=crypto_fixtures.key(8))
class OrderAPITests(TestCase):
    @classmethod
    def setUpTestData(cls):
        fixtures.OrderServiceTests.setUpTestData.__func__(cls)

    def setUp(self):
        fixtures.OrderServiceTests.setUp(self)
        self.api = APIClient()
        self.api.force_authenticate(self.doctor)
        self.root = "/api/medical/orders/"
        self.scope = dict(business_id=self.business.pk, patient_id=self.patient.pk, appointment_id=self.appointment.pk)
        self.payload = dict(business_id=self.business.pk, patient_id=self.patient.pk,
            encounter_id=self.encounter_record.pk, expected_encounter_revision=1,
            expected_patient_revision=self.patient.revision,
            content={"kind": "medication", "text": "Literal <script> synthetic", "medication": {"dose": "Synthetic dose"}})

    def private(self, response):
        self.assertEqual(response["Cache-Control"], "no-store, private")
        self.assertEqual(response["Pragma"], "no-cache")
        return response

    def command(self, path="", payload=None, key="order"):
        return self.private(self.api.post(self.root + path, self.payload if payload is None else payload,
            format="json", HTTP_IDEMPOTENCY_KEY=key))

    def read(self, path="", **overrides):
        return self.private(self.api.get(self.root + path, self.scope | overrides))

    def test_create_update_paginated_history_and_exact_version(self):
        created = self.command()
        self.assertEqual(created.status_code, 201, created.data)
        first = created.data
        self.assertTrue(self.command().data["replayed"])
        self.assertEqual(self.read(f"versions/{first['version_id']}/").data["content"], self.payload["content"])
        updated = self.command(f"{first['id']}/draft/", self.payload | dict(expected_order_revision=1,
            content={"kind": "other", "text": "Synthetic updated", "medication": {}}), "update")
        self.assertEqual(updated.status_code, 200, updated.data)
        self.assertEqual(updated.data["revision"], 2)
        page = self.read(encounter_id=self.encounter_record.pk)
        self.assertEqual(page.data["results"][0]["version_id"], updated.data["version_id"])
        history = self.read(f"{first['id']}/revisions/", limit=1)
        self.assertEqual(history.data["next_before_revision"], 2)
        self.assertEqual(self.read(f"{first['id']}/revisions/", before_revision=2).data["results"][0]["version_id"], first["version_id"])
        self.assertEqual(self.read(f"versions/{first['version_id']}/").data["content"], self.payload["content"])

    def test_participation_can_read_historical_orders_then_end_revokes_all_readers(self):
        first = self.command().data
        updated = self.command(f"{first['id']}/draft/", self.payload | dict(expected_order_revision=1,
            content={"kind": "other", "text": "Historical synthetic updated", "medication": {}}), "historical-update")
        self.assertEqual(updated.status_code, 200, updated.data)
        now = timezone.now()
        type(self.appointment).objects.filter(pk=self.appointment.pk).update(status="completed")
        type(self.encounter_record).objects.filter(pk=self.encounter_record.pk).update(state="finalized", ended_at=now,
            finalized_at=now, finalized_by=self.doctor)
        participation = TreatmentParticipation.objects.create(patient=self.patient, member=self.member,
            branch=self.first, proposed_by=self.owner, state="active", proposed_at=now, accepted_at=now)
        self.scope = dict(business_id=self.business.pk, patient_id=self.patient.pk, participation_id=participation.pk)
        access = self.read("workspace-access/", encounter_id=self.encounter_record.pk)
        self.assertEqual(access.status_code, 200, access.data)
        self.assertEqual(access.data["actions"], {"view": True, "create": False, "update": False})
        self.assertEqual(self.read(encounter_id=self.encounter_record.pk).data["results"][0]["revision"], 2)
        self.assertEqual(len(self.read(f"{first['id']}/revisions/").data["results"]), 2)
        self.assertEqual(self.read(f"versions/{first['version_id']}/").data["content"], self.payload["content"])
        participation.state, participation.closed_at, participation.closed_by = "ended", now, self.owner
        participation.save(update_fields=["state", "closed_at", "closed_by"])
        for path, params in (("", {"encounter_id": self.encounter_record.pk}),
                ("workspace-access/", {"encounter_id": self.encounter_record.pk}),
                (f"{first['id']}/revisions/", {}), (f"versions/{first['version_id']}/", {})):
            with self.subTest(path=path):
                self.assertEqual(self.read(path, **params).status_code, 403)

    def test_permission_and_branch_revocation_clear_list_version_and_replay(self):
        first = self.command().data
        access = self.read("workspace-access/", encounter_id=self.encounter_record.pk)
        self.assertTrue(access.data["actions"]["create"])
        self.assignment.branches.clear()
        for result in (self.read(encounter_id=self.encounter_record.pk),
                       self.read(f"versions/{first['version_id']}/"), self.command()):
            self.assertEqual(result.status_code, 403, result.data)
            self.assertNotIn("Synthetic dose", result.content.decode())

    def test_other_tenant_and_owner_without_medical_role_are_denied(self):
        other = Business.objects.create(name="Synthetic other tenant", owner=self.owner)
        self.assertEqual(self.command(payload=self.payload | {"business_id": other.pk}).status_code, 403)
        self.api.force_authenticate(self.owner)
        self.assertEqual(self.command().status_code, 403)
        self.assertEqual(MedicalOrderRevision.objects.count(), 0)

    def test_missing_prescription_right_is_not_replaced_by_record_right(self):
        RolePermission.objects.filter(business_role=self.role, resource="medical_prescriptions", action="create").delete()
        self.assertFalse(self.read("workspace-access/", encounter_id=self.encounter_record.pk).data["actions"]["create"])
        self.assertEqual(self.command().status_code, 403)
        RolePermission.objects.filter(business_role=self.role, resource="medical_prescriptions", action="view").delete()
        self.assertEqual(self.read(encounter_id=self.encounter_record.pk).status_code, 403)
        self.assertEqual(self.private(self.api.get("/api/medical/encounters/workspace/", self.scope)).status_code, 200)

    def test_invalid_stale_and_audit_failure_have_private_recoverable_responses(self):
        self.assertEqual(self.command(payload=self.payload | {"unexpected": "Synthetic"}).status_code, 400)
        self.assertEqual(self.command(payload=self.payload | {"expected_encounter_revision": 999}).status_code, 409)
        with patch("apps.medical.order_services.write_patient_audit", side_effect=MedicalAuditUnavailable):
            self.assertEqual(self.command().status_code, 503)
        self.assertEqual(MedicalOrderRevision.objects.count(), 0)
        self.assertEqual(self.command().status_code, 201)
