from unittest.mock import patch

from django.test import TestCase, override_settings
from django.utils import timezone

from apps.integrations import tests_ycloud
from apps.integrations.ycloud import client, onboarding
from apps.integrations.ycloud.models import YCloudConnection


@override_settings(YCLOUD_ENABLED=True, YCLOUD_API_KEY="synthetic-key", YCLOUD_WEBHOOK_SECRET="synthetic-webhook-secret")
class YCloudExpiryTests(TestCase):
    setUp = tests_ycloud.YCloudOnboardingTests.setUp

    def test_iso_expiry_creates_bound_coexistence_attempt_without_persisting_link(self):
        expiry = timezone.now() + timezone.timedelta(hours=2)
        link = {**self.link, "expiresAt": expiry.isoformat().replace("+00:00", "Z")}
        with patch.object(client, "create_link", return_value=link):
            result = onboarding.start(self.channel, self.owner,
                onboarding_type="WHATSAPP_BUSINESS_APP", expected_phone_number="+77010000000")
        connection = YCloudConnection.objects.get(channel=self.channel)
        self.assertEqual(connection.expires_at, expiry)
        self.assertEqual(connection.expected_phone_number, "+77010000000")
        self.assertEqual(connection.onboarding_type, "WHATSAPP_BUSINESS_APP")
        self.assertEqual(result["onboarding_url"], link["onboardingUrl"])
        self.channel.refresh_from_db()
        self.assertNotIn("synthetic", str(self.channel.config_json))

    def test_rejected_expiry_preserves_channel_and_creates_no_connection(self):
        now = timezone.now()
        invalid = [None, {}, "invalid", (now + timezone.timedelta(hours=2)).replace(tzinfo=None).isoformat(),
            (now - timezone.timedelta(seconds=1)).isoformat(),
            (now + timezone.timedelta(hours=4)).isoformat(),
            int((now + timezone.timedelta(hours=4)).timestamp() * 1000)]
        original = self.channel.config_json.copy()
        for expiry in invalid:
            with self.subTest(expiry=expiry), patch.object(client, "create_link", return_value={**self.link, "expiresAt": expiry}):
                with self.assertRaises(client.YCloudError) as raised:
                    onboarding.start(self.channel, self.owner)
                self.assertEqual(raised.exception.code, "invalid_provider_response")
                self.channel.refresh_from_db()
                self.assertEqual(self.channel.config_json, original)
                self.assertFalse(YCloudConnection.objects.exists())
