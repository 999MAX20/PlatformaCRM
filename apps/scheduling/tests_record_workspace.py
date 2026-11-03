from datetime import timedelta

from django.test import TestCase

from apps.businesses.models import RolePermission
from apps.scheduling.models import Appointment
from apps.scheduling.tests_record_commands import RecordCommandTests


class RecordWorkspaceTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        RecordCommandTests.setUpTestData.__func__(cls)

    def setUp(self):
        RecordCommandTests.setUp(self)

    def record(self, **overrides):
        return Appointment.objects.create(business=self.business, client=self.client_record,
            service=self.service, resource=self.resource, start_at=self.start,
            end_at=self.start + timedelta(minutes=30), **overrides)

    def workspace(self, **params):
        return self.api.get("/api/appointments/workspace/", {"business": self.business.pk, **params})

    def test_card_does_not_invent_legacy_links_or_mix_other_client_tasks(self):
        from apps.tasks.models import Task
        from apps.activities.models import ActivityEvent

        record = self.record()
        unrelated = self.record()
        own = Task.objects.create(business=self.business, client=self.client_record,
            appointment=record, title="Record task", created_by=self.owner)
        Task.objects.create(business=self.business, client=self.client_record,
            appointment=unrelated, title="Other record task", created_by=self.owner)
        ActivityEvent.objects.create(business=self.business, client=self.client_record,
            entity_type="Appointment", entity_id=str(unrelated.pk), event_type="updated", text="Other record")
        response = self.api.get(f"/api/appointments/{record.pk}/crm-card/")
        self.assertEqual(response.status_code, 200, response.data)
        self.assertIsNone(response.data["lead"])
        self.assertIsNone(response.data["deal"])
        self.assertEqual([task["id"] for task in response.data["tasks"]], [own.pk])
        self.assertEqual(response.data["meta"]["related_counts"]["tasks"], 1)
        self.assertNotIn("Other record", [event["text"] for event in response.data["timeline"]])

    def test_pagination_and_pipeline_counts_are_not_page_totals(self):
        for _ in range(29):
            self.record()
        self.record(status="confirmed")
        self.record(status="rescheduled")
        self.record(status="completed")
        self.record(status="cancelled")
        self.record(status="no_show")
        self.record(is_archived=True)
        response = self.workspace(workflow="planned", page_size=10, page=2)
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data["count"], 31)
        self.assertEqual(len(response.data["results"]), 10)
        self.assertEqual(response.data["summary"], {"planned": 31, "completed": 1, "cancelled": 1, "no_show": 1})
        ids = [row["id"] for row in response.data["results"]]
        self.assertEqual(ids, sorted(ids))

    def test_search_responsible_confirmation_and_reverse_order(self):
        first = self.record(responsible_user=self.owner, status="confirmed")
        last = self.record(responsible_user=self.owner, status="confirmed")
        self.record(responsible_user=self.staff)
        response = self.workspace(q="Client", responsible_user=self.owner.pk, confirmed="true", ordering="-start_at")
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual([row["id"] for row in response.data["results"]], [last.pk, first.pk])
        self.assertEqual(response.data["summary"]["planned"], 2)
        self.assertEqual(self.workspace(q="not-found").data["count"], 0)

    def test_invalid_parameters_are_400_not_unfiltered_success(self):
        for params in ({"business": "bad"}, {"resource": "bad"}, {"responsible_user": -1},
                       {"workflow": "won"}, {"confirmed": "maybe"}, {"ordering": "client__phone"},
                       {"start_from": "bad"}, {"start_from": "2026-12-03", "start_to": "2026-12-02"},
                       {"page_size": 101}, {"page": 0}):
            with self.subTest(params=params):
                self.assertEqual(self.workspace(**params).status_code, 400)
        self.assertEqual(self.api.get("/api/appointments/workspace/").status_code, 400)

    def test_business_day_boundaries_and_current_object_scope(self):
        self.business.timezone = "Asia/Qyzylorda"
        self.business.save(update_fields=["timezone"])
        self.start = self.start.replace(hour=18)
        record = self.record()
        date = (self.start + timedelta(hours=5)).date()
        self.assertEqual(self.workspace(start_from=str(date), start_to=str(date + timedelta(days=1))).data["count"], 1)
        self.api.force_authenticate(self.staff)
        response = self.workspace()
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data["count"], 0)
        self.assertEqual(sum(response.data["summary"].values()), 0)
        self.resource.linked_user = self.staff
        self.resource.save(update_fields=["linked_user"])
        self.assertEqual(self.workspace().data["results"][0]["id"], record.pk)

    def test_search_cannot_reveal_client_without_client_view(self):
        self.record()
        role = self.staff.business_memberships.get(business=self.business).business_role
        RolePermission.objects.update_or_create(business_role=role, resource="appointments", action="view", defaults={"scope": "business", "is_allowed": True})
        RolePermission.objects.update_or_create(business_role=role, resource="clients", action="view", defaults={"scope": "business", "is_allowed": False})
        self.api.force_authenticate(self.staff)
        self.assertEqual(self.workspace().data["count"], 1)
        response = self.workspace(q=self.client_record.full_name)
        self.assertEqual(response.data["count"], 0)
        self.assertEqual(sum(response.data["summary"].values()), 0)
        self.assertEqual(self.workspace(client=self.client_record.pk).data["count"], 0)

    def test_pending_results_keep_past_records_and_exclude_future_and_terminal(self):
        from django.utils import timezone
        self.start = timezone.now() - timedelta(days=4)
        past = self.record(status="rescheduled")
        self.record(status="completed")
        self.start = timezone.now() + timedelta(days=1)
        self.record()
        response = self.workspace(attention="pending_result", client=self.client_record.pk)
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual([row["id"] for row in response.data["results"]], [past.pk])
        self.assertEqual(response.data["summary"], {"planned": 1, "completed": 0, "cancelled": 0, "no_show": 0})
        self.assertEqual(self.workspace(client=self.client_record.pk + 9999).data["count"], 0)
        self.assertEqual(self.workspace(client="bad").status_code, 400)
        self.assertEqual(self.workspace(attention="invalid").status_code, 400)

    def test_foreign_business_and_revoked_access(self):
        from apps.businesses.models import Business
        foreign = Business.objects.create(owner=self.staff, name="Foreign", slug="workspace-foreign")
        self.assertEqual(self.workspace(business=foreign.pk).status_code, 400)
        self.api.force_authenticate(self.staff)
        self.staff.business_memberships.filter(business=self.business).update(is_active=False)
        self.assertEqual(self.workspace().status_code, 400)

    def test_legacy_resolution_uses_links_not_shared_client(self):
        unrelated = self.record()
        linked = self.record(lead=self.lead)
        response = self.api.get("/api/appointments/legacy-links/", {"business": self.business.pk, "kind": "lead", "object_id": self.lead.pk})
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual([item["id"] for item in response.data["results"]], [linked.pk])
        self.assertNotEqual(linked.pk, unrelated.pk)
        self.assertEqual(response.data["source"]["client"], self.client_record.pk)
        linked.lead = None
        linked.save(update_fields=["lead"])
        self.assertEqual(self.api.get("/api/appointments/legacy-links/", {"business": self.business.pk, "kind": "lead", "object_id": self.lead.pk}).data["count"], 0)

    def test_legacy_resolution_denies_hidden_source_and_invalid_kind(self):
        self.api.force_authenticate(self.staff)
        response = self.api.get("/api/appointments/legacy-links/", {"business": self.business.pk, "kind": "lead", "object_id": self.lead.pk})
        self.assertEqual(response.status_code, 404, response.data)
        self.assertEqual(self.api.get("/api/appointments/legacy-links/", {"business": self.business.pk, "kind": "task", "object_id": self.lead.pk}).status_code, 400)

    def test_legacy_deal_returns_all_real_links_and_preserves_archived_source(self):
        from apps.crm.models import Deal, Pipeline, PipelineStage
        pipeline = Pipeline.objects.create(business=self.business, name="Historical", slug="historical")
        stage = PipelineStage.objects.create(business=self.business, pipeline=pipeline, name="Closed")
        deal = Deal.objects.create(business=self.business, client=self.client_record, lead=self.lead,
            pipeline=pipeline, stage=stage, title="Archived deal", is_archived=True)
        records = [self.record(lead=self.lead) for _ in range(27)]
        params = {"business": self.business.pk, "kind": "deal", "object_id": deal.pk, "page": 2}
        response = self.api.get("/api/appointments/legacy-links/", params)
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data["count"], 27)
        self.assertEqual([item["id"] for item in response.data["results"]], [records[1].pk, records[0].pk])
        self.assertEqual(response.data["source"]["card"]["deal"]["title"], "Archived deal")
        deal.refresh_from_db()
        self.assertTrue(deal.is_archived)
        self.assertEqual(deal.lead_id, self.lead.pk)

    def test_legacy_source_read_does_not_require_or_grant_appointment_or_client_read(self):
        self.record(lead=self.lead)
        role = self.staff.business_memberships.get(business=self.business).business_role
        for resource, allowed in (("leads", True), ("appointments", False), ("clients", False)):
            RolePermission.objects.update_or_create(business_role=role, resource=resource, action="view",
                defaults={"scope": "business", "is_allowed": allowed})
        self.api.force_authenticate(self.staff)
        response = self.api.get("/api/appointments/legacy-links/", {"business": self.business.pk, "kind": "lead", "object_id": self.lead.pk})
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data["count"], 0)
        self.assertIsNone(response.data["source"]["client"])
        self.assertIsNone(response.data["source"]["card"]["client"])
        self.assertEqual(response.data["source"]["card"]["appointments"], [])
        self.assertEqual(response.data["source"]["card"]["lead"]["id"], self.lead.pk)
