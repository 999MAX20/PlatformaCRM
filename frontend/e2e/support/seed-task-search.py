"""Provenance-backed automatic task, disposable browser runtime only."""
from pathlib import Path
from datetime import timedelta
from types import SimpleNamespace
import json
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from scripts.browser_test_runtime import configure_browser_runtime

configure_browser_runtime()
import django
django.setup()

from django.utils import timezone
from apps.accounts.models import User
from apps.activities.models import ActivityEvent
from apps.activities.taxonomy import ActivityEvents
from apps.businesses.models import Business
from apps.clients.models import Client
from apps.services.models import Service
from apps.scheduling.models import Appointment
from apps.scheduling.services import _appointment_follow_up_task_spec
from apps.tasks.models import Task

owner = User.objects.get(email="business_owner@example.com")
business = Business.objects.filter(owner=owner).order_by("id").first()
client = Client.objects.create(business=business, full_name="QA016 synthetic client")
service = Service.objects.create(business=business, name="QA016 service")
now = timezone.now()
appointment = Appointment.objects.create(business=business, client=client, service=service,
    start_at=now, end_at=now+timedelta(hours=1), status="cancelled")
spec = _appointment_follow_up_task_spec(SimpleNamespace(id=appointment.pk, status="cancelled"))
task = Task.objects.create(business=business, appointment=appointment, client=client,
    assignee=owner, created_by=owner, title=spec["title"], description=spec["description"])
ActivityEvent.objects.create(business=business, entity_type="Task", entity_id=str(task.pk),
    event_type=ActivityEvents.TASK_CREATED,
    metadata={"appointment_id": appointment.pk, "appointment_status": "cancelled"})
print(json.dumps({"id": task.pk, "appointment": appointment.pk, "title": task.title,
    "description": task.description}))
