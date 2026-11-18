from datetime import timedelta
from urllib.parse import parse_qs, urlsplit
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from apps.businesses.models import Business, BusinessMember
from apps.integrations import google_oauth
from apps.integrations.google_http import GoogleError
from apps.integrations.google_models import GoogleConnection, GoogleOAuthAttempt


@override_settings(GOOGLE_INTEGRATION_CLIENT_ID="google-client", GOOGLE_INTEGRATION_CLIENT_SECRET="private-secret",
                   GOOGLE_INTEGRATION_REDIRECT_URI="https://crm.example.com/app/integrations/google/callback")
class GoogleOAuthTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="google-owner", email="google-owner@example.com", role="business_owner")
        self.business = Business.objects.create(owner=self.user, name="Google", slug="google-test")
        BusinessMember.objects.create(business=self.business, user=self.user, role="owner")
        self.other = get_user_model().objects.create_user(username="other-google", email="other-google@example.com", role="business_owner")
        self.api = APIClient()
        self.api.force_authenticate(self.user)
        self.remote = patch("apps.integrations.google_oauth.google_request", side_effect=self.respond).start()
        self.addCleanup(patch.stopall)

    def respond(self, url, **kwargs):
        if url.endswith("userinfo"):
            return {"sub": "google-subject", "email": "test@example.com", "email_verified": True}
        return {"access_token": "private-access", "refresh_token": "private-refresh", "scope": google_oauth.SHEETS_SCOPE, "expires_in": 3600}

    def start(self):
        response = self.api.post("/api/integrations/google/start/", {"business": self.business.pk}, format="json")
        self.assertEqual(response.status_code, 200, response.data)
        return parse_qs(urlsplit(response.data["authorization_url"]).query)

    def complete(self, state):
        return self.api.post("/api/integrations/google/complete/", {"state": state, "code": "private-code"}, format="json")

    def test_start_pkce_scopes_and_encrypted_complete_replay(self):
        query = self.start()
        self.assertEqual(query["code_challenge_method"], ["S256"])
        self.assertNotIn("calendar", query["scope"][0])
        response = self.complete(query["state"][0])
        self.assertEqual(response.status_code, 200, response.data)
        connection = GoogleConnection.objects.get()
        self.assertNotIn("private-refresh", connection.encrypted_refresh)
        self.assertNotIn("private-access", str(response.data))
        self.assertEqual(self.complete(query["state"][0]).status_code, 400)
        self.assertEqual(self.remote.call_count, 2)

    def test_actor_and_business_boundaries(self):
        state = self.start()["state"][0]
        self.api.force_authenticate(self.other)
        self.assertEqual(self.complete(state).status_code, 400)
        self.assertEqual(self.api.post("/api/integrations/google/start/", {"business": self.business.pk}).status_code, 404)
        self.assertFalse(self.remote.called)

    def test_expired_and_superseded_state(self):
        old = self.start()["state"][0]
        new = self.start()["state"][0]
        self.assertEqual(self.complete(old).status_code, 400)
        GoogleOAuthAttempt.objects.update(created_at=timezone.now()-timedelta(minutes=11))
        self.assertEqual(self.complete(new).status_code, 400)
        self.assertFalse(self.remote.called)

    def test_failed_exchange_is_not_replayed(self):
        state = self.start()["state"][0]
        self.remote.side_effect = GoogleError()
        self.assertEqual(self.complete(state).status_code, 503)
        self.assertEqual(self.complete(state).status_code, 400)
        self.assertEqual(self.remote.call_count, 1)

    def test_missing_scope_does_not_activate(self):
        state = self.start()["state"][0]
        self.remote.side_effect = None
        self.remote.return_value = {"access_token": "private", "refresh_token": "private", "scope": "openid"}
        self.assertEqual(self.complete(state).status_code, 400)
        self.assertEqual(GoogleConnection.objects.get().status, "disconnected")

    def test_refresh_revocation_persists_and_disconnect_invalidates_attempt(self):
        self.complete(self.start()["state"][0])
        connection = GoogleConnection.objects.get()
        connection.access_expires_at = timezone.now()
        connection.save()
        self.remote.side_effect = GoogleError(revoked=True)
        with self.assertRaises(GoogleError):
            google_oauth.access_token(connection, self.user)
        connection.refresh_from_db()
        self.assertEqual(connection.status, "expired_credentials")
        state = self.start()["state"][0]
        response = self.api.post(f"/api/integrations/google/connections/{connection.pk}/disconnect/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.complete(state).status_code, 400)
        connection.refresh_from_db()
        self.assertEqual(connection.encrypted_refresh, "")
