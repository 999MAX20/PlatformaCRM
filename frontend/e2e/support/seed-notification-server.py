"""Notification acceptance data, guarded by the disposable browser runtime."""
from datetime import timedelta
import json
from pathlib import Path
import sys
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from scripts.browser_test_runtime import configure_browser_runtime

configure_browser_runtime()
import django

django.setup()

from django.utils import timezone
from apps.accounts.models import User
from apps.businesses.models import Business
from apps.notifications.announcements import publish_announcement, revoke_announcement
from apps.notifications.models import Notification
from apps.tasks.models import Task

mode = sys.argv[1]
assert mode in {"dated", "receipts"}
owner = User.objects.get(email="business_owner@example.com")
staff = User.objects.get(email="business_specialist@example.com")
business = Business.objects.get(owner=owner)
foreign = Business.objects.get(owner__email="foreign_owner@example.com")
# Each case owns its disposable database's notification fixtures; no live rows.
Notification.objects.all().delete()
now = timezone.now()
rows = []
for index in range(55 if mode == "dated" else 2):
    text = f"Тест периода {index:02d}" if mode == "dated" else f"Объявление проверки {index + 1}"
    notification, _ = publish_announcement(actor=owner, business=business, text=text,
                                         priority="normal", publication_key=uuid4())
    Notification.objects.filter(pk=notification.pk).update(send_at=now - timedelta(days=index, minutes=1))
    rows.append({"id": notification.pk, "text": text})

task = Task.objects.create(business=business, assignee=owner, title="Проверка перехода из уведомления")
work = Notification.objects.create(business=business, recipient=owner, category="tasks",
                                   text="PRIVATE WORK SNAPSHOT", send_at=now,
                                   action_url=f"/app/tasks?task={task.pk}")
foreign_task = Task.objects.create(business=foreign, assignee=foreign.owner, title="Foreign task")
excluded = []
for values in (
    {"send_at": now + timedelta(days=1)},
    {"status": "cancelled"},
    {"channel": "email"},
    {"recipient": staff},
    {"action_url": f"/app/tasks?task={foreign_task.pk}"},
    {"business": foreign, "recipient": foreign.owner},
):
    notification = Notification.objects.create(**{
        "business": business, "recipient": owner, "send_at": now,
        "text": "EXCLUDED NOTIFICATION", **values,
    })
    excluded.append(notification.pk)
revoked, _ = publish_announcement(actor=owner, business=business, text="REVOKED ANNOUNCEMENT",
                                  priority="normal", publication_key=uuid4())
revoke_announcement(actor=owner, business=business, notification_id=revoked.pk)
excluded.append(revoked.pk)
print(json.dumps({"business": business.pk, "foreignBusiness": foreign.pk,
                  "owner": owner.pk, "staff": staff.pk, "rows": rows,
                  "work": work.pk, "task": task.pk, "excluded": excluded}))
