"""Separate process: python -m uvicorn config.notification_asgi:application."""
import os

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from apps.notifications.event_stream import AnnouncementEvents  # noqa: E402

application = AnnouncementEvents()
