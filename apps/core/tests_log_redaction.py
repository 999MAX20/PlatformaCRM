from io import StringIO
import json
import logging
import sys

from django.core.management import call_command
from django.test import SimpleTestCase, TestCase, override_settings

from apps.core.logging import JsonLogFormatter, request_id_context
from apps.core.paid_beta_gate import run_paid_beta_gate_check
from apps.core.sanitization import sanitize_error_payload, sanitize_error_text


class ConfiguredConsoleRedactionTests(SimpleTestCase):
    def emit(self, message, args=(), *, exc_info=None, extra=None):
        handler = next(item for item in logging.getLogger().handlers if isinstance(item.formatter, JsonLogFormatter))
        stream = StringIO()
        previous = handler.setStream(stream)
        token = request_id_context.set("c03-correlation")
        try:
            record = logging.getLogger("c03.synthetic").makeRecord("c03.synthetic", logging.ERROR, __file__, 22, message, args, exc_info, extra=extra)
            handler.handle(record)
        finally:
            request_id_context.reset(token)
            handler.setStream(previous)
        payload = json.loads(stream.getvalue())
        self.assertEqual(payload["request_id"], "c03-correlation")
        self.assertEqual(payload["logger"], "c03.synthetic")
        self.assertEqual(payload["level"], "ERROR")
        return payload

    def test_message_arguments_and_url_context(self):
        result = self.emit("Provider failed: %s", ("Authorization: Bearer C03_BEARER",), extra={"path": "/jobs?token=C03_QUERY", "job_id": "job-42"})
        for secret in ("C03_BEARER", "C03_QUERY"):
            self.assertNotIn(secret, json.dumps(result))
        self.assertEqual(result["job_id"], "job-42")

    def test_exception_chain_preserves_types_frames_and_correlation(self):
        try:
            try:
                raise ValueError("rediss://c03-user:C03_PASSWORD@redis.example.invalid:6379/0?token=C03_TOKEN")
            except ValueError as error:
                raise RuntimeError("secret=C03_OUTER") from error
        except RuntimeError:
            result = self.emit("Provider failure", exc_info=sys.exc_info())
        for secret in ("c03-user", "C03_PASSWORD", "C03_TOKEN", "C03_OUTER"):
            self.assertNotIn(secret, result["exception"])
        for useful in ("ValueError", "RuntimeError", "Traceback", "tests_log_redaction.py", "direct cause"):
            self.assertIn(useful, result["exception"])

    def test_implicit_exception_context_is_sanitized(self):
        try:
            try:
                raise ValueError("api_key=C03_INNER")
            except ValueError:
                raise RuntimeError("password=C03_CONTEXT")
        except RuntimeError:
            result = self.emit("Failure", exc_info=sys.exc_info())
        self.assertNotIn("C03_INNER", result["exception"])
        self.assertNotIn("C03_CONTEXT", result["exception"])
        self.assertIn("During handling", result["exception"])

    def test_structured_and_non_string_context(self):
        class Diagnostic:
            def __str__(self):
                return "access_token=C03_OBJECT"
        result = self.emit("%s", ({"password": "C03_DICT"},), extra={"path": Diagnostic(), "status_code": 503})
        self.assertNotIn("C03_DICT", json.dumps(result))
        self.assertNotIn("C03_OBJECT", json.dumps(result))
        self.assertEqual(result["status_code"], 503)

    def test_quoted_multiword_secret_is_fully_masked(self):
        result = self.emit('password="C03_FIRST C03_LAST"; next operation')
        self.assertNotIn("C03_FIRST", result["message"])
        self.assertNotIn("C03_LAST", result["message"])
        self.assertIn("next operation", result["message"])

    def test_long_safe_diagnostic_is_not_truncated(self):
        text = "safe diagnostic " * 150 + "END_OF_DIAGNOSTIC"
        self.assertEqual(self.emit(text)["message"], text)

    def test_quoted_values_with_other_quotes_escapes_and_newlines(self):
        for text in ('password="C03_ONE \'C03_TWO\'"', 'secret="C03_ONE\\" C03_TWO"', '"api_key": "C03_ONE\nC03_TWO"'):
            with self.subTest(text=text):
                safe = sanitize_error_text(text)
                self.assertNotIn("C03_ONE", safe)
                self.assertNotIn("C03_TWO", safe)
        value = {"items": [{"password": "C03_NESTED"}, "token=C03_TEXT"]}
        self.assertNotIn("C03_", json.dumps(sanitize_error_payload(value)))
        self.assertEqual(value["items"][0]["password"], "C03_NESTED")

    def test_encoded_userinfo_ipv6_and_basic_auth(self):
        result = self.emit("rediss://user:C03_ENCODED%40key@[::1]:6379/0 Authorization: Basic C03_BASIC")
        self.assertNotIn("C03_ENCODED", result["message"])
        self.assertNotIn("C03_BASIC", result["message"])
        self.assertIn("[::1]:6379/0", result["message"])


class PaidBetaBrokerRedactionTests(TestCase):
    @override_settings(CELERY_BROKER_URL="rediss://c03-user:C03_PASSWORD@redis.example.invalid:6379/0?token=C03_QUERY#C03_FRAGMENT", AUTOMATIONS_RUN_INLINE=False)
    def test_json_and_text_commands_do_not_emit_broker_credentials(self):
        for format_name in ("json", "text"):
            with self.subTest(format=format_name):
                output = StringIO()
                call_command("paid_beta_gate_check", format=format_name, stdout=output)
                for secret in ("c03-user", "C03_PASSWORD", "C03_QUERY", "C03_FRAGMENT"):
                    self.assertNotIn(secret, output.getvalue())
                self.assertIn("runtime.redis_celery", output.getvalue())
        item = next(row for row in run_paid_beta_gate_check()["items"] if row["key"] == "runtime.redis_celery")
        self.assertEqual(item["status"], "pass")

    @override_settings(CELERY_BROKER_URL="redis://c03-user:C03_PASSWORD@redis.example.invalid/0", AUTOMATIONS_RUN_INLINE=False)
    def test_plain_redis_stays_blocked_without_echoing_url(self):
        item = next(row for row in run_paid_beta_gate_check()["items"] if row["key"] == "runtime.redis_celery")
        self.assertEqual(item["status"], "fail")
        self.assertNotIn("C03_PASSWORD", item["detail"])
