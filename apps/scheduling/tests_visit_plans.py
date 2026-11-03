from datetime import time, timedelta
from unittest.mock import patch

from django.test import TestCase
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.businesses.access import Actions, Resources, ensure_default_roles
from apps.businesses.models import Business, BusinessMember, BusinessRole, RolePermission
from apps.clients.models import Client
from apps.core.domain_errors import InvalidTransition, IdempotencyConflict
from apps.core.models import CRMCommandIdempotency
from apps.scheduling.models import Appointment, Resource, VisitPlan, VisitPlanStep, WorkingHours
from apps.scheduling.plan_access import visible_steps
from apps.scheduling.plan_services import create_plan, change_plan
from apps.services.models import Service


class VisitPlanTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.owner = User.objects.create_user(username="plan-owner", email="plan-owner@example.test", role="business_owner")
        cls.staff = User.objects.create_user(username="plan-staff", email="plan-staff@example.test", role="staff")
        cls.business = Business.objects.create(owner=cls.owner, name="Plans", slug="plans", timezone="UTC")
        ensure_default_roles(cls.business)
        cls.role = BusinessRole.objects.get(business=cls.business, preset_key="specialist")
        BusinessMember.objects.create(business=cls.business, user=cls.staff, role="specialist", business_role=cls.role)
        cls.customer = Client.objects.create(business=cls.business, full_name="Client")
        cls.service = Service.objects.create(business=cls.business, name="Service", duration_minutes=30, price_from=100)
        cls.resource = Resource.objects.create(business=cls.business, name="Specialist", linked_user=cls.staff)
        for weekday in range(7):
            WorkingHours.objects.create(business=cls.business, weekday=weekday, start_time=time(8), end_time=time(20))

    def make(self, **overrides):
        return create_plan(**{"business": self.business, "actor": self.owner, "client": self.customer,
            "steps": [{"service": self.service}], "idempotency_key": "create", **overrides})

    def change(self, plan, command="revise", data=None, **overrides):
        return change_plan(**{"plan": plan, "actor": self.owner, "command": command,
            "expected_revision": plan.revision, "idempotency_key": command,
            "data": data or {"consent": True, "reason": "Client agreed", "add": [{"service": self.service}]}, **overrides})

    def schedule(self, plan, **overrides):
        start = (timezone.now() + timedelta(days=2)).replace(hour=10, minute=0, second=0, microsecond=0)
        return self.change(plan, "schedule", {"step_id": plan.steps.first().pk, "start_at": start,
            "resource": self.resource, "expected_price": self.service.price_from,
            "expected_duration_minutes": 30}, **overrides)

    def test_undated_and_replay_have_no_appointments(self):
        plan, replay = self.make()
        self.assertFalse(replay)
        again, replay = self.make()
        self.assertTrue(replay)
        self.assertEqual(plan.pk, again.pk)
        self.assertEqual(VisitPlanStep.objects.count(), 1)
        self.assertFalse(Appointment.objects.exists())
        self.assertEqual(plan.responsible_user, self.owner)
        self.assertEqual(CRMCommandIdempotency.objects.get().response_json, {})

    def test_schedule_single_identity_replay_and_stale(self):
        plan, _ = self.make()
        plan, _ = self.schedule(plan)
        self.assertEqual(plan.revision, 2)
        appointment = plan.steps.get().appointment
        self.assertEqual(appointment.client, self.customer)
        self.assertEqual(appointment.responsible_user, self.owner)
        _, replay = self.schedule(plan, expected_revision=1)
        self.assertTrue(replay)
        self.assertEqual(Appointment.objects.count(), 1)
        with self.assertRaises(InvalidTransition):
            self.change(plan, expected_revision=1)
        with self.assertRaises(InvalidTransition):
            self.schedule(plan, idempotency_key="new-key")

    def test_revision_consent_stable_removed_history(self):
        plan, _ = self.make()
        step = plan.steps.get()
        with self.assertRaises(ValidationError):
            self.change(plan, data={"remove": [step.pk]})
        plan, _ = self.change(plan, data={"consent": True, "reason": "Changed", "remove": [step.pk], "add": [{"service": self.service}]})
        step.refresh_from_db()
        self.assertIsNotNone(step.removed_at)
        self.assertEqual(plan.steps.count(), 2)
        self.assertEqual(plan.revision, 2)
        with self.assertRaises(IdempotencyConflict):
            self.change(plan, data={"consent": True, "reason": "Different"})

    def test_rollback_including_booking_effects(self):
        plan, _ = self.make()
        with patch("apps.scheduling.plan_services._effect", side_effect=RuntimeError("synthetic")):
            with self.assertRaises(RuntimeError):
                self.schedule(plan)
        plan.refresh_from_db()
        self.assertEqual(plan.revision, 1)
        self.assertFalse(Appointment.objects.exists())
        self.assertIsNone(plan.steps.get().appointment_id)
        self.assertEqual(CRMCommandIdempotency.objects.count(), 1)

    def test_tenant_invalid_service_and_required_key(self):
        foreign = Business.objects.create(owner=self.owner, name="Other", slug="other")
        other = Service.objects.create(business=foreign, name="Other", duration_minutes=30)
        for overrides in ({"steps": [{"service": other}]}, {"idempotency_key": ""}):
            with self.assertRaises(ValidationError):
                self.make(**overrides)
        self.assertFalse(VisitPlan.objects.exists())

    def permissions(self):
        for action in (Actions.VIEW, Actions.CREATE, Actions.UPDATE):
            RolePermission.objects.update_or_create(business_role=self.role, resource=Resources.APPOINTMENTS,
                action=action, defaults={"is_allowed": True, "scope": "own"})
        RolePermission.objects.update_or_create(business_role=self.role, resource=Resources.CLIENTS,
            action=Actions.VIEW, defaults={"is_allowed": True, "scope": "business"})

    def test_own_cannot_gain_access_from_responsible_or_empty_plan(self):
        self.permissions()
        plan, _ = self.make(responsible_user=self.staff)
        with self.assertRaises(PermissionDenied):
            visible_steps(plan, self.staff)
        for steps in ([], [{"service": self.service}]):
            with self.assertRaises(PermissionDenied):
                self.make(actor=self.staff, steps=steps)

    def test_partial_visibility_does_not_authorize_hidden_mutation(self):
        self.permissions()
        plan, _ = self.make(steps=[{"service": self.service, "resource": self.resource}, {"service": self.service}])
        self.assertEqual(len(visible_steps(plan, self.staff)), 1)
        with self.assertRaises(PermissionDenied):
            self.change(plan, actor=self.staff)
        BusinessMember.objects.filter(business=self.business, user=self.staff).update(is_active=False)
        with self.assertRaises(PermissionDenied):
            visible_steps(plan, self.staff)

    def test_scheduled_history_not_replaced_after_cancel(self):
        plan, _ = self.make()
        plan, _ = self.schedule(plan)
        step = plan.steps.get()
        Appointment.objects.filter(pk=step.appointment_id).update(status="cancelled")
        with self.assertRaises(InvalidTransition):
            self.schedule(plan, idempotency_key="replace")
        with self.assertRaises(InvalidTransition):
            self.change(plan, data={"consent": True, "reason": "Remove", "remove": [step.pk]})

    def test_archive_restore_versioned(self):
        plan, _ = self.make()
        plan, _ = self.change(plan, "archive", {"reason": "Stopped"})
        self.assertTrue(plan.is_archived)
        with self.assertRaises(InvalidTransition):
            self.schedule(plan)
        plan, _ = self.change(plan, "restore", {"reason": "Resume"})
        self.assertFalse(plan.is_archived)
        self.assertEqual(plan.revision, 3)

    def test_api_pagination_detail_and_replay(self):
        api = APIClient()
        api.force_authenticate(self.owner)
        payload = {"business": self.business.pk, "client": self.customer.pk, "steps": [{"service": self.service.pk}]}
        first = api.post("/api/visit-plans/", payload, format="json", HTTP_IDEMPOTENCY_KEY="api")
        self.assertEqual(first.status_code, 201, first.data)
        again = api.post("/api/visit-plans/", payload, format="json", HTTP_IDEMPOTENCY_KEY="api")
        self.assertEqual(again.status_code, 200, again.data)
        self.assertEqual(first.data["id"], again.data["id"])
        listing = api.get("/api/visit-plans/", {"business": self.business.pk, "page_size": 1})
        self.assertEqual(listing.data["count"], 1)
        self.assertEqual(listing.data["results"][0]["steps"][0]["status"], "unscheduled")
        self.assertEqual(api.get("/api/visit-plans/").status_code, 400)
        self.assertEqual(api.patch(f'/api/visit-plans/{first.data["id"]}/', payload, format="json").status_code, 405)

    def test_api_hidden_rows_filtered_before_count_and_page(self):
        self.permissions()
        hidden, _ = self.make()
        visible, _ = self.make(idempotency_key="visible", steps=[{"service": self.service, "resource": self.resource}, {"service": self.service}])
        api = APIClient()
        api.force_authenticate(self.staff)
        response = api.get("/api/visit-plans/", {"business": self.business.pk, "page_size": 1})
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data["count"], 1)
        row = response.data["results"][0]
        self.assertEqual(row["id"], visible.pk)
        self.assertEqual(len(row["steps"]), 1)
        self.assertFalse(row["can_change"])
        self.assertEqual(api.get(f"/api/visit-plans/{hidden.pk}/", {"business": self.business.pk}).status_code, 404)
        response = api.post(f"/api/visit-plans/{visible.pk}/commands/revise/?business={self.business.pk}",
            {"expected_revision": 1, "consent": True, "reason": "Hidden removal", "remove": [visible.steps.last().pk]}, format="json", HTTP_IDEMPOTENCY_KEY="denied")
        self.assertEqual(response.status_code, 403, response.data)

    def test_appointment_command_advances_plan_revision(self):
        from apps.scheduling.services import confirm_appointment, cancel_appointment
        plan, _ = self.make()
        plan, _ = self.schedule(plan)
        appointment = plan.steps.get().appointment
        confirm_appointment(appointment=appointment, actor=self.owner)
        plan.refresh_from_db()
        self.assertEqual(plan.revision, 3)
        with self.assertRaises(InvalidTransition):
            self.change(plan, expected_revision=2)
        cancel_appointment(appointment=appointment, actor=self.owner, reason="Client request")
        plan.refresh_from_db()
        self.assertEqual(plan.revision, 4)
        self.assertEqual(plan.steps.get().appointment.status, "cancelled")

    def test_client_merge_moves_plan_and_scheduled_identity(self):
        from apps.clients.services import merge_clients, merge_clients_dry_run
        plan, _ = self.make()
        plan, _ = self.schedule(plan)
        target = Client.objects.create(business=self.business, full_name="Target")
        preview = merge_clients_dry_run(target_client=target, duplicate_client=self.customer)
        self.assertIn("visit_plans", str(preview))
        merge_clients(target_client=target, duplicate_client=self.customer, actor=self.owner)
        plan.refresh_from_db()
        self.assertEqual(plan.client_id, target.pk)
        self.assertEqual(plan.steps.get().appointment.client_id, target.pk)
        self.assertEqual(plan.revision, 3)

    def test_client_archive_rejects_undated_and_allows_archived_plan(self):
        from apps.clients.lifecycle import client_has_unfinished_work
        plan, _ = self.make()
        self.assertTrue(client_has_unfinished_work(self.customer))
        plan, _ = self.change(plan, "archive", {"reason": "Stopped"})
        self.assertFalse(client_has_unfinished_work(self.customer))

    def test_responsible_default_does_not_overwrite_step_override(self):
        plan, _ = self.make(steps=[{"service": self.service, "responsible_user": self.owner}, {"service": self.service}])
        plan, _ = self.change(plan, "responsible", {"responsible_user": self.staff})
        self.assertEqual(plan.responsible_user_id, self.staff.pk)
        self.assertEqual(plan.steps.first().responsible_user_id, self.owner.pk)
        with self.assertRaises(ValidationError):
            self.change(plan, "responsible", {"responsible_user": self.staff, "step_ids": [plan.steps.first().pk]}, idempotency_key="override")

    def test_plan_history_does_not_leak_via_client(self):
        from apps.activities.models import ActivityEvent
        from apps.core.crm_read_scope import scope_entity_records
        self.permissions()
        plan, _ = self.make(responsible_user=self.staff)
        events = scope_entity_records(ActivityEvent.objects.filter(entity_type="VisitPlan"), actor=self.staff, business=self.business)
        self.assertFalse(events.exists())
        self.assertTrue(ActivityEvent.objects.filter(entity_type="VisitPlan", entity_id=str(plan.pk)).exists())

    def test_own_and_team_candidates_match_sql_and_object_policy(self):
        from apps.scheduling.plan_selectors import readable_plans
        self.permissions()
        for scope in ("own", "team"):
            RolePermission.objects.filter(business_role=self.role, resource=Resources.APPOINTMENTS).update(scope=scope)
            plan, _ = self.make(actor=self.staff, steps=[{"service": self.service, "resource": self.resource}], idempotency_key=scope)
            self.assertEqual(len(visible_steps(plan, self.staff)), 1)
            self.assertTrue(readable_plans(business=self.business, actor=self.staff).filter(pk=plan.pk).exists())
        BusinessMember.objects.filter(business=self.business, user=self.staff).update(is_active=False)
        self.assertFalse(readable_plans(business=self.business, actor=self.staff).exists())

    def test_branch_scope_hides_undated_and_prevents_new_step(self):
        from apps.branches.models import Branch, BranchService, SpecialistBranch
        from apps.scheduling.plan_selectors import readable_plans
        self.permissions()
        branch = Branch.objects.create(business=self.business, name="Restricted")
        BranchService.objects.create(business=self.business, branch=branch, service=self.service, duration_minutes=30)
        assignment = SpecialistBranch.objects.create(business=self.business, branch=branch, resource=self.resource)
        assignment.services.add(self.service)
        steps = [{"service": self.service, "resource": self.resource, "branch": branch}]
        plan, _ = self.make(steps=steps)
        self.assertFalse(readable_plans(business=self.business, actor=self.staff).exists())
        with self.assertRaises(PermissionDenied):
            self.make(actor=self.staff, steps=steps)
        with self.assertRaises(PermissionDenied):
            visible_steps(plan, self.staff)

    def test_replay_rechecks_creation_permission_and_current_projection(self):
        self.permissions()
        plan, _ = self.make(actor=self.staff, steps=[{"service": self.service, "resource": self.resource}])
        RolePermission.objects.filter(business_role=self.role, resource=Resources.APPOINTMENTS, action=Actions.CREATE).update(is_allowed=False)
        with self.assertRaises(PermissionDenied):
            self.make(actor=self.staff, steps=[{"service": self.service, "resource": self.resource}])
        self.assertEqual(VisitPlan.objects.count(), 1)
        self.assertEqual(plan.revision, 1)

    def test_disabled_specialist_and_unknown_step_are_rejected(self):
        self.resource.is_active = False
        self.resource.save(update_fields=["is_active"])
        with self.assertRaises(ValidationError):
            self.make(steps=[{"service": self.service, "resource": self.resource}])
        plan, _ = self.make()
        with self.assertRaises(ValidationError):
            self.change(plan, data={"consent": True, "reason": "Changed", "changes": [{"id": 999999, "service": self.service}]})
        self.assertEqual(plan.steps.count(), 1)

    def test_card_plan_link_respects_client_view(self):
        from apps.core.crm_cards import appointment_crm_card
        plan, _ = self.make()
        plan, _ = self.schedule(plan)
        appointment = plan.steps.get().appointment
        self.assertEqual(appointment_crm_card(appointment, actor=self.owner)["appointment"]["visit_plan"], plan.pk)
        self.permissions()
        RolePermission.objects.filter(business_role=self.role, resource=Resources.CLIENTS, action=Actions.VIEW).update(is_allowed=False)
        self.assertIsNone(appointment_crm_card(appointment, actor=self.staff)["appointment"]["visit_plan"])

    def test_history_is_paginated_and_never_exposes_audit_snapshots(self):
        plan, _ = self.make()
        plan, _ = self.change(plan)
        api = APIClient()
        api.force_authenticate(self.owner)
        response = api.get(f"/api/visit-plans/{plan.pk}/history/", {"business": self.business.pk, "page_size": 1})
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data["count"], 2)
        self.assertEqual(response.data["results"][0]["command"], "revise")
        self.assertEqual(set(response.data["results"][0]), {"id", "created_at", "command", "actor_name"})
        api.force_authenticate(self.staff)
        self.assertEqual(api.get(f"/api/visit-plans/{plan.pk}/history/", {"business": self.business.pk}).status_code, 404)
