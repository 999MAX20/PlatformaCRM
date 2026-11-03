from datetime import timedelta
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

from django.db import connections
from django.test import TransactionTestCase, skipUnlessDBFeature
from django.utils import timezone
from rest_framework.test import APIClient

from apps.scheduling import tests_visit_plans as fixtures
from apps.scheduling.models import Appointment, VisitPlan
from apps.scheduling.plan_services import create_plan


@skipUnlessDBFeature("has_select_for_update")
class PlanConcurrencyTests(TransactionTestCase):
    def setUp(self):
        fixtures.VisitPlanTests.setUpTestData.__func__(type(self))
        self.plan, _ = create_plan(business=self.business, actor=self.owner, client=self.customer,
            steps=[{"service": self.service}], idempotency_key="plan")
        self.payload = {"expected_revision": 1, "step_id": self.plan.steps.get().pk,
            "resource": self.resource.pk, "start_at": (timezone.now() + timedelta(days=2)).replace(hour=10, minute=0, second=0, microsecond=0).isoformat(),
            "expected_price": "100.00", "expected_duration_minutes": 30}

    def parallel(self, operations):
        barrier = Barrier(len(operations))
        def run(operation):
            connections.close_all()
            try:
                api = APIClient()
                api.force_authenticate(self.owner)
                barrier.wait(timeout=20)
                response = operation(api)
                return response.status_code, response.data
            finally:
                connections.close_all()
        with ThreadPoolExecutor(max_workers=len(operations)) as pool:
            futures = [pool.submit(run, op) for op in operations]
            return [future.result(timeout=45) for future in futures]

    def schedule(self, api, plan=None, payload=None, key="schedule"):
        return api.post(f"/api/visit-plans/{(plan or self.plan).pk}/commands/schedule/?business={self.business.pk}",
            payload or self.payload, format="json", HTTP_IDEMPOTENCY_KEY=key)

    def test_same_command_creates_one_appointment(self):
        results = self.parallel([lambda api: self.schedule(api)] * 2)
        self.assertEqual(sorted(code for code, _ in results), [200, 200], results)
        self.assertEqual(Appointment.objects.count(), 1)
        self.plan.refresh_from_db()
        self.assertEqual(self.plan.revision, 2)

    def test_last_slot_between_plans_has_one_winner(self):
        other, _ = create_plan(business=self.business, actor=self.owner, client=self.customer,
            steps=[{"service": self.service}], idempotency_key="other")
        payload = {**self.payload, "step_id": other.steps.get().pk}
        results = self.parallel([lambda api: self.schedule(api), lambda api: self.schedule(api, other, payload, "other-slot")])
        self.assertEqual(sorted(code for code, _ in results), [200, 409], results)
        self.assertEqual(Appointment.objects.count(), 1)
        self.assertEqual(VisitPlan.objects.filter(revision=2).count(), 1)

    def test_remove_and_schedule_cannot_both_apply(self):
        def remove(api):
            return api.post(f"/api/visit-plans/{self.plan.pk}/commands/revise/?business={self.business.pk}",
                {"expected_revision": 1, "consent": True, "reason": "Changed", "remove": [self.payload["step_id"]]},
                format="json", HTTP_IDEMPOTENCY_KEY="remove")
        results = self.parallel([lambda api: self.schedule(api), remove])
        self.assertEqual(sorted(code for code, _ in results), [200, 409], results)
        step = self.plan.steps.get()
        self.assertNotEqual(bool(step.appointment_id), bool(step.removed_at))
