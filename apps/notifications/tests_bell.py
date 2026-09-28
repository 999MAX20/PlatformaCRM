from django.utils import timezone
from rest_framework.test import APITestCase

from apps.accounts.models import User
from apps.businesses.models import Business, BusinessMember
from apps.notifications.models import Notification


class NotificationBellSurfaceTests(APITestCase):
    def setUp(self):
        self.owner = User.objects.create_user(username="bell-owner", email="bell@example.test", password="pass")
        self.business = Business.objects.create(owner=self.owner, name="Bell clinic", slug="bell-clinic")
        BusinessMember.objects.create(business=self.business, user=self.owner, role="owner")
        self.client.force_authenticate(self.owner)

    def test_bell_list_summary_and_mark_all_exclude_future_cancelled_and_outbound(self):
        now = timezone.now()
        defaults = dict(business=self.business, recipient=self.owner, text="Synthetic notification", send_at=now)
        due = Notification.objects.create(**defaults, status="sent")
        outbound = Notification.objects.create(**defaults, channel="sms")
        cancelled = Notification.objects.create(**defaults, status="cancelled")
        future = Notification.objects.create(**{**defaults, "send_at": now + timezone.timedelta(hours=1)})
        response = self.client.get("/api/notifications/", {"surface": "bell"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual([item["id"] for item in response.data["results"]], [due.pk])
        summary = self.client.get("/api/notifications/summary/", {"surface": "bell"})
        self.assertEqual(summary.data["unread"], 1)
        marked = self.client.post("/api/notifications/mark-all-read/?surface=bell")
        self.assertEqual(marked.data["updated"], 1)
        for excluded in (outbound, cancelled, future):
            excluded.refresh_from_db()
            self.assertIsNone(excluded.read_at)
        # General delivery management still has every authorized record.
        general = self.client.get("/api/notifications/")
        self.assertEqual(general.data["count"], 4)
