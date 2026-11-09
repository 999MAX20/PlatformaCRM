"""Owner-approved personal-state replacement for the earlier AUD17 shared policy.

Earlier shared UPDATE/scope evidence is retained in the OFFICIAL21 artifact packet.
These tests keep its isolation/replay/rollback cases under the new personal contract.
"""
from unittest.mock import patch

from django.db.models.query import QuerySet
from django.utils import timezone
from rest_framework.test import APITestCase

from apps.businesses.models import BusinessMember, BusinessRole, RolePermission, Team, TeamMember
from apps.notifications.models import Notification, NotificationRecipient
from apps.notifications.tests_personal_services import PersonalNotificationFixtures
from apps.tasks.models import Task


class MarkAllReadAccessTests(PersonalNotificationFixtures, APITestCase):
    def setUp(self):
        super().setUp()
        self.shared = self.publish()
        self.personal = self.work()
        self.peer_notification = self.work(actor=self.peer)

    def mark_all(self, actor=None, *, business=None, suffix=""):
        self.client.force_authenticate(actor or self.staff)
        return self.client.post(f"/api/notifications/mark-all-read/?business={(business or self.business).pk}{suffix}")

    def permission(self, action, *, allowed=False, scope="none"):
        role, _ = BusinessRole.objects.get_or_create(business=self.business, name="Personal notification test")
        BusinessMember.objects.filter(business=self.business, user=self.staff).update(business_role=role)
        RolePermission.objects.update_or_create(business_role=role, resource="notifications", action=action,
                                               defaults={"is_allowed": allowed, "scope": scope})
        return role

    def test_owner_reads_only_own_copy_not_other_recipients(self):
        response = self.mark_all(self.owner)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["updated"], 1)
        self.assertIsNotNone(self.state(self.shared, self.owner).read_at)
        self.assertIsNone(self.state(self.shared, self.staff).read_at)
        self.assertIsNone(self.state(self.personal, self.staff).read_at)

    def test_view_only_can_read_own_feed_without_update(self):
        self.permission("update")
        response = self.mark_all()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["updated"], 2)
        self.assertIsNone(self.state(self.peer_notification, self.peer).read_at)

    def test_explicit_update_deny_does_not_control_personal_read_state(self):
        self.permission("update")
        self.permission("manage", allowed=True, scope="business")
        self.assertEqual(self.mark_all().data["updated"], 2)
        self.assertIsNone(self.state(self.shared, self.peer).read_at)

    def test_team_authority_never_changes_team_members_read_state(self):
        self.permission("update", allowed=True, scope="team")
        team = Team.objects.create(business=self.business, name="Personal test team")
        for user in (self.staff, self.peer):
            TeamMember.objects.create(team=team, member=BusinessMember.objects.get(business=self.business, user=user))
        self.assertEqual(self.mark_all().data["updated"], 2)
        self.assertIsNone(self.state(self.peer_notification, self.peer).read_at)

    def test_manage_authority_never_changes_other_personal_states(self):
        self.permission("manage", allowed=True, scope="business")
        self.assertEqual(self.mark_all().data["updated"], 2)
        self.assertIsNone(self.state(self.shared, self.owner).read_at)

    def test_empty_feed_returns_zero_for_active_member(self):
        Notification.objects.filter(business=self.business).delete()
        self.assertEqual(self.mark_all().data, {"updated": 0})

    def test_notification_view_deny_preserves_announcement_access_only(self):
        self.permission("view")
        self.assertEqual(self.mark_all().data["updated"], 1)
        self.assertIsNotNone(self.state(self.shared).read_at)
        self.assertIsNone(self.state(self.personal).read_at)

    def test_revoked_membership_cannot_change_any_state(self):
        BusinessMember.objects.filter(business=self.business, user=self.staff).update(is_active=False)
        self.assertEqual(self.mark_all().status_code, 403)
        self.assertFalse(NotificationRecipient.objects.filter(read_at__isnull=False).exists())

    def test_foreign_business_is_denied(self):
        self.assertEqual(self.mark_all(business=self.foreign).status_code, 403)
        self.assertFalse(NotificationRecipient.objects.filter(read_at__isnull=False).exists())

    def test_multiple_businesses_require_explicit_selection(self):
        BusinessMember.objects.create(business=self.foreign, user=self.staff, role="admin")
        foreign = self.publish(actor=self.outsider, business=self.foreign)
        self.client.force_authenticate(self.staff)
        self.assertEqual(self.client.post("/api/notifications/mark-all-read/").status_code, 400)
        self.assertEqual(self.mark_all().data["updated"], 2)
        self.assertIsNone(self.state(foreign).read_at)

    def test_current_source_role_revocation_applies_on_next_request(self):
        task = Task.objects.create(business=self.business, title="Scope test", assignee=self.staff)
        work = self.work(action_url=f"/app/tasks?task={task.pk}")
        self.assertEqual(self.mark_all().data["updated"], 3)
        self.change(work, "unread")
        Task.objects.filter(pk=task.pk).update(assignee=self.peer)
        self.assertEqual(self.mark_all().data["updated"], 0)
        self.assertIsNone(self.state(work).read_at)

    def test_display_filters_do_not_silently_narrow_read_all(self):
        self.assertEqual(self.mark_all(suffix="&category=finance&priority=urgent&unread=false").data["updated"], 2)
        self.assertIsNone(self.state(self.peer_notification, self.peer).read_at)

    def test_replay_preserves_first_read_timestamp(self):
        self.assertEqual(self.mark_all().data["updated"], 2)
        first = self.state(self.personal).read_at
        self.assertEqual(self.mark_all().data["updated"], 0)
        self.assertEqual(self.state(self.personal).read_at, first)

    def test_future_cancelled_outbound_and_other_inbox_stay_unchanged(self):
        future = self.work()
        Notification.objects.filter(pk=future.pk).update(send_at=timezone.now() + timezone.timedelta(days=1))
        cancelled = self.work(status="cancelled")
        outbound = self.work(channel="email")
        inbox = self.work(actor=self.peer, action_url="/app/conversations?conversation=999999")
        self.assertEqual(self.mark_all(suffix="&surface=bell").data["updated"], 2)
        for notification, actor in ((future, self.staff), (cancelled, self.staff), (inbox, self.peer)):
            self.assertIsNone(self.state(notification, actor).read_at)
        outbound.refresh_from_db()
        self.assertIsNone(outbound.read_at)

    def test_reassigned_legacy_recipient_does_not_inherit_audience(self):
        Notification.objects.filter(pk=self.personal.pk).update(recipient=self.peer)
        self.assertEqual(self.mark_all().data["updated"], 1)
        self.assertIsNone(self.state(self.personal).read_at)
        self.assertFalse(self.personal.recipient_states.filter(user=self.peer).exists())

    def test_shared_legacy_read_state_is_not_modified(self):
        before = list(Notification.objects.values("pk", "read_at", "updated_at"))
        self.mark_all()
        self.assertEqual(before, list(Notification.objects.values("pk", "read_at", "updated_at")))

    def test_bulk_chunks_roll_back_when_later_database_write_fails(self):
        Notification.objects.bulk_create([
            Notification(business=self.business, recipient=self.staff, text="Synthetic batch", send_at=timezone.now())
            for _ in range(501)
        ])
        original_update = QuerySet.update
        writes = []

        def fail_second_write(queryset, **fields):
            if queryset.model is NotificationRecipient and "read_at" in fields:
                writes.append(fields)
                if len(writes) == 2:
                    raise RuntimeError("Synthetic second-write failure")
            return original_update(queryset, **fields)

        with patch.object(QuerySet, "update", fail_second_write):
            response = self.mark_all()
        self.assertEqual(response.status_code, 500)
        self.assertEqual(len(writes), 2)
        self.assertFalse(NotificationRecipient.objects.filter(read_at__isnull=False).exists())

    def test_read_all_never_records_open_or_acknowledgement(self):
        self.assertEqual(self.mark_all().data["updated"], 2)
        self.assertFalse(NotificationRecipient.objects.filter(opened_at__isnull=False).exists())
        self.assertFalse(NotificationRecipient.objects.filter(acknowledged_at__isnull=False).exists())

    def test_arrival_after_selection_stays_unread(self):
        original_update = QuerySet.update
        arrivals = []

        def arrival_at_write(queryset, **fields):
            if queryset.model is NotificationRecipient and "read_at" in fields and not arrivals:
                arrivals.append(self.work())
            return original_update(queryset, **fields)

        with patch.object(QuerySet, "update", arrival_at_write):
            response = self.mark_all()
        self.assertEqual(response.data["updated"], 2)
        self.assertIsNone(self.state(arrivals[0]).read_at)
