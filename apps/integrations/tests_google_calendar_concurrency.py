from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

from django.db import close_old_connections
from django.test import TransactionTestCase, override_settings, skipUnlessDBFeature

from apps.integrations import tests_google_calendar as fixtures, google_calendar_sync as sync
from apps.integrations.google_calendar_models import GoogleCalendarMirror


@skipUnlessDBFeature("has_select_for_update")
@override_settings(GOOGLE_CALENDAR_ENABLED=True)
class CalendarConcurrencyTests(TransactionTestCase):
    setUp = fixtures.CalendarSyncTests.setUp
    write = fixtures.CalendarSyncTests.write
    delete = fixtures.CalendarSyncTests.delete

    def test_concurrent_workers_reserve_and_insert_one_copy(self):
        barrier = Barrier(2)

        def run():
            close_old_connections()
            try:
                barrier.wait(timeout=15)
                return sync.sync_binding(self.binding.pk)
            finally:
                close_old_connections()

        with ThreadPoolExecutor(max_workers=2) as pool:
            futures = [pool.submit(run) for _ in range(2)]
            results = [future.result(timeout=45) for future in futures]
        self.assertEqual(len(results), 2)
        self.assertEqual(GoogleCalendarMirror.objects.count(), 1)
        self.assertEqual(self.write_mock.call_count, 1)
        self.assertEqual(len(self.remote_events), 1)
