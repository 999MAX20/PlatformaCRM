from concurrent.futures import ThreadPoolExecutor
from datetime import time
from threading import Barrier

from django.db import IntegrityError, close_old_connections
from django.test import TransactionTestCase, skipUnlessDBFeature

from apps.accounts.models import User
from apps.businesses.models import Business
from apps.scheduling.models import WorkingHours


@skipUnlessDBFeature("has_select_for_update")
class WorkingHoursConcurrencyTests(TransactionTestCase):
    def test_concurrent_general_day_inserts_have_one_winner(self):
        owner = User.objects.create_user(username="hours-race", email="hours-race@example.test")
        business = Business.objects.create(owner=owner, name="Hours race", slug="hours-race")
        barrier = Barrier(2)

        def insert():
            close_old_connections()
            try:
                barrier.wait(timeout=15)
                WorkingHours.objects.create(business_id=business.pk, weekday=0, start_time=time(9), end_time=time(18))
                return "created"
            except IntegrityError:
                return "rejected"
            finally:
                close_old_connections()

        with ThreadPoolExecutor(max_workers=2) as pool:
            attempts = [pool.submit(insert) for _ in range(2)]
            self.assertEqual(sorted(item.result(timeout=30) for item in attempts), ["created", "rejected"])
        self.assertEqual(WorkingHours.objects.filter(business=business, weekday=0).count(), 1)
