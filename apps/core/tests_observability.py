import json
import unittest

import sentry_sdk
from sentry_sdk.transport import Transport

from apps.core.observability import sanitize_sentry_event, sentry_privacy_options


class RecordingTransport(Transport):
    def __init__(self, options):
        super().__init__(options)
        self.envelopes = []

    def capture_envelope(self, envelope):
        self.envelopes.append(envelope)


class SentryPrivacyTests(unittest.TestCase):
    def test_unstructured_request_and_exception_data_are_not_sent(self):
        marker = "PRIVATE_CUSTOMER_AND_TOKEN_SENTINEL"
        event = {
            "event_id": "a" * 32, "release": "yc-pilot-20261106", "environment": "production",
            "request": {"url": f"https://host/invite/{marker}", "data": marker, "cookies": marker},
            "user": {"email": marker}, "extra": {"task_args": marker}, "tags": {"client": marker},
            "breadcrumbs": [{"message": marker}], "contexts": {"trace": {"dynamic_sampling_context": {"transaction": marker}}},
            "logentry": {"formatted": marker}, "transaction": marker, "message": marker,
            "exception": {"values": [{"type": "ValueError", "value": marker, "mechanism": {"handled": False, "data": marker},
                "stacktrace": {"frames": [{"filename": f"/private/{marker}/views.py", "function": "post", "lineno": 42,
                    "vars": {"password": marker}, "context_line": marker, "abs_path": marker, "in_app": True}]}}]},
        }
        hint = {"attachments": [marker]}
        result = sanitize_sentry_event(event, hint)
        self.assertNotIn(marker, json.dumps(result))
        self.assertNotIn("attachments", hint)
        frame = result["exception"]["values"][0]["stacktrace"]["frames"][0]
        self.assertEqual(frame, {"filename": "views.py", "function": "post", "lineno": 42, "in_app": True})
        self.assertFalse(result["exception"]["values"][0]["mechanism"]["handled"])

    def test_sdk_envelope_contains_error_only_without_attachments_or_scope_data(self):
        marker = "PRIVATE_SCOPE_PAYLOAD"
        options = sentry_privacy_options()
        options["integrations"] = []
        with sentry_sdk.init(dsn="https://public@example.invalid/1", transport=RecordingTransport,
                             release="privacy-test", environment="test", traces_sample_rate=0, **options):
            transport = sentry_sdk.get_client().transport
            with sentry_sdk.isolation_scope() as scope:
                scope.set_user({"email": marker})
                scope.set_extra("payload", marker)
                scope.set_tag("customer", marker)
                scope.add_attachment(bytes=marker.encode(), filename="private.txt")
                try:
                    raise ValueError(marker)
                except ValueError:
                    event_id = sentry_sdk.capture_exception()
            self.assertIsNotNone(event_id)
            self.assertEqual(len(transport.envelopes), 1)
            envelope = transport.envelopes[0]
            self.assertEqual([item.headers["type"] for item in envelope.items], ["event"])
            self.assertNotIn(marker.encode(), envelope.serialize())
            self.assertEqual(envelope.get_event()["exception"]["values"][0]["type"], "ValueError")

    def test_sdk_drops_transactions_even_if_sampling_is_enabled(self):
        options = sentry_privacy_options()
        options["integrations"] = []
        with sentry_sdk.init(dsn="https://public@example.invalid/1", transport=RecordingTransport,
                             traces_sample_rate=1, **options):
            transport = sentry_sdk.get_client().transport
            with sentry_sdk.start_transaction(name="/invite/PRIVATE_TOKEN", op="http.server"):
                pass
            self.assertEqual(transport.envelopes, [])

    def test_log_messages_do_not_expose_free_text(self):
        result = sanitize_sentry_event({"event_id": "b" * 32, "message": "Customer Alice: password=secret"}, {})
        self.assertNotIn("Alice", json.dumps(result))
        self.assertNotIn("secret", json.dumps(result))

    def test_invalid_event_identity_is_dropped(self):
        self.assertIsNone(sanitize_sentry_event({"event_id": "secret-data"}, {}))

    def test_privacy_options_disable_unreviewed_channels(self):
        options = sentry_privacy_options()
        self.assertFalse(options["send_default_pii"])
        self.assertFalse(options["include_local_variables"])
        self.assertFalse(options["auto_enabling_integrations"])
        self.assertFalse(options["enable_logs"])
        self.assertEqual(options["max_request_body_size"], "never")
