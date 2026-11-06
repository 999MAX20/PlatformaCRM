from datetime import timedelta
from unittest.mock import patch

from django.conf import settings
from django.test import SimpleTestCase, TestCase
from django.utils import timezone
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken, OutstandingToken
from rest_framework_simplejwt.tokens import RefreshToken

from apps.accounts.models import User
from apps.accounts.tasks import flush_expired_tokens
from scripts.cleanup_local_tokens import ROOT, check_local_database


class TokenCleanupTests(TestCase):
    def test_cleanup_preserves_active_tokens_revocations_and_is_idempotent(self):
        user = User.objects.create_user(username="token-cleanup")
        live = RefreshToken.for_user(user)
        revoked = RefreshToken.for_user(user)
        revoked.blacklist()
        expired = RefreshToken.for_user(user)
        expired_revoked = RefreshToken.for_user(user)
        expired_revoked.blacklist()
        OutstandingToken.objects.filter(jti__in=[expired["jti"], expired_revoked["jti"]]).update(
            expires_at=timezone.now() - timedelta(days=1)
        )
        for _ in range(2):
            flush_expired_tokens()
            self.assertEqual(set(OutstandingToken.objects.values_list("jti", flat=True)), {live["jti"], revoked["jti"]})
            self.assertEqual(list(BlacklistedToken.objects.values_list("token__jti", flat=True)), [revoked["jti"]])
            RefreshToken(str(live))
            with self.assertRaises(TokenError):
                RefreshToken(str(revoked))
        self.assertTrue(User.objects.filter(pk=user.pk).exists())


class TokenCleanupConfigurationTests(SimpleTestCase):
    def test_daily_schedule_routes_to_registered_task(self):
        entry = settings.CELERY_BEAT_SCHEDULE["expired-auth-tokens"]
        self.assertEqual(entry["task"], flush_expired_tokens.name)
        self.assertEqual(entry["schedule"], 86400)
        self.assertEqual(entry["options"]["queue"], "default")

    def test_local_runner_rejects_remote_other_and_production_databases(self):
        for database, environment in [
            ({"ENGINE": "django.db.backends.postgresql", "NAME": "postgres"}, "development"),
            ({"ENGINE": "django.db.backends.sqlite3", "NAME": "other.sqlite3"}, "development"),
            ({"ENGINE": "django.db.backends.sqlite3", "NAME": "db.sqlite3"}, "production"),
        ]:
            with self.subTest(database=database, environment=environment), self.assertRaises(RuntimeError):
                check_local_database(database, environment)

    def test_local_runner_accepts_only_existing_checkout_database(self):
        with patch("pathlib.Path.is_file", return_value=True):
            check_local_database({"ENGINE": "django.db.backends.sqlite3", "NAME": ROOT / "db.sqlite3"}, "development")
        with patch("pathlib.Path.is_file", return_value=False), self.assertRaises(RuntimeError):
            check_local_database({"ENGINE": "django.db.backends.sqlite3", "NAME": ROOT / "db.sqlite3"}, "development")
