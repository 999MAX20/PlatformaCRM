"""OFFICIAL-13: status projections obey current notification and linked read rights."""
from datetime import timedelta
from unittest.mock import patch

from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.businesses.models import Business, BusinessCapability, BusinessMember, BusinessRole, RolePermission, Team, TeamMember
from apps.clients.models import Client
from apps.core.domain_errors import ModuleDisabled
from apps.notifications.models import Notification
from apps.outreach.services import appointment_automation_status
from apps.scheduling.models import Appointment, Resource
from apps.scheduling.services import APPOINTMENT_REMINDER_LABEL
from apps.services.models import Service


class AutomationStatusAccessTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(username="status-owner", email="status-owner@example.test")
        self.actor = User.objects.create_user(username="status-reader", email="status-reader@example.test")
        self.peer = User.objects.create_user(username="status-peer", email="status-peer@example.test")
        self.business = Business.objects.create(owner=self.owner, name="Status", slug="status-access")
        self.role = BusinessRole.objects.create(business=self.business, name="Status reader")
        self.member = BusinessMember.objects.create(business=self.business, user=self.actor, role="staff", business_role=self.role)
        self.peer_member = BusinessMember.objects.create(business=self.business, user=self.peer, role="staff")
        for resource in ("notifications", "clients", "appointments"):
            RolePermission.objects.create(business_role=self.role, resource=resource, action="view", scope="business")
        self.customer = Client.objects.create(business=self.business, full_name="Visible customer", phone="+77000001122")
        service = Service.objects.create(business=self.business, name="Session")
        resource = Resource.objects.create(business=self.business, name="Specialist", linked_user=self.peer)
        now = timezone.now()
        self.appointment = Appointment.objects.create(business=self.business, client=self.customer, service=service,
            resource=resource, start_at=now, end_at=now + timedelta(hours=1))
        self.mine = self.notification(recipient=self.actor)
        self.api = APIClient()
        self.api.force_authenticate(self.actor)

    def notification(self, **kwargs):
        values = dict(business=self.business, client=self.customer, appointment=self.appointment,
            channel="system", category="sales", status="failed", text="Synthetic reminder",
            send_at=timezone.now(), action_label=APPOINTMENT_REMINDER_LABEL,
            action_url=f"/app/calendar?appointment={self.appointment.pk}")
        values.update(kwargs)
        return Notification.objects.create(**values)

    def permission(self, resource="notifications", *, allowed=True, scope="business"):
        RolePermission.objects.filter(business_role=self.role, resource=resource, action="view").update(is_allowed=allowed, scope=scope)

    def get(self, **params):
        return self.api.get("/api/outreach/campaigns/appointment-automation-status/", {"business": self.business.pk, **params})

    def assert_empty(self, data):
        self.assertEqual(data["total_pending"], 0)
        self.assertEqual(data["total_failed"], 0)
        self.assertEqual(data["failed_notifications"], [])
        self.assertTrue(all(not any(s["counts"].values()) for s in data["scenarios"]))

    def test_denied_resource_returns_no_status_payload(self):
        self.permission(allowed=False)
        response = self.get()
        self.assertEqual(response.status_code, 403, response.data)
        self.assertNotIn("scenarios", response.data)

    def test_direct_denied_or_missing_actor_returns_no_private_status(self):
        self.permission(allowed=False)
        for actor in (self.actor, None):
            with self.subTest(actor=actor):
                self.assert_empty(appointment_automation_status(self.business, actor=actor))

    def test_own_scope_counts_and_limit_exclude_peer_rows(self):
        self.permission(scope="own")
        for _ in range(10):
            self.notification(recipient=self.peer)
        self.notification(recipient=self.peer, status="pending")
        result = self.get()
        self.assertEqual(result.status_code, 200, result.data)
        self.assertEqual(result.data["total_failed"], 1)
        self.assertEqual(result.data["total_pending"], 0)
        self.assertEqual([n["id"] for n in result.data["failed_notifications"]], [self.mine.pk])

    def test_own_preserves_shared_notification_policy(self):
        self.permission(scope="own")
        shared = self.notification(recipient=None)
        result = self.get()
        self.assertEqual(result.data["total_failed"], 2)
        self.assertEqual({n["id"] for n in result.data["failed_notifications"]}, {self.mine.pk, shared.pk})

    def test_team_scope_tracks_membership_and_excludes_shared(self):
        self.permission(scope="team")
        team = Team.objects.create(business=self.business, name="Readers")
        TeamMember.objects.create(team=team, member=self.member)
        peer_membership = TeamMember.objects.create(team=team, member=self.peer_member)
        self.notification(recipient=self.peer)
        self.notification(recipient=None)
        self.assertEqual(self.get().data["total_failed"], 2)
        peer_membership.delete()
        self.assertEqual(self.get().data["total_failed"], 1)

    def test_permission_revocation_between_reads(self):
        self.assertEqual(self.get().status_code, 200)
        self.permission(allowed=False)
        self.assertEqual(self.get().status_code, 403)

    def test_appointment_denial_masks_id_and_link_but_keeps_visible_notification(self):
        self.permission("appointments", allowed=False)
        result = self.get()
        self.assertEqual(result.data["total_failed"], 1)
        row = result.data["failed_notifications"][0]
        self.assertIsNone(row["appointment_id"])
        self.assertEqual(row["action_url"], "")
        self.assertEqual(row["client_phone"], self.customer.phone)

    def test_appointment_own_scope_masks_other_specialists_record(self):
        self.permission("appointments", scope="own")
        row = self.get().data["failed_notifications"][0]
        self.assertIsNone(row["appointment_id"])
        self.assertEqual(row["action_url"], "")

    def test_disabled_appointment_module_masks_links(self):
        BusinessCapability.objects.update_or_create(business=self.business, module_key="appointments", defaults={"is_enabled": False})
        row = self.get().data["failed_notifications"][0]
        self.assertIsNone(row["appointment_id"])
        self.assertEqual(row["action_url"], "")

    def test_client_denial_retains_existing_redaction(self):
        self.permission("clients", allowed=False)
        self.mine.action_url = f"/app/clients?client={self.customer.pk}"
        self.mine.save()
        row = self.get().data["failed_notifications"][0]
        self.assertEqual(row["client_name"], "")
        self.assertEqual(row["client_phone"], "")
        self.assertEqual(row["action_url"], "")

    def test_owner_retains_details_and_eight_row_limit(self):
        self.api.force_authenticate(self.owner)
        for _ in range(9):
            self.notification(recipient=self.peer)
        result = self.get()
        self.assertEqual(result.data["total_failed"], 10)
        self.assertEqual(len(result.data["failed_notifications"]), 8)
        row = result.data["failed_notifications"][0]
        self.assertEqual(row["appointment_id"], self.appointment.pk)
        self.assertEqual(row["client_phone"], self.customer.phone)
        self.assertEqual(row["action_url"], self.mine.action_url)

    def test_other_business_http_and_direct_read_rejected(self):
        foreign = Business.objects.create(owner=self.peer, name="Other", slug="status-other")
        self.notification(business=foreign, recipient=self.peer)
        self.assertEqual(self.get(business=foreign.pk).status_code, 400)
        self.assert_empty(appointment_automation_status(foreign, actor=self.actor))

    def test_inactive_membership_cannot_read_direct_status(self):
        self.member.is_active = False
        self.member.save()
        self.assert_empty(appointment_automation_status(self.business, actor=self.actor))

    def test_empty_business_preserves_shape(self):
        Notification.objects.all().delete()
        result = self.get()
        self.assertEqual(result.status_code, 200)
        self.assertTrue(result.data["enabled"])
        self.assertEqual(len(result.data["scenarios"]), 3)
        self.assert_empty(result.data)

    def test_scope_applies_to_every_count_status(self):
        self.permission(scope="own")
        for status in ("pending", "sent", "failed", "cancelled"):
            self.notification(recipient=self.actor, status=status)
            self.notification(recipient=self.peer, status=status)
        counts = next(s["counts"] for s in self.get().data["scenarios"] if s["label"] == APPOINTMENT_REMINDER_LABEL)
        self.assertEqual(counts, {"pending": 1, "sent": 1, "failed": 2, "cancelled": 1})

    def test_null_appointment_retains_notification(self):
        self.mine.appointment = None
        self.mine.action_url = ""
        self.mine.save()
        self.permission("appointments", allowed=False)
        row = self.get().data["failed_notifications"][0]
        self.assertEqual(row["id"], self.mine.pk)
        self.assertIsNone(row["appointment_id"])

    def test_cross_business_link_is_not_projected_even_for_owner(self):
        foreign = Business.objects.create(owner=self.owner, name="Foreign", slug="status-foreign-link")
        Appointment.objects.filter(pk=self.appointment.pk).update(business=foreign)
        self.api.force_authenticate(self.owner)
        row = self.get().data["failed_notifications"][0]
        self.assertIsNone(row["appointment_id"])
        self.assertEqual(row["action_url"], "")

    def test_endpoint_calls_notification_capability_guard(self):
        # Notifications has no module mapping: this proves guard integration only.
        with patch("apps.outreach.views.assert_resource_enabled", side_effect=ModuleDisabled()) as guard:
            response = self.get()
        self.assertEqual(response.status_code, 403, response.data)
        guard.assert_called_once_with(self.business, "notifications")

    def test_personal_patch_denied_and_legacy_detached_appointment_link_hidden(self):
        self.api.force_authenticate(self.owner)
        response = self.api.patch(f"/api/notifications/{self.mine.pk}/", {"appointment": None}, format="json")
        self.assertEqual(response.status_code, 404, response.data)
        # Personal history is now server-owned. Retain the historical detached
        # data projection regression without reopening the former PATCH route.
        Notification.objects.filter(pk=self.mine.pk).update(appointment=None)
        self.mine.refresh_from_db()
        self.assertIsNone(self.mine.appointment_id)
        self.assertTrue(self.mine.action_url)
        self.api.force_authenticate(self.actor)
        self.permission("appointments", allowed=False)
        row = self.get().data["failed_notifications"][0]
        self.assertIsNone(row["appointment_id"])
        self.assertEqual(row["action_url"], "")

    def test_calendar_url_copies_are_bound_to_visible_appointment(self):
        expected = f"/app/calendar?appointment={self.appointment.pk}"
        for url in ("/app/calendar?appointment=999999", "/app/%63alendar?appointment=999999",
                    "/app/calendar?appointment=999999&appointment=1", "https://example.test/app/calendar?appointment=999999"):
            with self.subTest(url=url):
                Notification.objects.filter(pk=self.mine.pk).update(action_url=url)
                row = self.get().data["failed_notifications"][0]
                self.assertEqual(row["action_url"], expected)

    def test_private_conversation_notification_matches_ordinary_list(self):
        self.notification(recipient=self.peer, action_url="/app/conversations?conversation=123")
        response = self.get()
        self.assertEqual(response.data["total_failed"], 1)
        self.assertEqual([row["id"] for row in response.data["failed_notifications"]], [self.mine.pk])
