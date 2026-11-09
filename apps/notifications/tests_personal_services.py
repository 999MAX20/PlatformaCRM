from uuid import uuid4
from unittest.mock import patch

from django.test import TestCase
from django.utils import timezone
from rest_framework.exceptions import NotFound, PermissionDenied, ValidationError

from apps.accounts.models import User
from apps.businesses.models import Business, BusinessCapability, BusinessMember, BusinessRole, RolePermission
from apps.core.domain_errors import IdempotencyConflict, InvalidTransition
from apps.core.models import AuditLog
from apps.notifications.announcements import publish_announcement, revoke_announcement
from apps.notifications.models import Notification, NotificationPreference, NotificationRecipient
from apps.notifications.personal_selectors import personal_business, personal_states
from apps.notifications.personal_services import change_personal_state, read_personal_feed
from apps.tasks.models import Task


class PersonalNotificationFixtures:
    def setUp(self):
        self.owner = self.user("owner")
        self.admin = self.user("admin")
        self.staff = self.user("staff")
        self.peer = self.user("peer")
        self.marketer = self.user("marketer")
        self.outsider = self.user("outsider")
        self.business = Business.objects.create(name="Personal feed", slug="personal-feed", owner=self.owner)
        self.foreign = Business.objects.create(name="Foreign", slug="personal-foreign", owner=self.outsider)
        for user, role in ((self.admin, "admin"), (self.staff, "specialist"), (self.peer, "specialist"), (self.marketer, "marketer")):
            BusinessMember.objects.create(business=self.business, user=user, role=role)

    def user(self, name):
        return User.objects.create_user(username="personal-" + name, email=f"personal-{name}@example.com")

    def publish(self, **kwargs):
        args = dict(actor=self.owner, business=self.business, text="Announcement", priority="normal", publication_key=uuid4())
        args.update(kwargs)
        return publish_announcement(**args)[0]

    def state(self, notification, actor=None):
        return NotificationRecipient.objects.get(notification=notification, user=actor or self.staff)

    def change(self, notification, action, actor=None):
        return change_personal_state(actor=actor or self.staff, business=self.business, notification_id=notification.pk, action=action)

    def work(self, actor=None, **kwargs):
        return Notification.objects.create(business=self.business, recipient=actor or self.staff, text="Private snapshot",
                                           send_at=timezone.now(), **kwargs)


class PersonalNotificationServicesTests(PersonalNotificationFixtures, TestCase):
    def test_only_owner_and_admin_can_publish_even_when_marketer_has_manage(self):
        self.publish()
        self.publish(actor=self.admin)
        for actor in (self.staff, self.marketer, self.outsider):
            with self.assertRaises(PermissionDenied):
                self.publish(actor=actor)
        self.assertEqual(Notification.objects.filter(kind="announcement").count(), 2)

    def test_announcement_bypasses_work_section_and_notification_preferences(self):
        role = BusinessRole.objects.create(business=self.business, name="No notification management")
        for action in ("view", "update", "manage"):
            RolePermission.objects.create(business_role=role, resource="notifications", action=action, is_allowed=False, scope="none")
        BusinessMember.objects.filter(business=self.business, user=self.staff).update(business_role=role)
        NotificationPreference.objects.create(business=self.business, user=self.staff, category="system", in_app_enabled=False)
        announcement = self.publish()
        self.assertEqual(list(personal_states(actor=self.staff, business=self.business).values_list("notification_id", flat=True)), [announcement.pk])
        self.change(announcement, "read")
        self.assertIsNotNone(self.state(announcement).read_at)

    def test_read_open_and_acknowledgement_are_independent_between_users(self):
        announcement = self.publish()
        self.change(announcement, "read")
        state = self.state(announcement)
        self.assertIsNotNone(state.read_at)
        self.assertIsNone(state.opened_at)
        self.assertIsNone(state.acknowledged_at)
        self.assertIsNone(self.state(announcement, self.peer).read_at)
        with self.assertRaises(InvalidTransition):
            self.change(announcement, "acknowledge")
        self.change(announcement, "open")
        self.change(announcement, "acknowledge")
        self.change(announcement, "unread")
        state.refresh_from_db()
        self.assertIsNone(state.read_at)
        self.assertIsNotNone(state.opened_at)
        self.assertIsNotNone(state.acknowledged_at)
        self.assertIsNone(self.state(announcement, self.peer).acknowledged_at)

    def test_repeated_actions_keep_first_timestamps_and_single_ack_audit(self):
        announcement = self.publish()
        first = self.change(announcement, "open")
        ack = self.change(announcement, "acknowledge")
        self.change(announcement, "open")
        self.change(announcement, "acknowledge")
        current = self.state(announcement)
        self.assertEqual(current.opened_at, first.opened_at)
        self.assertEqual(current.read_at, first.read_at)
        self.assertEqual(current.acknowledged_at, ack.acknowledged_at)
        self.assertEqual(AuditLog.objects.filter(metadata__kind="notification_acknowledged").count(), 1)

    def test_work_cannot_be_acknowledged(self):
        notification = self.work()
        self.change(notification, "open")
        with self.assertRaises(InvalidTransition):
            self.change(notification, "acknowledge")

    def test_no_owner_or_peer_write_to_someone_elses_personal_notification(self):
        notification = self.work()
        for actor in (self.owner, self.peer):
            with self.assertRaises(NotFound):
                self.change(notification, "read", actor=actor)
        self.assertIsNone(self.state(notification).read_at)

    def test_foreign_and_revoked_members_cannot_read_or_mutate(self):
        announcement = self.publish()
        with self.assertRaises(PermissionDenied):
            personal_business(actor=self.staff, business_id=self.foreign.pk)
        BusinessMember.objects.filter(business=self.business, user=self.staff).update(is_active=False)
        with self.assertRaises(PermissionDenied):
            self.change(announcement, "open")
        self.assertIsNone(self.state(announcement).opened_at)

    def test_disabled_user_is_denied_even_with_stale_actor_object(self):
        announcement = self.publish()
        User.objects.filter(pk=self.staff.pk).update(is_active=False)
        with self.assertRaises(PermissionDenied):
            self.change(announcement, "read")
        self.assertIsNone(self.state(announcement).read_at)

    def test_direct_selector_does_not_reuse_stale_module_flags(self):
        task = Task.objects.create(business=self.business, title="Module test", assignee=self.staff)
        notification = self.work(action_url=f"/app/tasks?task={task.pk}")
        self.assertTrue(personal_states(actor=self.staff, business=self.business).filter(notification=notification).exists())
        BusinessCapability.objects.update_or_create(business=self.business, module_key="tasks", defaults={"is_enabled": False})
        self.assertFalse(personal_states(actor=self.staff, business=self.business).filter(notification=notification).exists())

    def test_rejoined_member_receives_no_announcements_published_during_absence(self):
        member = BusinessMember.objects.get(business=self.business, user=self.staff)
        member.is_active = False
        member.save()
        announcement = self.publish()
        member.is_active = True
        member.save()
        self.assertFalse(personal_states(actor=self.staff, business=self.business).filter(notification=announcement).exists())

    def test_new_member_does_not_receive_old_announcement(self):
        announcement = self.publish()
        BusinessMember.objects.create(business=self.business, user=self.outsider, role="specialist")
        self.assertFalse(personal_states(actor=self.outsider, business=self.business).filter(notification=announcement).exists())

    def test_publish_retry_is_idempotent_and_does_not_expand_audience(self):
        key = uuid4()
        first = self.publish(publication_key=key)
        BusinessMember.objects.create(business=self.business, user=self.outsider, role="specialist")
        retry = self.publish(publication_key=key)
        self.assertEqual(first.pk, retry.pk)
        self.assertFalse(retry.recipient_states.filter(user=self.outsider).exists())
        self.assertEqual(AuditLog.objects.filter(metadata__kind="announcement_published").count(), 1)
        with self.assertRaises(IdempotencyConflict):
            self.publish(publication_key=key, text="Changed")

    def test_invalid_publication_does_not_write(self):
        for kwargs in ({"text": " "}, {"text": "x" * 4001}, {"priority": "invalid"}, {"publication_key": None}):
            with self.assertRaises(ValidationError):
                self.publish(**kwargs)
        self.assertFalse(Notification.objects.exists())

    def test_publication_and_audience_roll_back_when_audit_fails(self):
        with patch("apps.notifications.announcements.write_actor_audit_log", side_effect=RuntimeError("synthetic")):
            with self.assertRaises(RuntimeError):
                self.publish()
        self.assertFalse(Notification.objects.exists())
        self.assertFalse(NotificationRecipient.objects.exists())

    def test_revoke_hides_feed_but_preserves_history(self):
        announcement = self.publish()
        self.change(announcement, "open")
        with self.assertRaises(PermissionDenied):
            revoke_announcement(actor=self.marketer, business=self.business, notification_id=announcement.pk)
        revoke_announcement(actor=self.admin, business=self.business, notification_id=announcement.pk)
        self.assertFalse(personal_states(actor=self.staff, business=self.business).exists())
        self.assertIsNotNone(self.state(announcement).opened_at)
        with self.assertRaises(NotFound):
            self.change(announcement, "acknowledge")

    def test_read_all_changes_only_current_business_and_never_open_or_ack(self):
        own = self.publish()
        BusinessMember.objects.create(business=self.foreign, user=self.staff, role="specialist")
        foreign = self.publish(actor=self.outsider, business=self.foreign)
        self.assertEqual(read_personal_feed(actor=self.staff, business=self.business), 1)
        self.assertEqual(read_personal_feed(actor=self.staff, business=self.business), 0)
        state = self.state(own)
        self.assertIsNotNone(state.read_at)
        self.assertIsNone(state.opened_at)
        self.assertIsNone(state.acknowledged_at)
        self.assertIsNone(self.state(own, self.peer).read_at)
        self.assertIsNone(self.state(foreign).read_at)

    def test_work_source_access_is_rechecked_before_list_count_and_write(self):
        task = Task.objects.create(business=self.business, title="Private task", assignee=self.staff)
        notification = self.work(action_url=f"/app/tasks?task={task.pk}")
        self.assertTrue(personal_states(actor=self.staff, business=self.business).filter(notification=notification).exists())
        Task.objects.filter(pk=task.pk).update(assignee=self.peer)
        self.assertFalse(personal_states(actor=self.staff, business=self.business).filter(notification=notification).exists())
        self.assertEqual(read_personal_feed(actor=self.staff, business=self.business), 0)
        with self.assertRaises(NotFound):
            self.change(notification, "read")

    def test_broad_section_view_does_not_subscribe_to_peers_events(self):
        notification = self.work(actor=self.peer)
        self.assertFalse(personal_states(actor=self.owner, business=self.business).filter(notification=notification).exists())

    def test_future_cancelled_unknown_and_foreign_links_are_hidden(self):
        future = self.publish()
        Notification.objects.filter(pk=future.pk).update(send_at=timezone.now() + timezone.timedelta(days=1))
        cancelled = self.publish()
        Notification.objects.filter(pk=cancelled.pk).update(status="cancelled")
        foreign_task = Task.objects.create(business=self.foreign, title="Foreign")
        self.work(action_url=f"/app/tasks?task={foreign_task.pk}")
        self.work(action_url="https://example.invalid/private")
        self.assertFalse(personal_states(actor=self.staff, business=self.business).exists())
