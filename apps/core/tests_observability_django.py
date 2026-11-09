import sentry_sdk
from django.test import SimpleTestCase, override_settings
from django.urls import path

from apps.core.observability import sentry_privacy_options
from apps.core.tests_observability import RecordingTransport


def failing_view(request, token):
    raise ValueError("PRIVATE_REQUEST_BODY " + token)


urlpatterns = [path("invite/<str:token>/", failing_view)]


@override_settings(ROOT_URLCONF=__name__, MIDDLEWARE=[], ALLOWED_HOSTS=["testserver"])
class DjangoSentryPrivacyTests(SimpleTestCase):
    def test_real_django_exception_reports_location_without_request_data(self):
        client = sentry_sdk.Client(
            dsn="https://public@example.invalid/1", transport=RecordingTransport,
            release="privacy-test", environment="test", traces_sample_rate=0,
            **sentry_privacy_options(),
        )
        self.addCleanup(client.close)
        with sentry_sdk.isolation_scope() as scope:
            scope.set_client(client)
            with self.assertRaises(ValueError):
                self.client.post(
                    "/invite/PRIVATE_INVITATION_TOKEN/", {"customer": "PRIVATE_REQUEST_BODY"},
                    HTTP_AUTHORIZATION="Bearer PRIVATE_AUTHORIZATION", HTTP_COOKIE="session=PRIVATE_COOKIE",
                )
        self.assertTrue(client.transport.envelopes)
        events = [envelope.get_event() for envelope in client.transport.envelopes]
        self.assertTrue(any(event.get("exception") for event in events))
        for envelope in client.transport.envelopes:
            self.assertNotIn(b"PRIVATE_", envelope.serialize())
            self.assertEqual([item.headers["type"] for item in envelope.items], ["event"])
