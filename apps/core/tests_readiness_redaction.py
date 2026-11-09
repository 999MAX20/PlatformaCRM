import json
from io import StringIO

from django.core.management import call_command
from django.test import SimpleTestCase, TestCase, override_settings
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.core.production_audit import run_production_readiness_audit


# All addresses and markers below are synthetic and are never contacted.
BROKER = "redis://fixture-user:fixture-password@broker.example.invalid:6379/fixture-path?key=fixture-query#fixture-fragment"
MARKERS = ("fixture-user", "fixture-password", "broker.example.invalid", "fixture-path", "fixture-query", "fixture-fragment")


def redis_item(report):
    return next(item for item in report["items"] if item["key"] == "queue.redis")


class ReadinessRedactionTests(SimpleTestCase):
    @override_settings(CELERY_BROKER_URL=BROKER)
    def test_broker_failure_contains_state_not_configuration(self):
        item = redis_item(run_production_readiness_audit())
        self.assertEqual(item["status"], "fail")
        self.assertEqual(item["severity"], "critical")
        self.assertIn("configured=True", item["detail"])
        self.assertTrue(item["action"])
        for marker in MARKERS:
            with self.subTest(marker=marker):
                self.assertNotIn(marker, item["detail"])

    def test_alternate_broker_representations_never_echo_values(self):
        values = (
            "fixture-password-without-url",
            "//fixture-user:fixture-password@broker.example.invalid/fixture-path",
            "redis://fixture-user:fixture-password@broker.example.invalid/fixture-path",
            "memory://fixture-user:fixture-password@broker.example.invalid/fixture-path",
            "rediss://fixture-user:fixture-password@broker.example.invalid/fixture-path",
        )
        for value in values:
            with self.subTest(value_class=value.split(":", 1)[0]), override_settings(CELERY_BROKER_URL=value):
                detail = redis_item(run_production_readiness_audit())["detail"]
                self.assertIn("configured=True", detail)
                self.assertNotIn("fixture-", detail)
                self.assertNotIn("broker.example.invalid", detail)

    def test_tls_and_missing_configuration_keep_legitimate_statuses(self):
        for value, expected, configured in (("", "fail", False), (BROKER, "fail", True),
                                             (BROKER.replace("redis://", "rediss://"), "pass", True)):
            with self.subTest(status=expected, configured=configured), override_settings(CELERY_BROKER_URL=value):
                item = redis_item(run_production_readiness_audit())
                self.assertEqual(item["status"], expected)
                self.assertIn(f"configured={configured}", item["detail"])

    @override_settings(CELERY_BROKER_URL="redis://fixture-user:fixture-password@[malformed/fixture-path")
    def test_malformed_broker_is_a_safe_failed_check(self):
        item = redis_item(run_production_readiness_audit())
        self.assertEqual(item["status"], "fail")
        self.assertIn("configured=True", item["detail"])
        self.assertNotIn("fixture-", item["detail"])

    @override_settings(
        TELEGRAM_ENABLED=False, WHATSAPP_ENABLED=False, INSTAGRAM_ENABLED=False,
        TELEGRAM_BASE_API_URL="http://fixture-user:fixture-password@telegram.example.invalid/fixture-path?key=fixture-query",
        WHATSAPP_GRAPH_BASE_URL="http://fixture-user:fixture-password@whatsapp.example.invalid/fixture-path#fixture-fragment",
        INSTAGRAM_GRAPH_BASE_URL="http://fixture-user:fixture-password@instagram.example.invalid/fixture-path",
        CORS_ALLOWED_ORIGINS=["http://fixture-user:fixture-password@origin.example.invalid/fixture-path"],
        CSRF_TRUSTED_ORIGINS=["http://fixture-user:fixture-password@origin.example.invalid/fixture-path"],
    )
    def test_other_config_url_copies_are_not_reported(self):
        report = run_production_readiness_audit()
        serialized = json.dumps(report)
        self.assertNotIn("fixture-", serialized)
        for host in ("telegram", "whatsapp", "instagram", "origin"):
            self.assertNotIn(f"{host}.example.invalid", serialized)
        by_key = {item["key"]: item for item in report["items"]}
        self.assertEqual(by_key["integrations.telegram"]["status"], "pass")
        self.assertEqual(by_key["integrations.whatsapp"]["status"], "pass")
        self.assertEqual(by_key["integrations.instagram"]["status"], "pass")
        self.assertEqual(by_key["environment.cors"]["status"], "fail")

    @override_settings(CELERY_BROKER_URL=BROKER)
    def test_json_and_text_command_share_safe_details(self):
        for format in ("json", "text"):
            output = StringIO()
            call_command("production_readiness_audit", format=format, stdout=output)
            text = output.getvalue()
            self.assertIn("queue.redis", text)
            self.assertIn("configured=True", text)
            for marker in MARKERS:
                self.assertNotIn(marker, text)


class ReadinessRedactionApiTests(TestCase):
    def setUp(self):
        self.api = APIClient()
        self.platform = User.objects.create_user(
            username="readiness-platform", email="readiness-platform@example.invalid", role=User.Roles.PLATFORM_MANAGER,
        )

    @override_settings(CELERY_BROKER_URL=BROKER, TELEGRAM_ENABLED=False,
                       TELEGRAM_BASE_API_URL="http://fixture-user:fixture-password@telegram.example.invalid/fixture-path")
    def test_platform_manager_response_has_no_config_url_copies(self):
        self.api.force_authenticate(self.platform)
        response = self.api.get("/api/platform/operations-health/")
        self.assertEqual(response.status_code, 200)
        serialized = json.dumps(response.data, default=str)
        for marker in MARKERS:
            self.assertNotIn(marker, serialized)
        self.assertNotIn("telegram.example.invalid", serialized)
        item = next(item for item in response.data["runtime"]["production_readiness"]["failed_items"] if item["key"] == "queue.redis")
        self.assertIn("configured=True", item["detail"])
        self.assertIn("summary", response.data)

    @override_settings(CELERY_BROKER_URL=BROKER.replace("redis://", "rediss://"))
    def test_tls_control_keeps_broker_out_of_failed_items(self):
        self.api.force_authenticate(self.platform)
        response = self.api.get("/api/platform/operations-health/")
        self.assertEqual(response.status_code, 200)
        keys = {item["key"] for item in response.data["runtime"]["production_readiness"]["failed_items"]}
        self.assertNotIn("queue.redis", keys)

    def test_merchant_still_cannot_read_platform_readiness(self):
        merchant = User.objects.create_user(username="readiness-merchant", email="readiness-merchant@example.invalid")
        self.api.force_authenticate(merchant)
        self.assertEqual(self.api.get("/api/platform/operations-health/").status_code, 403)
