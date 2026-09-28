import json

from django.core.management.base import BaseCommand, CommandError
from django.db.models import Count

from apps.core.antivirus import ScanUnavailable, scanner_health
from apps.core.file_scanning import scan_due_attachments
from apps.core.models import FileAttachment


class Command(BaseCommand):
    help = "Check antivirus/signature readiness and quarantine counts; optionally process due files."

    def add_arguments(self, parser):
        parser.add_argument("--process", action="store_true", help="Mutates scan states in the configured DB; requires an authorized target.")
        parser.add_argument("--limit", type=int, default=10)

    def handle(self, *args, **options):
        try:
            engine = scanner_health()
        except ScanUnavailable as exc:
            raise CommandError(exc.code) from None
        processed = scan_due_attachments(options["limit"]) if options["process"] else 0
        counts = dict(FileAttachment.objects.values_list("scan_status").annotate(total=Count("id")))
        self.stdout.write(json.dumps({"engine": engine, "processed": processed, "counts": counts}))
