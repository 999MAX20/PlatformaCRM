from datetime import timedelta
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from unittest.mock import patch

from django.db import close_old_connections
from django.test import TestCase, TransactionTestCase, skipUnlessDBFeature
from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.automations.models import AutomationRun
from apps.businesses.models import Business, BusinessMember
from apps.core.models import ExportJob, FileAttachment, ServiceComponentState
from apps.core.service_status import business_service_status, observe_business_service, observe_service_batch, platform_service_status
from apps.notifications.models import Notification, NotificationPreference


class ServiceObservationTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(username="service-owner", email="service-owner@example.com")
        self.business = Business.objects.create(owner=self.owner, name="Service clinic", slug="service-clinic")
        self.now = timezone.now()

    def overdue_export(self):
        job = ExportJob.objects.create(business=self.business, actor=self.owner, kind="entity", export_key="clients")
        ExportJob.objects.filter(pk=job.pk).update(created_at=self.now - timedelta(hours=1))
        return job

    def test_start_repeat_recovery_recurrence_and_freshness(self):
        self.assertEqual(business_service_status(self.business)["status"], "unknown")
        job = self.overdue_export()
        first = observe_business_service(self.business.pk, now=self.now)
        self.assertEqual([(row.component, event) for row, event in first], [("exports", "started")])
        self.assertEqual(observe_business_service(self.business.pk, now=self.now + timedelta(seconds=1)), [])
        stale = business_service_status(self.business, now=self.now + timedelta(minutes=4))
        self.assertEqual(stale["status"], "unknown")
        item = next(item for item in stale["components"] if item["component"] == "exports")
        self.assertEqual(item["last_state"], "degraded")
        self.assertIsNone(item["recovered_at"])
        self.assertEqual(Notification.objects.count(), 1)
        ExportJob.objects.filter(pk=job.pk).update(status="succeeded")
        recovered = observe_business_service(self.business.pk, now=self.now + timedelta(minutes=5))
        self.assertEqual([(row.episode, event) for row, event in recovered], [(1, "recovered")])
        ExportJob.objects.filter(pk=job.pk).update(status="pending")
        repeated = observe_business_service(self.business.pk, now=self.now + timedelta(minutes=6))
        self.assertEqual([(row.episode, event) for row, event in repeated], [(2, "started")])
        self.assertEqual(Notification.objects.count(), 3)
        self.assertEqual(Notification.objects.filter(status="sent", recipient=self.owner).count(), 3)
        self.assertEqual(Notification.objects.filter(text__contains="устранена").count(), 1)

    def test_old_observation_cannot_overwrite_recovery(self):
        job = self.overdue_export()
        observe_business_service(self.business.pk, now=self.now)
        ExportJob.objects.filter(pk=job.pk).update(status="succeeded")
        observe_business_service(self.business.pk, now=self.now + timedelta(minutes=1))
        ExportJob.objects.filter(pk=job.pk).update(status="pending")
        self.assertEqual(observe_business_service(self.business.pk, now=self.now), [])
        self.assertEqual(ServiceComponentState.objects.get(business=self.business, component="exports").state, "healthy")
        self.assertEqual(Notification.objects.count(), 2)

    def test_only_active_owner_and_admin_receive_notices_with_preferences(self):
        admin = User.objects.create_user(username="service-admin", email="service-admin@example.com")
        BusinessMember.objects.create(business=self.business, user=admin, role="admin")
        for index, (role, member_active, user_active) in enumerate([
            ("manager", True, True), ("operator", True, True), ("admin", False, True), ("admin", True, False),
        ]):
            user = User.objects.create_user(username=f"excluded-{index}", email=f"excluded-{index}@example.com", is_active=user_active)
            BusinessMember.objects.create(business=self.business, user=user, role=role, is_active=member_active)
        other = Business.objects.create(owner=self.owner, name="Other", slug="notification-other")
        outsider = User.objects.create_user(username="other-admin", email="other-admin@example.com")
        BusinessMember.objects.create(business=other, user=outsider, role="admin")
        job = self.overdue_export()
        observe_business_service(self.business.pk, now=self.now)
        self.assertEqual(set(Notification.objects.values_list("recipient_id", flat=True)), {self.owner.pk, admin.pk})
        self.assertFalse(Notification.objects.exclude(business=self.business).exists())
        api = APIClient()
        for user in (self.owner, admin):
            api.force_authenticate(user)
            response = api.get("/api/notifications/", {"surface": "bell", "business": self.business.pk})
            self.assertEqual(response.status_code, 200)
            self.assertEqual(len(response.data["results"]), 1)
            self.assertEqual(response.data["results"][0]["recipient"], user.pk)
        api.force_authenticate(User.objects.get(username="excluded-0"))
        response = api.get("/api/notifications/", {"surface": "bell", "business": self.business.pk})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["results"], [])
        NotificationPreference.objects.create(business=self.business, user=admin, category="system", in_app_enabled=False)
        ExportJob.objects.filter(pk=job.pk).update(status="succeeded")
        observe_business_service(self.business.pk, now=self.now + timedelta(seconds=1))
        self.assertEqual(Notification.objects.filter(recipient=admin).count(), 1)
        self.assertEqual(Notification.objects.filter(recipient=self.owner).count(), 2)
        BusinessMember.objects.filter(business=self.business, user=admin).update(is_active=False)
        self.owner.is_active = False
        self.owner.save(update_fields=["is_active"])
        ExportJob.objects.filter(pk=job.pk).update(status="pending")
        observe_business_service(self.business.pk, now=self.now + timedelta(seconds=2))
        self.assertEqual(Notification.objects.count(), 3)

    def test_notification_failure_rolls_back_state_and_can_retry(self):
        self.overdue_export()
        with patch("apps.core.service_status.Notification.objects.bulk_create", side_effect=RuntimeError("write failed")):
            with self.assertRaises(RuntimeError):
                observe_business_service(self.business.pk, now=self.now)
        self.assertFalse(ServiceComponentState.objects.exists())
        self.assertFalse(Notification.objects.exists())
        observe_business_service(self.business.pk, now=self.now)
        self.assertEqual(Notification.objects.count(), 1)

    def test_terminal_failures_and_future_work_are_not_current_outage(self):
        job = self.overdue_export()
        ExportJob.objects.filter(pk=job.pk).update(status="failed", error="private historical failure")
        AutomationRun.objects.create(business=self.business, trigger_type="lead_created", status="failed")
        AutomationRun.objects.create(business=self.business, trigger_type="lead_created", status="waiting", run_after=self.now + timedelta(days=1))
        self.assertEqual(observe_business_service(self.business.pk, now=self.now), [])
        payload = business_service_status(self.business, now=self.now)
        self.assertEqual(payload["status"], "healthy")
        self.assertNotIn("private historical failure", str(payload))
        # No optional connector/provider setup is needed for this healthy sample.
        self.assertEqual(len(payload["components"]), 4)

    def test_late_component_failure_rolls_back_entire_sample(self):
        from apps.core.service_status import _record_observation
        def fail_late(business, component, count, observed_at):
            if component == "exports":
                raise RuntimeError("sample failed")
            return _record_observation(business, component, count, observed_at)
        with patch("apps.core.service_status._record_observation", side_effect=fail_late):
            with self.assertRaises(RuntimeError):
                observe_business_service(self.business.pk, now=self.now)
        self.assertFalse(ServiceComponentState.objects.exists())

    def test_observations_are_business_scoped(self):
        other = Business.objects.create(owner=self.owner, name="Other", slug="service-other")
        self.overdue_export()
        observe_business_service(other.pk, now=self.now)
        self.assertEqual(business_service_status(other, now=self.now)["status"], "healthy")
        self.assertEqual(business_service_status(self.business, now=self.now)["status"], "unknown")

    def test_sources_count_overdue_work_and_ignore_scheduled_or_terminal_records(self):
        old = self.now - timedelta(hours=1)
        AutomationRun.objects.create(business=self.business, trigger_type="lead_created", status="pending", run_after=old)
        Notification.objects.create(business=self.business, channel="system", text="Private notification", send_at=old)
        file = FileAttachment.objects.create(business=self.business, original_name="Private file", size=1,
                                             entity_type="client", entity_id="42", scan_status="error")
        FileAttachment.objects.filter(pk=file.pk).update(created_at=old)
        self.overdue_export()
        transitions = observe_business_service(self.business.pk, now=self.now)
        self.assertEqual(len(transitions), 4)
        self.assertEqual(set(ServiceComponentState.objects.values_list("affected_count", flat=True)), {1})
        summary = platform_service_status(now=self.now)
        self.assertEqual(summary["businesses"]["degraded"], 1)
        self.assertEqual(len(summary["incidents"]), 4)
        self.assertEqual({item["business_id"] for item in summary["incidents"]}, {self.business.pk})
        payload = business_service_status(self.business, now=self.now)
        self.assertNotIn("Private", str(payload))
        self.assertNotIn("entity_id", str(payload))

    def test_batch_rotates_and_platform_does_not_hide_unknown_businesses(self):
        other = Business.objects.create(owner=self.owner, name="Other", slug="rotation-other")
        self.assertEqual(platform_service_status(now=self.now)["businesses"], {"total": 2, "healthy": 0, "degraded": 0, "unknown": 2})
        observe_service_batch(limit=1)
        observe_service_batch(limit=1)
        self.assertEqual(ServiceComponentState.objects.filter(business=other).count(), 4)
        self.assertEqual(platform_service_status()["businesses"]["healthy"], 2)

    def test_status_api_is_read_only_scoped_and_rechecks_membership(self):
        api = APIClient()
        url = f"/api/service-status/?business={self.business.pk}"
        self.assertIn(api.get(url).status_code, (401, 403))
        api.force_authenticate(self.owner)
        self.assertEqual(api.get(url).status_code, 200)
        self.assertEqual(api.get("/api/service-status/?business=bad").status_code, 400)
        self.assertEqual(api.post(url, {}).status_code, 405)
        outsider = User.objects.create_user(username="outsider", email="outsider@example.com")
        api.force_authenticate(outsider)
        self.assertEqual(api.get(url).status_code, 403)
        membership = BusinessMember.objects.create(business=self.business, user=outsider, role="operator")
        self.assertEqual(api.get(url).status_code, 200)
        membership.is_active = False
        membership.save()
        self.assertEqual(api.get(url).status_code, 403)
        self.assertFalse(ServiceComponentState.objects.exists())


@skipUnlessDBFeature("has_select_for_update")
class ServiceObservationConcurrencyTests(TransactionTestCase):
    def test_two_collectors_record_only_one_incident_start(self):
        owner = User.objects.create_user(username="parallel-owner", email="parallel-owner@example.com")
        business = Business.objects.create(owner=owner, name="Concurrent", slug="concurrent-service")
        job = ExportJob.objects.create(business=business, actor=owner, kind="entity", export_key="clients")
        ExportJob.objects.filter(pk=job.pk).update(created_at=timezone.now() - timedelta(hours=1))
        barrier = Barrier(2)
        def collect():
            close_old_connections()
            try:
                barrier.wait(timeout=10)
                return len(observe_business_service(business.pk))
            finally:
                close_old_connections()
        with ThreadPoolExecutor(max_workers=2) as pool:
            futures = [pool.submit(collect) for _ in range(2)]
            results = [future.result(timeout=30) for future in futures]
        self.assertEqual(sorted(results), [0, 1])
        self.assertEqual(ServiceComponentState.objects.filter(business=business).count(), 4)
        self.assertEqual(ServiceComponentState.objects.get(business=business, component="exports").episode, 1)
        self.assertEqual(Notification.objects.filter(business=business, recipient=owner).count(), 1)
