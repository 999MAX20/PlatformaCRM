"""Durable in-app reminders, consumed by the existing notification beat tick."""

from django.db import transaction
from django.db.models import Exists, OuterRef, Q
from django.utils import timezone

from apps.businesses.models import BusinessCapability
from apps.tasks.models import Task, TaskReminderDelivery
from apps.tasks.services import OPEN_STATUSES, create_routed_task_notifications


def _due_reminders(now):
    disabled = BusinessCapability.objects.filter(module_key="tasks", is_enabled=False)
    return (
        Task.objects.filter(status__in=OPEN_STATUSES, is_archived=False, reminder_at__lte=now)
        .filter(Q(snoozed_until__isnull=True) | Q(snoozed_until__lte=now))
        .filter(~Exists(TaskReminderDelivery.objects.filter(task_id=OuterRef("pk"), reminder_at=OuterRef("reminder_at"))))
        .exclude(business_id__in=disabled.values("business_id"))
    )


def enqueue_due_task_reminders(*, limit=100, now=None):
    now = now or timezone.now()
    task_ids = list(_due_reminders(now).order_by("reminder_at", "pk").values_list("pk", flat=True)[:limit])
    enqueued = 0
    for task_id in task_ids:
        with transaction.atomic():
            task = _due_reminders(now).select_for_update().filter(pk=task_id).first()
            if task is None:
                continue
            # Unique receipt and notifications commit together. Ordinary task edits
            # cannot erase it; retries after a rollback remain eligible next tick.
            _, claimed = TaskReminderDelivery.objects.get_or_create(task=task, reminder_at=task.reminder_at)
            if not claimed:
                continue
            enqueued += len(create_routed_task_notifications(
                task=task, text=f"Напоминание: {task.title}", priority=task.priority,
            ))
    return enqueued
