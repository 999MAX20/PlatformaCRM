import json
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from apps.medical.audit_reserve import ReserveUnavailable
from apps.medical.audit_reserve_recovery import MAX_RESERVE_BYTES, recover_reserved_read


class Command(BaseCommand):
    help = "Verify one locally retrieved medical reserve-audit object and print its audit references."
    requires_system_checks = []

    def add_arguments(self, parser):
        parser.add_argument("path", type=Path)
        parser.add_argument("--event-id", required=True)

    def handle(self, *args, **options):
        try:
            with options["path"].open("rb") as source:
                body = source.read(MAX_RESERVE_BYTES + 1)
            payload = recover_reserved_read(body, expected_event_id=options["event_id"])
        except (OSError, ReserveUnavailable):
            raise CommandError("The reserve audit object could not be verified. No data was returned.") from None
        self.stdout.write(json.dumps(payload, sort_keys=True, separators=(",", ":")))
