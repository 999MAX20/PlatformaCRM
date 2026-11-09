from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

from django.db import close_old_connections
from django.test import TransactionTestCase, skipUnlessDBFeature

from apps.businesses.models import Business
from apps.core.domain_errors import InvalidTransition
from .models import Branch
from .services import create_branch
from .single_location import ensure_initial_location
from .staff_lifecycle import change_branch_state
from . import tests_single_location as fixtures


@skipUnlessDBFeature("has_select_for_update")
class SingleLocationConcurrencyTests(TransactionTestCase):
    setUp = fixtures.SingleLocationTests.setUp

    def parallel(self, actions):
        barrier = Barrier(len(actions))
        def run(action):
            close_old_connections()
            try:
                barrier.wait(timeout=15)
                return action()
            finally:
                close_old_connections()
        with ThreadPoolExecutor(max_workers=len(actions)) as pool:
            pending = [pool.submit(run, action) for action in actions]
            return [item.result(timeout=30) for item in pending]

    def test_concurrent_initialization_creates_one_location(self):
        def create():
            return ensure_initial_location(Business.objects.get(pk=self.business.pk)).pk
        self.assertEqual(len(set(self.parallel([create, create]))), 1)
        self.assertEqual(Branch.objects.filter(business=self.business).count(), 1)

    def test_concurrent_archival_preserves_one_active_location(self):
        first = ensure_initial_location(self.business)
        second = create_branch(business=self.business, actor=self.owner, name="Second")
        def archive(branch):
            try:
                change_branch_state(branch=branch, actor=self.owner, state="archived")
                return "archived"
            except InvalidTransition:
                return "blocked"
        result = self.parallel([lambda: archive(first), lambda: archive(second)])
        self.assertEqual(sorted(result), ["archived", "blocked"])
        self.assertEqual(Branch.objects.filter(business=self.business, is_active=True, archived_at__isnull=True).count(), 1)
