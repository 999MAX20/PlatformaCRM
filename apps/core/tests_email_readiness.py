from io import StringIO
from smtplib import SMTPException
from unittest.mock import patch

from django.core.management import call_command, CommandError
from django.test import SimpleTestCase, override_settings

from apps.core.paid_beta_gate import _has_transactional_email
from apps.core.production_audit import run_production_readiness_audit
from apps.core.production_rules import has_transactional_email


@override_settings(
    ENVIRONMENT="production",
    EMAIL_BACKEND="django.core.mail.backends.smtp.EmailBackend",
    EMAIL_HOST="smtp.mail-provider.net",
    DEFAULT_FROM_EMAIL="PlatformaCRM <no-reply@platformacrm.kz>",
    EMAIL_USE_TLS=True,
    EMAIL_USE_SSL=False,
)
class EmailReadinessTests(SimpleTestCase):
    def test_secure_smtp_passes_both_gates(self):
        self.assertTrue(has_transactional_email())
        self.assertTrue(_has_transactional_email())
        with override_settings(EMAIL_USE_TLS=False, EMAIL_USE_SSL=True):
            self.assertTrue(has_transactional_email())

    def test_non_delivery_backends_fail_gates_and_smoke_without_sending(self):
        for name in ["locmem", "console", "filebased", "dummy"]:
            with self.subTest(backend=name), override_settings(
                EMAIL_BACKEND=f"django.core.mail.backends.{name}.EmailBackend"
            ), patch("apps.notifications.email.send_mail") as send:
                self.assertFalse(has_transactional_email())
                self.assertFalse(_has_transactional_email())
                audit = run_production_readiness_audit()
                item = next(i for i in audit["items"] if i["key"] == "email.transactional")
                self.assertEqual(item["status"], "warn")
                with self.assertRaises(CommandError):
                    call_command("email_runtime_smoke", "--send", "--to", "owner@example.com", stdout=StringIO())
                send.assert_not_called()

    def test_invalid_sender_host_and_transport_fail_closed(self):
        cases = [
            {"DEFAULT_FROM_EMAIL": "no-reply@your-domain.com"},
            {"DEFAULT_FROM_EMAIL": "invalid"},
            {"DEFAULT_FROM_EMAIL": "no-reply@zani.local"},
            {"EMAIL_HOST": " "},
            {"EMAIL_USE_TLS": False},
            {"EMAIL_USE_SSL": True},
        ]
        for values in cases:
            with self.subTest(values=values), override_settings(**values):
                self.assertFalse(has_transactional_email())
                self.assertFalse(_has_transactional_email())

    def test_preflight_never_sends(self):
        with patch("apps.notifications.email.send_mail") as send:
            call_command("email_runtime_smoke", "--fail-on-missing", stdout=StringIO())
            send.assert_not_called()

    def test_smtp_acceptance_does_not_claim_inbox_delivery(self):
        output = StringIO()
        with patch("apps.notifications.email.send_mail", return_value=1) as send:
            call_command("email_runtime_smoke", "--send", "--to", "owner@example.com", stdout=output)
            self.assertEqual(send.call_args.kwargs["recipient_list"], ["owner@example.com"])
            self.assertFalse(send.call_args.kwargs["fail_silently"])
        self.assertIn("recipient delivery must be verified", output.getvalue())

    def test_zero_send_and_transport_failure_are_not_success(self):
        output = StringIO()
        with patch("apps.notifications.email.send_mail", return_value=0):
            with self.assertRaises(CommandError):
                call_command("email_runtime_smoke", "--send", "--to", "owner@example.com", stdout=output)
        with patch("apps.notifications.email.send_mail", side_effect=SMTPException("transport unavailable")):
            with self.assertRaises(SMTPException):
                call_command("email_runtime_smoke", "--send", "--to", "owner@example.com", stdout=output)
        self.assertNotIn("accepted by SMTP", output.getvalue())

    def test_missing_recipient_does_not_send(self):
        with patch("apps.notifications.email.send_mail") as send:
            with self.assertRaises(CommandError):
                call_command("email_runtime_smoke", "--send", stdout=StringIO())
            send.assert_not_called()
