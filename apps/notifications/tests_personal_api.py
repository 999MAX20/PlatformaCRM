from uuid import uuid4

from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from apps.businesses.models import BusinessMember, BusinessRole, RolePermission
from apps.core.models import AuditLog
from apps.notifications.models import Notification
from apps.notifications.tests_personal_services import PersonalNotificationFixtures
from apps.tasks.models import Task


class PersonalNotificationAPITests(PersonalNotificationFixtures, TestCase):
    def setUp(self):
        super().setUp()
        self.api = APIClient()
        self.api.force_authenticate(self.staff)

    def url(self, suffix="", business=None):
        return f"/api/notifications/{suffix}?business={(business or self.business).pk}"

    def test_http_personal_list_detail_summary_and_read_share_scope(self):
        announcement = self.publish()
        peer = self.work(actor=self.peer)
        response = self.api.get(self.url())
        self.assertEqual(response.status_code, 200)
        self.assertEqual([row["id"] for row in response.data["results"]], [announcement.pk])
        self.assertEqual(self.api.get(self.url("summary/")).data["unread"], 1)
        self.assertEqual(self.api.get(self.url(f"{peer.pk}/")).status_code, 404)
        self.assertEqual(self.api.post(self.url(f"{peer.pk}/mark-read/")).status_code, 404)
        response = self.api.post(self.url(f"{announcement.pk}/mark-read/"))
        self.assertEqual(response.status_code, 200)
        self.assertIsNotNone(response.data["read_at"])
        self.assertIsNone(response.data["opened_at"])
        self.assertIsNone(response.data["acknowledged_at"])
        self.assertEqual(self.api.get(self.url("summary/")).data["unread"], 0)

    def deny_notification_view(self):
        role = BusinessRole.objects.create(business=self.business, name="No notification VIEW")
        RolePermission.objects.create(business_role=role, resource="notifications", action="view",
                                      is_allowed=False, scope="none")
        BusinessMember.objects.filter(business=self.business, user=self.staff).update(business_role=role)

    def test_http_announcement_flow_does_not_require_notification_view(self):
        self.deny_notification_view()
        notification = self.publish()
        self.assertEqual(self.api.get(self.url()).data["count"], 1)
        self.assertEqual(self.api.get(self.url(f"{notification.pk}/")).status_code, 200)
        for action in ("mark-read", "mark-unread", "open", "acknowledge"):
            with self.subTest(action=action):
                response = self.api.post(self.url(f"{notification.pk}/{action}/"))
                self.assertEqual(response.status_code, 200, response.data)
        self.assertIsNotNone(self.state(notification).acknowledged_at)
        self.assertIsNone(self.state(notification, self.peer).read_at)
        self.assertEqual(self.api.get(self.url(f"{notification.pk}/announcement-recipients/")).status_code, 403)

    def test_http_work_uses_source_access_even_without_notification_view(self):
        self.deny_notification_view()
        task = Task.objects.create(business=self.business, title="Own task", assignee=self.staff)
        notification = self.work(action_url=f"/app/tasks?task={task.pk}")
        self.assertEqual(self.api.get(self.url(f"{notification.pk}/")).status_code, 200)
        self.assertEqual(self.api.post(self.url(f"{notification.pk}/mark-read/")).status_code, 200)
        Task.objects.filter(pk=task.pk).update(assignee=self.peer)
        for method, suffix in ((self.api.get, ""), (self.api.post, "mark-unread/"), (self.api.post, "open/")):
            self.assertEqual(method(self.url(f"{notification.pk}/{suffix}")).status_code, 404)

    def test_personal_access_does_not_bypass_external_notification_permissions(self):
        self.deny_notification_view()
        notification = self.work(channel=Notification.Channels.EMAIL)
        self.assertEqual(self.api.get(self.url(f"{notification.pk}/")).status_code, 404)
        for action in ("mark-read", "mark-unread", "retry", "cancel", "mark-sent"):
            self.assertEqual(self.api.post(self.url(f"{notification.pk}/{action}/")).status_code, 404)

    def test_delivery_actions_cannot_change_shared_work_or_recipient_history(self):
        notification = Notification.objects.create(business=self.business, text="Shared work", send_at=timezone.now())
        before = Notification.objects.values().get(pk=notification.pk)
        receipts = list(notification.recipient_states.order_by("pk").values())
        audit_count = AuditLog.objects.count()
        self.api.force_authenticate(self.owner)
        for action in ("cancel", "mark-sent", "retry"):
            response = self.api.post(self.url(f"{notification.pk}/{action}/"))
            self.assertEqual(response.status_code, 400, response.data)
        self.assertEqual(Notification.objects.values().get(pk=notification.pk), before)
        self.assertEqual(list(notification.recipient_states.order_by("pk").values()), receipts)
        self.assertEqual(AuditLog.objects.count(), audit_count)
        self.api.force_authenticate(self.staff)
        self.assertEqual(self.api.get(self.url(f"{notification.pk}/")).status_code, 200)

    def test_http_read_all_ignores_display_filters_and_never_acknowledges(self):
        first = self.publish(priority="normal")
        second = self.publish(priority="urgent")
        response = self.api.post(self.url("mark-all-read/") + "&priority=urgent&unread=false")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data, {"updated": 2})
        self.assertEqual(self.api.post(self.url("mark-all-read/")).data, {"updated": 0})
        for notification in (first, second):
            self.assertIsNone(self.state(notification).acknowledged_at)
            self.assertIsNone(self.state(notification).opened_at)
            self.assertIsNone(self.state(notification, self.peer).read_at)

    def test_http_open_ack_and_monitor_are_separate(self):
        notification = self.publish()
        self.assertEqual(self.api.post(self.url(f"{notification.pk}/acknowledge/")).status_code, 409)
        opened = self.api.post(self.url(f"{notification.pk}/open/"))
        self.assertEqual(opened.status_code, 200)
        self.assertIsNotNone(opened.data["opened_at"])
        self.assertIsNone(opened.data["acknowledged_at"])
        acknowledged = self.api.post(self.url(f"{notification.pk}/acknowledge/"))
        self.assertEqual(acknowledged.status_code, 200)
        self.assertIsNotNone(acknowledged.data["acknowledged_at"])
        self.assertEqual(self.api.get(self.url(f"{notification.pk}/announcement-recipients/")).status_code, 403)
        self.api.force_authenticate(self.admin)
        monitor = self.api.get(self.url(f"{notification.pk}/announcement-recipients/"))
        self.assertEqual(monitor.status_code, 200)
        self.assertEqual(monitor.data["announcement"]["opened_count"], 1)
        self.assertEqual(monitor.data["announcement"]["acknowledged_count"], 1)
        self.assertEqual(monitor.data["count"], 5)

    def test_http_publish_owner_admin_only_and_replay(self):
        body = {"text": "For everyone", "priority": "normal", "publication_key": str(uuid4())}
        for actor in (self.staff, self.marketer):
            self.api.force_authenticate(actor)
            self.assertEqual(self.api.post(self.url("announcements/"), body, format="json").status_code, 403)
        self.api.force_authenticate(self.admin)
        published = self.api.post(self.url("announcements/"), body, format="json")
        self.assertEqual(published.status_code, 201)
        self.assertEqual(published.data["recipient_count"], 5)
        replay = self.api.post(self.url("announcements/"), body, format="json")
        self.assertEqual(replay.status_code, 200)
        self.assertEqual(replay.data["id"], published.data["id"])
        self.assertTrue(self.api.get(self.url("summary/")).data["can_manage_announcements"])

    def test_http_cannot_spoof_recipient_timestamp_author_or_content(self):
        notification = self.publish()
        for action in ("mark-read", "mark-unread", "open", "acknowledge"):
            response = self.api.post(self.url(f"{notification.pk}/{action}/"),
                                     {"user": self.peer.pk, "read_at": "2020-01-01"}, format="json")
            self.assertEqual(response.status_code, 400)
        self.api.force_authenticate(self.owner)
        response = self.api.post(self.url("announcements/"), {"text": "Synthetic", "publication_key": str(uuid4()),
                                                              "recipient": self.peer.pk}, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(self.api.patch(self.url(f"{notification.pk}/"), {"text": "Changed"}, format="json").status_code, 400)
        self.assertEqual(self.api.delete(self.url(f"{notification.pk}/")).status_code, 400)
        for action in ("cancel", "retry", "mark-sent"):
            self.assertEqual(self.api.post(self.url(f"{notification.pk}/{action}/")).status_code, 400)
        notification.refresh_from_db()
        self.assertEqual(notification.text, "Announcement")
        self.assertIsNone(notification.revoked_at)

    def test_http_work_snapshot_is_not_a_field_permission_bypass(self):
        task = Task.objects.create(business=self.business, title="Visible task", assignee=self.staff)
        notification = self.work(action_url=f"/app/tasks?task={task.pk}&token=private-copy")
        response = self.api.get(self.url(f"{notification.pk}/"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["text"], "")
        self.assertEqual(response.data["message_key"], "notification.work.tasks")
        self.assertEqual(response.data["action_url"], f"/app/tasks?task={task.pk}")
        Task.objects.filter(pk=task.pk).update(assignee=self.peer)
        self.assertEqual(self.api.get(self.url()).data["count"], 0)
        self.assertEqual(self.api.get(self.url("summary/")).data["unread"], 0)
        self.assertEqual(self.api.get(self.url(f"{notification.pk}/")).status_code, 404)

    def test_http_current_business_is_required_when_ambiguous(self):
        BusinessMember.objects.create(business=self.foreign, user=self.staff, role="specialist")
        self.publish()
        self.publish(actor=self.outsider, business=self.foreign)
        self.assertEqual(self.api.post("/api/notifications/mark-all-read/").status_code, 400)
        self.assertEqual(self.api.get("/api/notifications/summary/?business=0").status_code, 400)
        self.assertEqual(self.api.post(self.url("mark-all-read/")).data["updated"], 1)
        self.assertEqual(self.api.get(self.url("summary/", self.foreign)).data["unread"], 1)

    def test_http_foreign_announcement_monitor_and_revoke_are_forbidden(self):
        notification = self.publish(actor=self.outsider, business=self.foreign)
        self.api.force_authenticate(self.owner)
        self.assertEqual(self.api.get(self.url(f"{notification.pk}/announcement-recipients/")).status_code, 404)
        self.assertEqual(self.api.post(self.url(f"{notification.pk}/revoke-announcement/")).status_code, 404)
        self.assertEqual(self.api.get(self.url("announcements/", self.foreign)).status_code, 403)

    def test_http_revoke_retains_monitoring_and_disappears_from_feed(self):
        notification = self.publish()
        self.api.post(self.url(f"{notification.pk}/open/"))
        self.api.force_authenticate(self.admin)
        self.assertEqual(self.api.post(self.url(f"{notification.pk}/revoke-announcement/")).status_code, 200)
        monitoring = self.api.get(self.url(f"{notification.pk}/announcement-recipients/"))
        self.assertEqual(monitoring.status_code, 200)
        self.assertEqual(monitoring.data["announcement"]["opened_count"], 1)
        self.api.force_authenticate(self.staff)
        self.assertEqual(self.api.get(self.url("summary/")).data["unread"], 0)
        self.assertEqual(self.api.post(self.url(f"{notification.pk}/acknowledge/")).status_code, 404)
