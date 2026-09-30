from datetime import timedelta
from unittest.mock import patch

from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.ai_core.ai_client import AIClientError, AIClientResult
from apps.ai_core.models import AIJob, AIRequestLog
from apps.ai_core.services import process_ai_job, process_due_ai_jobs
from apps.businesses.models import Business, BusinessMember


class AIJobRecoveryTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.owner = User.objects.create_user(username="job-owner", email="job-owner@example.invalid")
        cls.business = Business.objects.create(owner=cls.owner, name="Job recovery", slug="job-recovery")
        BusinessMember.objects.create(business=cls.business, user=cls.owner, role="owner")

    def job(self, **fields):
        return AIJob.objects.create(
            business=self.business, user=self.owner, source="crm", prompt_type="crm_assistant",
            idempotency_key=f"recovery-{AIJob.objects.count()}", input_json={"user_input": "What needs attention?"},
            **fields,
        )

    def abandon(self, job):
        AIJob.objects.filter(pk=job.pk).update(locked_at=timezone.now() - timedelta(hours=1))

    def test_abandoned_claim_fails_without_repeating_unknown_provider_effect(self):
        job = self.job(status="running", attempts=1, locked_at=timezone.now() - timedelta(hours=1))
        with patch("apps.ai_core.services.run_ai_request") as provider:
            process_due_ai_jobs()
        job.refresh_from_db()
        self.assertEqual(job.status, "failed")
        self.assertIsNone(job.locked_at)
        self.assertIsNotNone(job.completed_at)
        self.assertEqual(job.attempts, 1)
        self.assertEqual(job.result_json, {})
        provider.assert_not_called()
        api = APIClient()
        api.force_authenticate(self.owner)
        response = api.get(f"/api/ai/jobs/{job.pk}/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["status"], "failed")

    def test_recent_claim_and_completed_result_are_preserved(self):
        active = self.job(status="running", attempts=1, locked_at=timezone.now())
        completed = self.job(status="succeeded", result_json={"answer": "Saved result"})
        with patch("apps.ai_core.services.run_ai_request") as provider:
            process_due_ai_jobs()
        active.refresh_from_db()
        completed.refresh_from_db()
        self.assertEqual(active.status, "running")
        self.assertEqual(completed.result_json, {"answer": "Saved result"})
        provider.assert_not_called()

    def test_legacy_running_claim_without_lock_uses_last_update(self):
        stale = self.job(status="running", attempts=1)
        recent = self.job(status="running", attempts=1)
        AIJob.objects.filter(pk=stale.pk).update(updated_at=timezone.now() - timedelta(hours=1))
        process_due_ai_jobs()
        stale.refresh_from_db()
        recent.refresh_from_db()
        self.assertEqual(stale.status, "failed")
        self.assertEqual(recent.status, "running")

    def test_late_success_cannot_replace_expired_claim(self):
        job = self.job()

        def finish_after_expiry(**kwargs):
            self.abandon(job)
            process_due_ai_jobs()
            log = AIRequestLog.objects.create(business=self.business, user=self.owner, prompt_type="crm_assistant", output_text="Late answer", model="synthetic")
            return AIClientResult("Late answer", "synthetic"), log

        with patch("apps.ai_core.services.run_ai_request", side_effect=finish_after_expiry) as provider:
            result = process_ai_job(job.pk)
        self.assertEqual(result.status, "failed")
        self.assertEqual(result.result_json, {})
        self.assertIsNone(result.request_log_id)
        provider.assert_called_once()

    def test_late_transient_error_cannot_requeue_expired_claim(self):
        job = self.job()

        def fail_after_expiry(**kwargs):
            self.abandon(job)
            process_due_ai_jobs()
            raise AIClientError(retryable=True)

        with patch("apps.ai_core.services.run_ai_request", side_effect=fail_after_expiry) as provider:
            result = process_ai_job(job.pk)
        self.assertEqual(result.status, "failed")
        self.assertIsNone(result.next_retry_at)
        provider.assert_called_once()

    def test_unexpired_claim_completes_normally_and_replay_is_read_only(self):
        job = self.job()
        log = AIRequestLog.objects.create(business=self.business, user=self.owner, prompt_type="crm_assistant", output_text="Current answer", model="synthetic")
        with patch("apps.ai_core.services.run_ai_request", return_value=(AIClientResult("Current answer", "synthetic"), log)) as provider:
            self.assertEqual(process_ai_job(job.pk).status, "succeeded")
            self.assertEqual(process_ai_job(job.pk).result_json["answer"], "Current answer")
        provider.assert_called_once()
