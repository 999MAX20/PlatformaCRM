"""Synthetic Calendar adapter for the network-isolated browser acceptance runner."""
import copy
import threading
import time


def configure(business, owner, output):
    from datetime import timedelta
    from django.conf import settings
    from django.db import close_old_connections, OperationalError
    from django.utils import timezone
    from apps.integrations import google_calendar_provider as provider, google_calendar_sync as sync
    from apps.integrations.credential_encryption import encrypt_credential_value
    from apps.integrations.google_http import GoogleError
    from apps.integrations.google_models import GoogleConnection
    from apps.scheduling.models import Resource

    settings.GOOGLE_CALENDAR_ENABLED = True
    GoogleConnection.objects.get_or_create(business=business, actor=owner, provider="google_calendar", defaults={
        "status": "connected", "email": "calendar-fixture@example.test", "subject": "isolated-calendar",
        "encrypted_access": encrypt_credential_value("isolated-access"),
        "encrypted_refresh": encrypt_credential_value("isolated-refresh"),
        "access_expires_at": timezone.now() + timedelta(hours=2)})
    Resource.objects.get_or_create(business=business, name="Calendar Test Specialist")
    info = {"id": "calendar-fixture@example.test", "summary": "PlatformaCRM Test Calendar",
            "timeZone": "Asia/Almaty", "accessRole": "owner"}
    events = {}

    def check():
        if (output / "provider-error").exists():
            raise GoogleError()

    def calendars(token):
        check()
        return [] if (output / "no-calendars").exists() else [info]

    def calendar_info(*args):
        check()
        return info

    def list_events(*args):
        check()
        return copy.deepcopy(list(events.values()))

    def write(token, calendar, event_id, payload, existing=None):
        check()
        events[event_id] = {**copy.deepcopy(payload), "id": event_id, "etag": '"fixture"'}
        return events[event_id]

    def delete(token, calendar, event_id, existing):
        check()
        events[event_id] = {"id": event_id, "status": "cancelled"}

    provider.calendars = calendars
    provider.calendar_info = calendar_info
    provider.events = list_events
    provider.get_event = lambda token, calendar, event_id: copy.deepcopy(events.get(event_id))
    provider.write_event = write
    provider.delete_event = delete

    def poll():
        while not (output / "stop").exists():
            close_old_connections()
            try:
                sync.process_due()
            except OperationalError:
                pass  # SQLite fixture polling retries after a concurrent UI write.
            finally:
                close_old_connections()
            time.sleep(1)

    threading.Thread(target=poll, daemon=True).start()
