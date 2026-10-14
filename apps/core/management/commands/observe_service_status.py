from django.core.management.base import BaseCommand, CommandError

from apps.businesses.models import Business
from apps.core.service_status import observe_business_service, observe_service_batch


class Command(BaseCommand):
    help = "Observe internal background delays and record incident transitions (no external probes)."

    def add_arguments(self, parser):
        parser.add_argument("--business", type=int)
        parser.add_argument("--limit", type=int, default=100)

    def handle(self, *args, **options):
        if options["business"]:
            try:
                observe_business_service(options["business"])
            except Business.DoesNotExist:
                raise CommandError("Business does not exist.")
            count = 1
        else:
            count = observe_service_batch(limit=options["limit"])
        self.stdout.write(f"Observed {count} businesses.")
