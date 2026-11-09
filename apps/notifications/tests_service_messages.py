from datetime import timedelta
from types import SimpleNamespace

from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.businesses.models import Business, BusinessMember
from apps.core.models import ExportJob, ServiceComponentState
from apps.core.service_status import observe_business_service
from apps.notifications.models import Notification
from apps.notifications.serializers import NotificationSerializer
from apps.notifications.service_messages import service_message_key


class ServiceMessageTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(username="service-copy-owner", email="service-copy@example.com")
        self.other = User.objects.create_user(username="service-copy-other", email="service-other@example.com")
        self.business = Business.objects.create(owner=self.owner, name="Service copy", slug="service-copy")
        self.foreign = Business.objects.create(owner=self.other, name="Other", slug="service-other")
        self.api = APIClient()
        self.api.force_authenticate(self.owner)
        self.now = timezone.now()
        self.row = ServiceComponentState.objects.create(business=self.business, component="exports",
            state="degraded", episode=2, observed_at=self.now)

    def notification(self, **overrides):
        values = dict(business=self.business, recipient=self.owner, text="PRIVATE old customer text",
                      send_at=self.now, status="sent", provider_reference=f"service-status:{self.row.pk}:1:started")
        values.update(overrides)
        return Notification.objects.create(**values)

    def serialize(self, notification):
        return NotificationSerializer(notification, context={"personal_feed": True,
            "request": SimpleNamespace(user=self.owner)}).data

    def test_all_components_and_transitions_use_only_whitelisted_keys(self):
        for component in ServiceComponentState.Components.values:
            self.row.component = component
            self.row.save(update_fields=["component"])
            for transition in ("started", "recovered"):
                with self.subTest(component=component, transition=transition):
                    notification = self.notification(provider_reference=f"service-status:{self.row.pk}:1:{transition}")
                    data = self.serialize(notification)
                    self.assertEqual(data["message_key"], f"notification.service.{component}.{transition}")
                    for field in ("text", "provider_reference", "last_error", "action_url", "action_label"):
                        self.assertEqual(data[field], "")

    def test_invalid_foreign_or_future_reference_keeps_generic_redacted_message(self):
        foreign = ServiceComponentState.objects.create(business=self.foreign, component="files",
            state="healthy", episode=1, observed_at=self.now)
        references = ["", f"service-status:{foreign.pk}:1:started", f"service-status:{self.row.pk}:3:started",
            f"service-status:{self.row.pk}:0:started", f"service-status:{self.row.pk}:1:private",
            f"service-status:{self.row.pk}:1:started\n", "service-status:999999999:1:started"]
        for reference in references:
            with self.subTest(reference=reference):
                data = self.serialize(self.notification(provider_reference=reference))
                self.assertEqual(data["message_key"], "notification.work.notifications")
                self.assertEqual(data["text"], "")

    def test_non_service_work_and_announcements_keep_existing_policy(self):
        for overrides in ({"category": "tasks"}, {"author": self.owner}, {"action_url": "/app/settings"}):
            with self.subTest(overrides=overrides):
                data = self.serialize(self.notification(**overrides))
                self.assertFalse(data["message_key"].startswith("notification.service."))
                self.assertEqual(data["text"], "")
        data = self.serialize(self.notification(kind="announcement", text="Approved announcement"))
        self.assertEqual(data["text"], "Approved announcement")
        self.assertEqual(data["message_key"], "")

    def test_service_state_lookup_is_batched_per_business(self):
        notifications = [self.notification() for _ in range(5)]
        context = {}
        with self.assertNumQueries(1):
            for notification in notifications:
                self.assertEqual(service_message_key(notification, context), "notification.service.exports.started")

    def test_real_producer_start_and_recovery_reach_personal_api(self):
        self.row.delete()
        job = ExportJob.objects.create(business=self.business, actor=self.owner, kind="entity", export_key="clients")
        ExportJob.objects.filter(pk=job.pk).update(created_at=self.now - timedelta(hours=1))
        observe_business_service(self.business.pk, now=self.now)
        ExportJob.objects.filter(pk=job.pk).update(status="completed")
        observe_business_service(self.business.pk, now=self.now + timedelta(seconds=1))
        response = self.api.get(f"/api/notifications/?business={self.business.pk}")
        self.assertEqual(response.status_code, 200)
        rows = response.data["results"]
        self.assertSetEqual({row["message_key"] for row in rows},
                           {"notification.service.exports.started", "notification.service.exports.recovered"})
        self.assertTrue(all(row["text"] == row["provider_reference"] == "" for row in rows))

    def test_personal_api_preserves_recipient_tenant_and_revocation_boundary(self):
        notification = self.notification()
        BusinessMember.objects.create(business=self.business, user=self.other, role="admin")
        self.api.force_authenticate(self.other)
        url = f"/api/notifications/{notification.pk}/?business={self.business.pk}"
        self.assertEqual(self.api.get(url).status_code, 404)
        self.api.force_authenticate(self.owner)
        self.assertEqual(self.api.get(url).status_code, 200)
        self.assertEqual(self.api.get(f"/api/notifications/?business={self.foreign.pk}").status_code, 403)
        Notification.objects.filter(pk=notification.pk).update(revoked_at=self.now)
        self.assertEqual(self.api.get(url).status_code, 404)
