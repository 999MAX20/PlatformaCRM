from django.core.management.base import BaseCommand

from apps.notifications.delivery import process_due_notifications
from apps.tasks.reminders import enqueue_due_task_reminders


class Command(BaseCommand):
    help = "Enqueues due task reminders and delivers pending notifications."

    def add_arguments(self, parser):
        parser.add_argument("--limit", type=int, default=100)

    def handle(self, *args, **options):
        enqueue_due_task_reminders(limit=options["limit"])
        results = process_due_notifications(limit=options["limit"])
        sent = sum(1 for item in results if item.get("status") == "sent")
        failed = sum(1 for item in results if item.get("status") == "failed")
        skipped = sum(1 for item in results if item.get("status") == "skipped")
        self.stdout.write(self.style.SUCCESS(f"Processed {len(results)} notifications: sent={sent}, failed={failed}, skipped={skipped}"))
