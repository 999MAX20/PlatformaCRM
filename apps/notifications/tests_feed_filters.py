from datetime import timedelta
from unittest.mock import patch

from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from apps.notifications.models import Notification
from apps.notifications.tests_personal_services import PersonalNotificationFixtures
from apps.tasks.models import Task


class PersonalFeedFilterTests(PersonalNotificationFixtures, TestCase):
    def setUp(self):
        super().setUp()
        self.api = APIClient()
        self.api.force_authenticate(self.staff)
        self.url = f"/api/notifications/?business={self.business.pk}&surface=bell"

    def ids(self, params=None):
        response = self.api.get("/api/notifications/", {"business": self.business.pk, "surface": "bell", **(params or {})})
        self.assertEqual(response.status_code, 200, response.data)
        return [row["id"] for row in response.data["results"]]

    def test_newest_and_oldest_order_ignore_shared_read_state_and_break_ties(self):
        first, second, third = self.work(), self.work(), self.work()
        now = timezone.now()
        Notification.objects.filter(pk=first.pk).update(send_at=now - timedelta(days=2))
        Notification.objects.filter(pk__in=[second.pk, third.pk]).update(send_at=now)
        Notification.objects.filter(pk=third.pk).update(read_at=now)
        self.change(second, "read")
        self.assertEqual(self.ids(), [third.pk, second.pk, first.pk])
        self.assertEqual(self.ids({"order": "oldest"}), [first.pk, second.pk, third.pk])

    def test_filters_combine_using_private_acknowledgement_and_read_state(self):
        waiting = self.publish()
        read_waiting = self.publish()
        acknowledged = self.publish()
        self.work()
        self.change(read_waiting, "read")
        self.change(acknowledged, "open")
        self.change(acknowledged, "acknowledge")
        self.change(waiting, "open", actor=self.peer)
        self.change(waiting, "acknowledge", actor=self.peer)
        self.assertEqual(set(self.ids({"awaiting_ack": "true"})), {waiting.pk, read_waiting.pk})
        self.assertEqual(self.ids({"awaiting_ack": "true", "unread": "true", "category": "system"}), [waiting.pk])
        self.assertEqual(self.ids({"awaiting_ack": "true", "category": "tasks"}), [])

    def test_period_is_inclusive_and_applied_before_pagination(self):
        now = timezone.now()
        boundary, outside, recent, last_month = [self.work() for _ in range(4)]
        for notification, sent in ((boundary, now - timedelta(days=7)),
                                   (outside, now - timedelta(days=7, seconds=1)),
                                   (recent, now - timedelta(hours=1)),
                                   (last_month, now - timedelta(days=31))):
            Notification.objects.filter(pk=notification.pk).update(send_at=sent)
        with patch("apps.notifications.feed_filters.timezone.now", return_value=now):
            self.assertEqual(self.ids({"period": "7d"}), [recent.pk, boundary.pk])
            self.assertEqual(self.ids({"period": "30d"}), [recent.pk, boundary.pk, outside.pk])
        self.assertEqual(len(self.ids({"period": "all"})), 4)

    def test_invalid_filter_values_return_400(self):
        for params in ({"period": "yesterday"}, {"period": "-1"}, {"order": "text"}, {"awaiting_ack": "maybe"}):
            with self.subTest(params=params):
                response = self.api.get("/api/notifications/", {"business": self.business.pk, "surface": "bell", **params})
                self.assertEqual(response.status_code, 400)
                self.assertIn(next(iter(params)), response.data)

    def test_period_and_order_apply_to_total_and_each_page(self):
        now = timezone.now()
        rows = [self.work() for _ in range(5)]
        for index, row in enumerate(rows):
            Notification.objects.filter(pk=row.pk).update(send_at=now - timedelta(days=index * 3))
        params = {"business": self.business.pk, "surface": "bell", "period": "7d", "order": "oldest"}
        with patch("rest_framework.pagination.PageNumberPagination.page_size", 2):
            first = self.api.get("/api/notifications/", {**params, "page": 1})
            second = self.api.get("/api/notifications/", {**params, "page": 2})
        self.assertEqual(first.status_code, 200)
        self.assertEqual(second.status_code, 200)
        self.assertEqual(first.data["count"], 3)
        self.assertEqual(second.data["count"], 3)
        self.assertEqual([row["id"] for row in first.data["results"]], [rows[2].pk, rows[1].pk])
        self.assertEqual([row["id"] for row in second.data["results"]], [rows[0].pk])
        self.assertIsNotNone(first.data["next"])
        self.assertIsNone(second.data["next"])

    def test_filters_preserve_current_source_recipient_and_tenant_boundary(self):
        own = self.work()
        self.work(actor=self.peer)
        task = Task.objects.create(business=self.business, title="Reassigned", assignee=self.staff)
        self.work(action_url=f"/app/tasks?task={task.pk}")
        Task.objects.filter(pk=task.pk).update(assignee=self.peer)
        Notification.objects.create(business=self.foreign, recipient=self.outsider, text="Foreign", send_at=timezone.now())
        self.assertEqual(self.ids({"period": "7d", "unread": "true"}), [own.pk])
        response = self.api.get(f"/api/notifications/?business={self.foreign.pk}&surface=bell&awaiting_ack=true")
        self.assertEqual(response.status_code, 403)

    def test_filtered_read_all_still_reads_full_personal_feed_without_acknowledging(self):
        first, second = self.publish(), self.publish()
        Notification.objects.filter(pk=first.pk).update(send_at=timezone.now() - timedelta(days=31))
        response = self.api.post(
            f"/api/notifications/mark-all-read/?business={self.business.pk}&surface=bell&period=7d&awaiting_ack=true",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["updated"], 2)
        for notification in (first, second):
            self.assertIsNotNone(self.state(notification).read_at)
            self.assertIsNone(self.state(notification).acknowledged_at)
            self.assertIsNone(self.state(notification, self.peer).read_at)

    def test_list_does_not_change_receipts_and_excludes_future_cancelled_and_external(self):
        visible = self.publish()
        future, cancelled = self.work(), self.work()
        Notification.objects.filter(pk=future.pk).update(send_at=timezone.now() + timedelta(days=1))
        Notification.objects.filter(pk=cancelled.pk).update(status=Notification.Statuses.CANCELLED)
        self.work(channel=Notification.Channels.EMAIL)
        self.assertEqual(self.ids(), [visible.pk])
        state = self.state(visible)
        self.assertIsNone(state.opened_at)
        self.assertIsNone(state.read_at)
        self.assertIsNone(state.acknowledged_at)
