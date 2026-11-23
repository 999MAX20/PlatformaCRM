import json
from datetime import timedelta

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from apps.integrations.google_retention import cleanup_google
from apps.integrations.google_models import GoogleRetentionState


class Command(BaseCommand):
    help = "Report Google technical retention backlog; --apply performs bounded local cleanup."

    def add_arguments(self, parser):
        parser.add_argument("--apply", action="store_true")
        parser.add_argument("--business-id", type=int)
        parser.add_argument("--batch-size", type=int, default=100)
        parser.add_argument("--check", action="store_true", help="Exit nonzero if the global cleanup is disabled, stale or has backlog.")

    def handle(self, *args, **options):
        if options["check"] and (options["apply"] or options["business_id"]):
            raise CommandError("Use --check without --apply or --business-id.")
        try:
            result = cleanup_google(apply=options["apply"], business_id=options["business_id"],
                                    batch_size=options["batch_size"])
        except ValueError as exc:
            raise CommandError(str(exc)) from None
        if options["check"]:
            state = GoogleRetentionState.objects.filter(key="google").first()
            healthy = bool(settings.GOOGLE_RETENTION_ENABLED and state and state.last_success_at
                and state.last_success_at >= timezone.now()-timedelta(minutes=15)
                and not any(value for key, value in result.items() if key != "mode"))
            result["healthy"] = healthy
            result["enabled"] = settings.GOOGLE_RETENTION_ENABLED
            result["last_success_at"] = state.last_success_at.isoformat() if state and state.last_success_at else None
        self.stdout.write(json.dumps(result, sort_keys=True))
        if options["check"] and not healthy:
            raise CommandError("Google cleanup is disabled, stale or has pending data; inspect counts.")
        if result.get("files_failed") or result.get("files_protected"):
            raise CommandError("Google file cleanup needs attention; see non-sensitive counts.")
