from concurrent.futures import ThreadPoolExecutor
from threading import Barrier, local
from unittest.mock import patch

from django.db import close_old_connections
from django.test import TransactionTestCase, skipUnlessDBFeature

from apps.automations import tests_follow_up_policy
from apps.automations.engine import _create_follow_up
from apps.businesses.models import Business
from apps.scheduling.models import Appointment
from apps.scheduling.services import create_appointment_follow_up_task
from apps.tasks.models import Task


@skipUnlessDBFeature("has_select_for_update")
class FollowUpConcurrencyTests(TransactionTestCase):
    def test_builtin_and_rule_create_one_task_under_race(self):
        fixture = tests_follow_up_policy.FollowUpPolicyTests()
        fixture.setUp()
        appointment = fixture.appointment
        appointment.status = Appointment.Statuses.COMPLETED
        appointment.save(update_fields=["status"])
        action = fixture.rule().actions.get()
        barrier, thread = Barrier(2), local()
        original = Business.objects.select_for_update

        def lock(*args, **kwargs):
            if not getattr(thread, "ready", False):
                thread.ready = True
                barrier.wait(timeout=20)
            return original(*args, **kwargs)

        def execute(rule):
            close_old_connections()
            try:
                if rule:
                    return _create_follow_up(action, business=fixture.f.business, entity=appointment, payload={}).pk
                return create_appointment_follow_up_task(appointment=appointment, actor=fixture.f.owner).pk
            finally:
                close_old_connections()

        with patch.object(Business.objects, "select_for_update", side_effect=lock):
            with ThreadPoolExecutor(max_workers=2) as pool:
                futures = [pool.submit(execute, value) for value in (True, False)]
                ids = [future.result(timeout=45) for future in futures]
        self.assertEqual(ids[0], ids[1])
        self.assertEqual(Task.objects.filter(appointment=appointment).count(), 1)
