from celery import shared_task

from apps.notifications.delivery import process_due_notifications
from apps.tasks.reminders import enqueue_due_task_reminders


@shared_task(bind=True, name="notifications.process_due_notifications", queue="notifications")
def process_due_notifications_task(self, limit=100):
    reminders = enqueue_due_task_reminders(limit=limit)
    results = process_due_notifications(limit=limit)
    return {
        "reminders_enqueued": reminders,
        "processed": len(results),
        "sent": sum(item.get("status") == "sent" for item in results),
        "retry_scheduled": sum(item.get("status") == "retry_scheduled" for item in results),
        "failed": sum(item.get("status") == "failed" for item in results),
    }
