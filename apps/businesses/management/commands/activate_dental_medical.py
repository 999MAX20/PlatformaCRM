import json

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import DatabaseError

from apps.businesses.medical_rollout import activate_medical_profile, preview_medical_rollout
from apps.businesses.models import Business
from apps.core.domain_errors import DomainAPIException


class Command(BaseCommand):
    help = "Preview the additive dental medical rollout; --apply requires release readiness."

    def add_arguments(self, parser):
        parser.add_argument("--apply", action="store_true", help="Apply to all existing dentistry businesses.")

    def handle(self, *args, **options):
        apply = options["apply"]
        if apply and not settings.DENTAL_MEDICAL_RELEASE_ENABLED:
            raise CommandError("DENTAL_MEDICAL_RELEASE_ENABLED must be enabled after release acceptance.")
        counts = {"planned": 0, "activated": 0, "unchanged": 0, "failed": 0}
        operation = activate_medical_profile if apply else preview_medical_rollout
        ids = Business.objects.filter(business_type=Business.BusinessTypes.DENTISTRY).order_by("pk").values_list("pk", flat=True)
        for business_id in ids.iterator(chunk_size=100):
            try:
                result = operation(business_id=business_id)
                counts[result["status"]] += 1
            except (DomainAPIException, DatabaseError):
                counts["failed"] += 1
                self.stderr.write(f"Business {business_id}: rollout failed; configuration and audit require review.")
        self.stdout.write(json.dumps({"mode": "apply" if apply else "dry_run", **counts}, sort_keys=True))
        if counts["failed"]:
            raise CommandError("Some dentistry businesses were not updated; resolve the failures and rerun.")
