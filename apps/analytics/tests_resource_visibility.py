import csv
from datetime import timedelta
from decimal import Decimal
import io

from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.analytics.crm_metrics import build_crm_operational_metrics
from apps.businesses.models import Business, BusinessCapability, BusinessMember, BusinessRole, RolePermission, Team, TeamMember
from apps.clients.models import Client
from apps.crm.models import Deal, Pipeline, PipelineStage
from apps.leads.models import Lead
from apps.scheduling.models import Appointment, Resource
from apps.services.models import Service
from apps.tasks.models import Task


class LegacyAnalyticsResourceVisibilityTests(TestCase):
    resources = ("leads", "deals", "appointments", "tasks")

    def setUp(self):
        self.now = timezone.now()
        self.owner = User.objects.create_user(username="metric-owner", email="metric-owner@example.test")
        self.actor = User.objects.create_user(username="metric-reader", email="metric-reader@example.test")
        self.peer = User.objects.create_user(username="metric-peer", email="metric-peer@example.test")
        self.business = Business.objects.create(owner=self.owner, name="Metrics", slug="metrics-visibility")
        self.role = BusinessRole.objects.create(business=self.business, name="Scoped metrics")
        self.member = BusinessMember.objects.create(business=self.business, user=self.actor, role="admin", business_role=self.role)
        self.peer_member = BusinessMember.objects.create(business=self.business, user=self.peer, role="manager")
        for resource in (*self.resources, "analytics", "clients"):
            RolePermission.objects.create(business_role=self.role, resource=resource, action="view", scope="business")
        self.client = Client.objects.create(business=self.business, full_name="Synthetic metric client")
        self.service = Service.objects.create(business=self.business, name="Synthetic service", price_from=7, duration_minutes=30)
        pipeline = Pipeline.objects.create(business=self.business, name="Metrics")
        stage = PipelineStage.objects.create(business=self.business, pipeline=pipeline, name="Start", order=1)
        self.leads, self.deals, self.appointments, self.tasks = [], [], [], []
        for index, user in enumerate((self.actor, self.peer)):
            lead = Lead.objects.create(business=self.business, client=self.client, responsible_user=user, status=Lead.Statuses.NEW, source="website")
            self.leads.append(lead)
            self.deals.append(Deal.objects.create(business=self.business, client=self.client, pipeline=pipeline, stage=stage,
                lead=lead, owner=user, title="Synthetic outcome", status=Deal.Statuses.WON, amount=11+index))
            resource = Resource.objects.create(business=self.business, name=f"Synthetic specialist {index}", linked_user=user)
            self.appointments.append(Appointment.objects.create(business=self.business, client=self.client, service=self.service,
                lead=lead, resource=resource, start_at=self.now+timedelta(hours=index), end_at=self.now+timedelta(hours=index+1),
                status=Appointment.Statuses.COMPLETED))
            self.tasks.append(Task.objects.create(business=self.business, client=self.client, assignee=user, created_by=user,
                title="Synthetic overdue", due_at=self.now-timedelta(hours=1)))
        self.api = APIClient()
        self.api.force_authenticate(self.actor)

    def permission(self, resource, *, allowed=True, scope="business"):
        RolePermission.objects.filter(business_role=self.role, resource=resource, action="view").update(is_allowed=allowed, scope=scope)

    def metrics(self, user=None, **kwargs):
        return build_crm_operational_metrics(self.business, user=user or self.actor, now=self.now, **kwargs)

    def api_payload(self, dashboard=False):
        path = "/api/analytics/owner-dashboard/" if dashboard else "/api/analytics/reports/summary/"
        response = self.api.get(path, {"business": self.business.pk})
        self.assertEqual(response.status_code, 200, response.data)
        return response.data

    def assert_resource_zero(self, metrics, resource):
        keys = {"leads": ("assigned_leads",), "deals": ("won_deals", "lost_deals", "deals_from_leads"),
                "appointments": ("appointments_completed", "appointments_no_show"), "tasks": ("open_tasks", "overdue_tasks")}
        for row in metrics["manager_performance"]["rows"]:
            for key in keys[resource]:
                self.assertEqual(row[key], 0, (resource, key, row))
            if resource == "deals":
                self.assertEqual(Decimal(row["won_value"]), 0)
                self.assertEqual(Decimal(row["lost_value"]), 0)

    def test_lead_view_denial_filters_manager_counts(self):
        self.permission("leads", allowed=False, scope="none")
        self.assert_resource_zero(self.metrics(), "leads")

    def test_deal_view_denial_filters_outcome_counts_and_sums(self):
        self.permission("deals", allowed=False, scope="none")
        self.assert_resource_zero(self.metrics(), "deals")

    def test_appointment_view_denial_filters_outcomes(self):
        self.permission("appointments", allowed=False, scope="none")
        self.assert_resource_zero(self.metrics(), "appointments")

    def test_task_view_denial_filters_open_and_overdue(self):
        self.permission("tasks", allowed=False, scope="none")
        self.assert_resource_zero(self.metrics(), "tasks")

    def test_own_scope_applies_before_member_grouping(self):
        for resource in self.resources:
            self.permission(resource, scope="own")
        metrics = self.metrics()
        rows = {r["user_id"]: r for r in metrics["manager_performance"]["rows"]}
        for key in ("assigned_leads", "won_deals", "appointments_completed", "open_tasks", "overdue_tasks"):
            self.assertEqual(rows[self.actor.pk][key], 1)
            self.assertEqual(rows[self.peer.pk][key], 0)
        self.assertEqual(Decimal(rows[self.actor.pk]["won_value"]), 11)
        self.assertEqual(Decimal(rows[self.peer.pk]["won_value"]), 0)

    def test_team_scope_hides_records_outside_team(self):
        team = Team.objects.create(business=self.business, name="Metric team")
        TeamMember.objects.create(team=team, member=self.member, is_lead=True)
        for resource in self.resources:
            self.permission(resource, scope="team")
        self.assertEqual(self.metrics()["manager_performance"]["totals"]["assigned_leads"], 1)
        TeamMember.objects.create(team=team, member=self.peer_member)
        self.assertEqual(self.metrics()["manager_performance"]["totals"]["assigned_leads"], 2)

    def test_report_member_boundary_is_not_widened_by_resource_business_scope(self):
        self.member.role = "manager"
        self.member.save(update_fields=["role"])
        report = self.metrics()["manager_performance"]
        self.assertEqual(report["scope"], "own")
        self.assertEqual([r["user_id"] for r in report["rows"]], [self.actor.pk])
        self.assertEqual(report["totals"]["assigned_leads"], 1)

    def test_capability_disabled_filters_dashboard_summary_and_nested_metrics(self):
        for resource in self.resources:
            with self.subTest(resource=resource):
                capability, _ = BusinessCapability.objects.update_or_create(business=self.business, module_key=resource, defaults={"is_enabled": False})
                for dashboard in (True, False):
                    payload = self.api_payload(dashboard)
                    nested = payload if dashboard else {"manager_performance": payload["scoped_manager_performance"]}
                    self.assert_resource_zero(nested, resource)
                    if dashboard:
                        key = {"leads": "total_leads", "appointments": "appointments_completed", "tasks": "open_tasks"}.get(resource)
                        if key:
                            self.assertEqual(payload[key], 0)
                        self.assertFalse(payload["crm_metrics_meta"]["availability"][resource])
                    else:
                        key = {"leads": "assigned_leads", "deals": "won_deals", "tasks": "open_tasks"}.get(resource)
                        if key:
                            self.assertTrue(all(row[key] == 0 for row in payload["manager_performance"]))
                        if resource == "appointments":
                            self.assertTrue(all(row["appointments"] == 0 for row in payload["source_roi"]))
                capability.is_enabled = True
                capability.save(update_fields=["is_enabled"])

    def test_hidden_leads_not_counted_as_visible_deal_conversions(self):
        self.permission("leads", allowed=False, scope="none")
        report = self.metrics()["manager_performance"]
        self.assertEqual(report["totals"]["assigned_leads"], 0)
        self.assertEqual(report["totals"]["deals_from_leads"], 0)
        self.assertEqual(report["totals"]["won_deals"], 2)
        self.assertEqual(sum(r["appointments_completed"] for r in report["rows"]), 2)

    def test_owner_and_permitted_business_control_preserve_formulas(self):
        for user in (self.actor, self.owner):
            with self.subTest(user=user.pk):
                report = self.metrics(user)["manager_performance"]
                self.assertEqual(report["totals"]["assigned_leads"], 2)
                self.assertEqual(report["totals"]["won_deals"], 2)
                self.assertEqual(report["totals"]["deals_from_leads"], 2)
                self.assertEqual(report["totals"]["lead_to_deal_rate"], 100)
                self.assertEqual(sum(Decimal(r["won_value"]) for r in report["rows"]), 23)
                self.assertEqual(report["totals"]["overdue_tasks"], 2)

    def test_permission_change_takes_effect_on_next_dashboard_read(self):
        self.assertEqual(self.api_payload(True)["manager_performance"]["totals"]["won_deals"], 2)
        self.permission("deals", allowed=False, scope="none")
        self.assert_resource_zero(self.api_payload(True), "deals")

    @override_settings(REPORT_EXPORT_SYNC_MAX_DAYS=1000)
    def test_legacy_export_excludes_capability_disabled_metrics(self):
        BusinessCapability.objects.update_or_create(business=self.business, module_key="tasks", defaults={"is_enabled": False})
        response = self.api.get("/api/analytics/reports/export/", {"business": self.business.pk, "report": "manager_performance"})
        self.assertEqual(response.status_code, 200, getattr(response, "data", None))
        rows = list(csv.DictReader(io.StringIO(response.content.decode())))
        self.assertTrue(rows)
        self.assertTrue(all(row["open_tasks"] == "0" for row in rows))

    def test_foreign_and_archived_records_do_not_enter_aggregates(self):
        foreign = Business.objects.create(owner=self.owner, name="Foreign metrics", slug="foreign-metrics")
        client = Client.objects.create(business=foreign, full_name="Foreign synthetic")
        Lead.objects.create(business=foreign, client=client, responsible_user=self.actor)
        Lead.objects.create(business=self.business, client=self.client, responsible_user=self.actor, is_archived=True)
        self.assertEqual(self.metrics()["manager_performance"]["totals"]["assigned_leads"], 2)
        later = timezone.localdate()+timedelta(days=2)
        self.assertEqual(self.metrics(start_date=later, end_date=later)["manager_performance"]["totals"]["assigned_leads"], 0)

    def test_analytics_permission_remains_required(self):
        self.permission("analytics", allowed=False, scope="none")
        for path in ("/api/analytics/owner-dashboard/", "/api/analytics/reports/summary/"):
            self.assertEqual(self.api.get(path, {"business": self.business.pk}).status_code, 403)

    def test_visible_old_lead_conversion_keeps_existing_period_formula(self):
        Lead.objects.filter(pk=self.leads[0].pk).update(created_at=self.now-timedelta(days=60))
        start = timezone.localdate()-timedelta(days=1)
        report = self.metrics(start_date=start, end_date=timezone.localdate())["manager_performance"]
        self.assertEqual(report["totals"]["assigned_leads"], 1)
        self.assertEqual(report["totals"]["deals_from_leads"], 2)
