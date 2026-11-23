from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from apps.branches.models import Branch, BranchAccess
from apps.businesses.models import Business, RolePermission
from apps.core.models import AuditLog
from .models import MedicalAuditEvent
from . import tests_reception_transfer as fixtures
from .tests_reception_claims import reception_member
from .tests_patient_services import key


@override_settings(MEDICAL_DATA_KEYS={"test": key(7)}, MEDICAL_DATA_ACTIVE_KEY_ID="test",
                   MEDICAL_IDENTITY_INDEX_KEY=key(8))
class ReceptionHandoverReadTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        fixtures.ReceptionTransferTests.setUpTestData.__func__(cls)

    request = fixtures.ReceptionTransferTests.request
    claim = fixtures.ReceptionTransferTests.claim
    transfer = fixtures.ReceptionTransferTests.transfer

    def setUp(self):
        fixtures.ReceptionTransferTests.setUp(self)
        self.api = APIClient()
        self.api.force_authenticate(self.reception)
        self.root = f"/api/reception/booking-requests/{self.item.pk}/"
        self.scope = {"business_id": self.business.pk}

    def read(self, path, **params):
        return self.api.get(self.root + path + "/", self.scope | params)

    def test_recipients_search_pagination_minimal_projection(self):
        _, other, _ = reception_member(self.business, self.owner, self.first, "handover-third")
        other.user.full_name = "Synthetic Handover Display"
        other.user.save(update_fields=["full_name"])
        first = self.read("recipients", limit=1)
        self.assertEqual(first.status_code, 200, first.data)
        self.assertEqual(first.data["results"], [{"id": self.colleague_member.pk, "name": self.colleague.email}])
        second = self.read("recipients", limit=1, offset=first.data["next_offset"])
        self.assertEqual([row["id"] for row in second.data["results"]], [other.pk])
        self.assertIsNone(second.data["next_offset"])
        search = self.read("recipients", search="handover-third")
        self.assertEqual([row["id"] for row in search.data["results"]], [other.pk])
        self.assertEqual(self.read("recipients", search=self.colleague.email).data["results"], first.data["results"])
        self.assertEqual(self.read("recipients", search="Handover Display").data["results"],
            [{"id": other.pk, "name": "Synthetic Handover Display"}])
        self.assertEqual(first["Cache-Control"], "no-store, private")
        self.assertTrue(MedicalAuditEvent.objects.filter(patient=self.patient, action="read").exists())

    def test_recipients_exclude_unavailable_targets_and_foreign_business(self):
        other = Business.objects.create(owner=self.owner, name="Synthetic foreign handover", slug="handover-other")
        branch = Branch.objects.create(business=other, name="Synthetic foreign")
        reception_member(other, self.owner, branch, "foreign-handover")
        self.colleague_assignment.branches.clear()
        self.assertEqual(self.read("recipients").data["results"], [])
        self.colleague_assignment.branches.add(self.first)
        BranchAccess.objects.filter(member=self.colleague_member).update(all_branches=False)
        self.assertEqual(self.read("recipients").data["results"], [])
        BranchAccess.objects.filter(member=self.colleague_member).update(all_branches=True)
        RolePermission.objects.filter(business_role=self.colleague_member.business_role,
            resource="clients", action="view").update(scope="own")
        self.assertEqual(self.read("recipients").data["results"], [])
        RolePermission.objects.filter(business_role=self.colleague_member.business_role,
            resource="clients", action="view").update(scope="business")
        self.colleague_assignment.revoked_at = timezone.now()
        self.colleague_assignment.save(update_fields=["revoked_at"])
        self.assertEqual(self.read("recipients").data["results"], [])

    def test_current_caller_scope_and_strict_query(self):
        for actor in (self.doctor, self.owner, self.colleague, None):
            self.api.force_authenticate(actor)
            response = self.read("recipients")
            self.assertEqual(response.status_code, 401 if actor is None else 403)
        self.api.force_authenticate(self.reception)
        for query in ({"limit": 51}, {"offset": -1}, {"search": "x" * 121}, {"unknown": "x"}):
            self.assertEqual(self.read("recipients", **query).status_code, 400)
        other = Business.objects.create(owner=self.owner, name="Synthetic foreign read", slug="foreign-read")
        for path in ("recipients", "history"):
            self.assertEqual(self.read(path, business_id=other.pk).status_code, 403)
        self.reception_assignment.branches.clear()
        for path in ("recipients", "history"):
            response = self.read(path)
            self.assertEqual(response.status_code, 403)
            self.assertEqual(response["Cache-Control"], "no-store, private")

    def test_history_has_no_other_entity_or_tenant_data_and_read_only_actor_cannot_transfer(self):
        other = Business.objects.create(owner=self.owner, name="Synthetic audit other", slug="handover-audit-other")
        for business, entity, kind in ((other, str(self.item.pk), "medical_follow_up_requested"),
                (self.business, "999999", "medical_follow_up_requested"),
                (self.business, str(self.item.pk), "unrelated_sensitive_event")):
            AuditLog.objects.create(business=business, actor=self.owner, action="update",
                entity_type="ReceptionBookingRequest", entity_id=entity, metadata={"kind": kind, "private": "not visible"})
        history = self.read("history")
        self.assertEqual(history.status_code, 200, history.data)
        self.assertEqual([row["kind"] for row in history.data["results"]],
            ["medical_follow_up_claimed", "medical_follow_up_requested"])
        self.assertEqual(self.read("history", unknown="x").status_code, 400)
        RolePermission.objects.filter(business_role=self.reception_member.business_role,
            resource="medical_patients", action="update").update(is_allowed=False)
        self.assertEqual(self.read("history").status_code, 200)
        self.assertEqual(self.read("recipients").status_code, 403)
        queue = self.api.get("/api/reception/booking-requests/", self.scope | {"branch_id": self.first.pk})
        self.assertEqual(queue.status_code, 200, queue.data)
        self.assertFalse(queue.data["results"][0]["actions"]["transfer"])
        RolePermission.objects.filter(business_role=self.reception_member.business_role,
            resource="clients", action="view").update(scope="own")
        self.assertEqual(self.read("history").status_code, 403)

    def test_history_whitelist_pagination_and_current_read_access(self):
        self.reception.full_name = "Synthetic Sender"
        self.reception.save(update_fields=["full_name"])
        self.transfer()
        event = AuditLog.objects.get(entity_type="ReceptionBookingRequest", metadata__kind="medical_follow_up_transferred")
        event.metadata["private_debug"] = "must not appear"
        event.save(update_fields=["metadata"])
        response = self.read("history", limit=1)
        self.assertEqual(response.status_code, 200, response.data)
        row = response.data["results"][0]
        self.assertEqual(set(row), {"id", "created_at", "kind", "actor_name", "from_name", "to_name", "reason"})
        self.assertEqual(row["reason"], "Synthetic shift handover")
        self.assertEqual((row["from_name"], row["to_name"]), ("Synthetic Sender", self.colleague.email))
        self.assertEqual(row["actor_name"], "Synthetic Sender")
        second = self.read("history", limit=1, offset=response.data["next_offset"])
        self.assertEqual(second.data["results"][0]["kind"], "medical_follow_up_claimed")
        third = self.read("history", limit=1, offset=second.data["next_offset"])
        self.assertEqual(third.data["results"][0]["kind"], "medical_follow_up_requested")
        self.assertIsNone(third.data["next_offset"])
        self.assertEqual(self.read("recipients").status_code, 403)
        self.api.force_authenticate(self.colleague)
        self.assertEqual(self.read("history").status_code, 200)
        self.colleague_assignment.revoked_at = timezone.now()
        self.colleague_assignment.save(update_fields=["revoked_at"])
        self.assertEqual(self.read("history").status_code, 403)
