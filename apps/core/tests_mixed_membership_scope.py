from django.utils import timezone
from rest_framework.test import APITestCase

from apps.accounts.models import User
from apps.businesses.models import Business, BusinessMember
from apps.notifications.models import Notification
from apps.tasks.models import Task


class MixedMembershipScopeTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="mixed-owner", email="mixed@example.test")
        self.other = User.objects.create_user(username="other-owner", email="other@example.test")
        self.owned = Business.objects.create(owner=self.user, name="Owned", slug="mixed-owned")
        self.joined = Business.objects.create(owner=self.other, name="Joined", slug="mixed-joined")
        self.foreign = Business.objects.create(owner=self.other, name="Foreign", slug="mixed-foreign")
        BusinessMember.objects.create(business=self.owned, user=self.user, role="owner")
        self.membership = BusinessMember.objects.create(business=self.joined, user=self.user, role="operator")
        self.client.force_authenticate(self.user)

    def test_tasks_combine_business_and_own_scope_without_leaking_other_assignments(self):
        owned = Task.objects.create(business=self.owned, title="Owned", assignee=self.other)
        assigned = Task.objects.create(business=self.joined, title="Assigned", assignee=self.user)
        hidden = Task.objects.create(business=self.joined, title="Other assignment", assignee=self.other)
        foreign = Task.objects.create(business=self.foreign, title="Foreign", assignee=self.user)
        archived = Task.objects.create(business=self.owned, title="Archived", is_archived=True)
        response = self.client.get("/api/tasks/")
        self.assertEqual(response.status_code, 200)
        self.assertCountEqual([row["id"] for row in response.data["results"]], [owned.pk, assigned.pk])
        for task in (hidden, foreign, archived):
            self.assertEqual(self.client.get(f"/api/tasks/{task.pk}/").status_code, 404)
        self.membership.is_active = False
        self.membership.save(update_fields=["is_active"])
        response = self.client.get("/api/tasks/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual([row["id"] for row in response.data["results"]], [owned.pk])
        self.assertEqual(self.client.get(f"/api/tasks/{assigned.pk}/").status_code, 404)

    def test_bell_combines_business_and_own_scope_and_counts_each_visible_notification_once(self):
        def notification(business, recipient):
            return Notification.objects.create(business=business, recipient=recipient, text="Synthetic", send_at=timezone.now())

        owned = notification(self.owned, self.user)
        assigned = notification(self.joined, self.user)
        broadcast = notification(self.joined, None)
        hidden = notification(self.joined, self.other)
        foreign = notification(self.foreign, self.user)
        response = self.client.get("/api/notifications/", {"surface": "bell"})
        self.assertEqual(response.status_code, 200)
        self.assertCountEqual([row["id"] for row in response.data["results"]], [owned.pk, assigned.pk, broadcast.pk])
        summary = self.client.get("/api/notifications/summary/", {"surface": "bell"})
        self.assertEqual(summary.status_code, 200)
        self.assertEqual(summary.data["unread"], 3)
        self.assertEqual(self.client.post("/api/notifications/mark-all-read/?surface=bell").data["updated"], 3)
        for excluded in (hidden, foreign):
            excluded.refresh_from_db()
            self.assertIsNone(excluded.read_at)
