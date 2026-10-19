from concurrent.futures import ThreadPoolExecutor
from threading import Barrier, local
from unittest.mock import patch

from django.db import close_old_connections
from django.test import TransactionTestCase, skipUnlessDBFeature
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.automations.models import AutomationAction, AutomationRule
from apps.businesses.models import Business


@skipUnlessDBFeature("has_select_for_update")
class AutomationConfigurationConcurrencyTests(TransactionTestCase):
    def setUp(self):
        self.owner = User.objects.create_user(username="concurrent-config", email="concurrent-config@example.test", role="business_owner")
        self.business = Business.objects.create(owner=self.owner, name="Concurrent config", slug="concurrent-config")
        self.rule = AutomationRule.objects.create(business=self.business, name="Concurrent", trigger_type="lead_created", is_active=True)

    def race(self, operations):
        barrier, thread = Barrier(2), local()
        original = Business.objects.select_for_update

        def lock(*args, **kwargs):
            if not getattr(thread, "ready", False):
                thread.ready = True
                barrier.wait(timeout=20)
            return original(*args, **kwargs)

        def run(operation):
            close_old_connections()
            try:
                api = APIClient()
                api.force_authenticate(User.objects.get(pk=self.owner.pk))
                return operation(api).status_code
            finally:
                close_old_connections()

        with patch.object(Business.objects, "select_for_update", side_effect=lock):
            with ThreadPoolExecutor(max_workers=2) as pool:
                futures = [pool.submit(run, operation) for operation in operations]
                return [future.result(timeout=45) for future in futures]

    def test_two_deletions_cannot_empty_an_active_rule(self):
        actions = [AutomationAction.objects.create(rule=self.rule, action_type="create_task", config={}) for _ in range(2)]
        statuses = self.race([lambda api, pk=action.pk: api.delete(f"/api/automation-actions/{pk}/") for action in actions])
        self.assertEqual(sorted(statuses), [204, 400])
        self.rule.refresh_from_db()
        self.assertTrue(self.rule.is_active)
        self.assertEqual(self.rule.actions.count(), 1)

    def test_activation_and_deletion_validate_the_locked_composition(self):
        self.rule.is_active = False
        self.rule.save()
        action = AutomationAction.objects.create(rule=self.rule, action_type="create_task", config={})
        statuses = self.race([
            lambda api: api.patch(f"/api/automation-rules/{self.rule.pk}/", {"is_active": True}, format="json"),
            lambda api: api.delete(f"/api/automation-actions/{action.pk}/"),
        ])
        self.rule.refresh_from_db()
        self.assertIn(statuses, ([200, 400], [400, 204]))
        self.assertFalse(self.rule.is_active and not self.rule.actions.exists())
