from datetime import timedelta

from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from apps.businesses.models import BusinessCapability, BusinessMember, BusinessRole, RolePermission
from apps.clients.models import Client
from apps.notifications.personal_selectors import notification_subject, personal_states
from apps.notifications.tests_personal_services import PersonalNotificationFixtures
from apps.scheduling.models import Appointment, Resource
from apps.services.models import Service


class AppointmentFeedLinkTests(PersonalNotificationFixtures, TestCase):
    def setUp(self):
        super().setUp()
        self.resource = Resource.objects.create(business=self.business, name="Feed specialist", linked_user=self.staff)
        self.appointment = Appointment.objects.create(
            business=self.business, resource=self.resource,
            client=Client.objects.create(business=self.business, full_name="Feed client"),
            service=Service.objects.create(business=self.business, name="Feed service"),
            start_at=timezone.now() + timedelta(days=1), end_at=timezone.now() + timedelta(days=1, hours=1),
        )
        self.link = f"/app/appointments/{self.appointment.pk}"
        self.notification = self.work(action_url=self.link)
        self.api = APIClient()
        self.api.force_authenticate(self.staff)

    def url(self, suffix=""):
        return f"/api/notifications/{suffix}?business={self.business.pk}"

    def assert_hidden(self):
        self.assertEqual(self.api.get(self.url()).data["count"], 0)
        self.assertEqual(self.api.get(self.url("summary/")).data["unread"], 0)
        self.assertEqual(self.api.get(self.url(f"{self.notification.pk}/")).status_code, 404)
        self.assertEqual(self.api.post(self.url("mark-all-read/")).data["updated"], 0)
        self.assertIsNone(self.state(self.notification).read_at)

    def test_canonical_link_list_detail_summary_and_read_use_same_scope(self):
        self.notification.action_url += "?token=private-copy"
        self.notification.save(update_fields=["action_url"])
        response = self.api.get(self.url())
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 1)
        row = self.api.get(self.url(f"{self.notification.pk}/")).data
        self.assertEqual(row["action_url"], self.link)
        self.assertEqual(row["text"], "")
        self.assertEqual(row["message_key"], "notification.work.appointments")
        self.assertEqual(self.api.get(self.url("summary/")).data["unread"], 1)
        self.assertEqual(self.api.post(self.url("mark-all-read/")).data["updated"], 1)
        self.assertIsNotNone(self.state(self.notification).read_at)

    def test_reassignment_revokes_current_own_scope(self):
        self.assertTrue(personal_states(actor=self.staff, business=self.business).filter(notification=self.notification).exists())
        self.resource.linked_user = self.peer
        self.resource.save(update_fields=["linked_user"])
        self.assert_hidden()

    def test_foreign_appointment_link_is_not_authorized_by_notification_business(self):
        foreign = Appointment.objects.create(
            business=self.foreign, start_at=self.appointment.start_at, end_at=self.appointment.end_at,
            client=Client.objects.create(business=self.foreign, full_name="Foreign client"),
            service=Service.objects.create(business=self.foreign, name="Foreign service"),
        )
        self.notification.action_url = f"/app/appointments/{foreign.pk}"
        self.notification.save(update_fields=["action_url"])
        self.assert_hidden()

    def test_explicit_deny_and_disabled_capability_hide_canonical_link(self):
        role = BusinessRole.objects.create(business=self.business, name="Denied appointment feed")
        BusinessMember.objects.filter(business=self.business, user=self.staff).update(business_role=role)
        permission = RolePermission.objects.create(
            business_role=role, resource="appointments", action="view", is_allowed=False, scope="none",
        )
        self.assert_hidden()
        permission.is_allowed = True
        permission.scope = "business"
        permission.save(update_fields=["is_allowed", "scope"])
        self.assertEqual(self.api.get(self.url()).data["count"], 1)
        BusinessCapability.objects.update_or_create(
            business=self.business, module_key="appointments", defaults={"is_enabled": False},
        )
        self.assert_hidden()

    def test_revoked_membership_cannot_read_or_change_feed(self):
        BusinessMember.objects.filter(business=self.business, user=self.staff).update(is_active=False)
        self.assertEqual(self.api.get(self.url()).status_code, 403)
        self.assertEqual(self.api.post(self.url("mark-all-read/")).status_code, 403)
        self.assertIsNone(self.state(self.notification).read_at)

    def test_legacy_link_and_canonical_parser_controls(self):
        legacy = f"/app/calendar?appointment={self.appointment.pk}"
        self.assertEqual(notification_subject(legacy)[:2], notification_subject(self.link)[:2])
        self.notification.action_url = legacy
        self.notification.save(update_fields=["action_url"])
        self.assertEqual(self.api.get(self.url()).data["count"], 1)
        for invalid in (
            "/app/appointments/0", "/app/appointments/-1", "/app/appointments/abc",
            "/app/appointments/1/extra", "/app/appointments/١", "/app/appointments/1#fragment",
            "https://example.test/app/appointments/1", "//example.test/app/appointments/1",
        ):
            with self.subTest(invalid=invalid):
                self.assertIsNone(notification_subject(invalid))
