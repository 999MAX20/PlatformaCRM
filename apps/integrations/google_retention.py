"""Bounded local cleanup; never delete remote files/events or CRM domain records."""
import hashlib
from datetime import timedelta

from django.db import connection as database, transaction
from django.db.models import Exists, F, OuterRef, Q
from django.utils import timezone

from apps.businesses.models import Business
from apps.core.models import AuditLog, FileAttachment, ImportJob
from apps.integrations.google_calendar_models import GoogleCalendarBinding, GoogleCalendarBusy
from apps.integrations.google_models import (
    GoogleConnection, GoogleOAuthAttempt, GoogleRetentionFile, GoogleRetentionState,
    GoogleSheetTransfer,
)


PROVIDERS = ("google_sheets", "google_calendar")
# Five-minute scheduler cadence plus one bounded task run before the maximum age.
SWEEP_HEADROOM = timedelta(minutes=10)


def _lock(queryset):
    options = {}
    if database.features.has_select_for_update_skip_locked:
        options["skip_locked"] = True
    if database.features.has_select_for_update_of:
        options["of"] = ("self",)
    return queryset.select_for_update(**options)


def _expired_jobs(now, business_id):
    terminal = Q(status__in=["imported", "cancelled", "failed"])
    completed = Q(imported_at__lte=now - timedelta(days=30)) | Q(
        imported_at__isnull=True, updated_at__lte=now - timedelta(days=30))
    expired = terminal & completed | ~terminal & Q(created_at__lte=now - timedelta(days=7))
    jobs = ImportJob.objects.filter(
        googlesheettransfer__connection__provider="google_sheets",
        googlesheettransfer__connection__business_id=F("business_id"),
        googlesheettransfer__kind="import").exclude(source_file="").filter(expired)
    if business_id is not None:
        jobs = jobs.filter(business_id=business_id)
    return jobs.distinct()


def _scrub_job(pk, now, business_id):
    with transaction.atomic():
        job = _lock(ImportJob.objects.filter(pk=pk)).first()
        if job is None or not _expired_jobs(now, business_id).filter(pk=pk).exists():
            return False
        GoogleRetentionFile.objects.get_or_create(storage_name=job.source_file.name,
            defaults={"business_id": job.business_id})
        job.source_file = ""
        job.original_filename = job.error = ""
        summary = (job.preview_json or {}).get("import_summary") or {}
        summary = {key: value for key, value in summary.items()
                   if key in {"total_rows", "created", "updated", "skipped", "errors", "duplicates"}
                   and isinstance(value, int) and not isinstance(value, bool)}
        job.mapping_json = job.duplicates_json = job.errors_json = {}
        job.preview_json = {"retention_expired": True, "import_summary": summary}
        if job.status in {"uploaded", "previewed"}:
            job.status = "cancelled"
        job.save(update_fields=["source_file", "original_filename", "error", "mapping_json",
            "preview_json", "duplicates_json", "errors_json", "status", "updated_at"])
        return True


def _expired_summaries(now, business_id):
    jobs = ImportJob.objects.filter(
        googlesheettransfer__connection__provider="google_sheets",
        googlesheettransfer__connection__business_id=F("business_id"),
        googlesheettransfer__kind="import", source_file="",
        preview_json__retention_expired=True,
    ).filter(Q(imported_at__lte=now-timedelta(days=90)) | Q(
        imported_at__isnull=True, created_at__lte=now-timedelta(days=90)))
    if business_id is not None:
        jobs = jobs.filter(business_id=business_id)
    return jobs.distinct()


def _delete_file(pk, now):
    with transaction.atomic():
        pending = _lock(GoogleRetentionFile.objects.filter(pk=pk)).first()
        if pending is None:
            return "skipped"
        name = pending.storage_name
        # Generated import paths are never reused by upload APIs. Protect any legacy aliases.
        if ImportJob.objects.filter(source_file=name).exists() or FileAttachment.objects.filter(file=name).exists():
            pending.error_code = "shared_reference"
            pending.next_attempt_at = now + timedelta(minutes=5)
            pending.save(update_fields=["error_code", "next_attempt_at"])
            return "protected"
        try:
            ImportJob._meta.get_field("source_file").storage.delete(name)
        except Exception:
            pending.attempts += 1
            pending.error_code = "storage_delete_failed"
            pending.next_attempt_at = now + timedelta(minutes=5)
            pending.save(update_fields=["attempts", "error_code", "next_attempt_at"])
            return "failed"
        # A crash before commit leaves the retry row; storage.delete is idempotent.
        pending.delete()
        return "deleted"


def cleanup_google(*, apply=False, business_id=None, batch_size=100, now=None):
    if not 1 <= batch_size <= 1000:
        raise ValueError("batch_size must be between 1 and 1000")
    if business_id is not None and business_id <= 0:
        raise ValueError("business_id must be positive")
    now = now or timezone.now()
    deadline = now + SWEEP_HEADROOM
    attempts = GoogleOAuthAttempt.objects.filter(connection__provider__in=PROVIDERS,
        created_at__lte=deadline - timedelta(hours=24))
    connections = GoogleConnection.objects.filter(provider__in=PROVIDERS, status="disconnected",
        disconnected_at__lte=deadline - timedelta(days=30)).annotate(
            retained_transfers=Exists(GoogleSheetTransfer.objects.filter(connection_id=OuterRef("pk")).exclude(status="expired")),
            retained_names=Exists(GoogleCalendarBinding.objects.filter(connection_id=OuterRef("pk")).exclude(calendar_name="")),
        ).filter((~Q(subject="") & ~Q(subject__startswith="sha256:")) | ~Q(email="")
                 | Q(retained_transfers=True) | Q(retained_names=True))
    audits = AuditLog.objects.filter(entity_type="GoogleConnection", category="integration",
        metadata__provider__in=PROVIDERS, created_at__lte=deadline - timedelta(days=90))
    busy = GoogleCalendarBusy.objects.filter(
        Q(binding__enabled=False) | Q(binding__connection__status="disconnected"))
    files = GoogleRetentionFile.objects.all()
    if business_id is not None:
        attempts = attempts.filter(connection__business_id=business_id)
        connections = connections.filter(business_id=business_id)
        audits = audits.filter(business_id=business_id)
        busy = busy.filter(binding__connection__business_id=business_id)
        files = files.filter(business_id=business_id)
    jobs = _expired_jobs(deadline, business_id)
    summaries = _expired_summaries(deadline, business_id)
    counts = {"attempts_due": attempts.count(), "snapshots_due": jobs.count(),
        "summaries_due": summaries.count(),
        "connections_due": connections.distinct().count(), "audits_due": audits.count(),
        "busy_due": busy.count(), "files_pending": files.count()}
    if not apply:
        return {"mode": "dry_run", **counts}
    if business_id is None:
        GoogleRetentionState.objects.update_or_create(key="google", defaults={"last_started_at": now})
    result = {"mode": "apply", "attempts": 0, "snapshots": 0, "connections": 0,
        "audits": 0, "summaries": 0, "busy": 0, "files_deleted": 0, "files_failed": 0, "files_protected": 0}
    for queryset, key in ((attempts, "attempts"), (audits, "audits"), (busy, "busy")):
        with transaction.atomic():
            ids = list(_lock(queryset.order_by("pk")).values_list("pk", flat=True)[:batch_size])
            result[key] = queryset.filter(pk__in=ids).delete()[0]
    for pk in list(jobs.order_by("pk").values_list("pk", flat=True)[:batch_size]):
        result["snapshots"] += int(_scrub_job(pk, deadline, business_id))
    for pk, tenant in list(summaries.order_by("pk").values_list("pk", "business_id")[:batch_size]):
        with transaction.atomic():
            Business.objects.select_for_update().get(pk=tenant)
            job = _lock(ImportJob.objects.filter(pk=pk)).first()
            if job is None or not _expired_summaries(deadline, business_id).filter(pk=pk).exists():
                continue
            GoogleSheetTransfer.objects.filter(import_job=job).update(
                status="expired", spreadsheet_id="", sheet_id=0, row_count=0)
            job.delete()
            result["summaries"] += 1
    for pk, tenant in list(connections.values_list("pk", "business_id").distinct()[:batch_size]):
        with transaction.atomic():
            Business.objects.select_for_update().get(pk=tenant)
            current = _lock(GoogleConnection.objects.filter(pk=pk)).first()
            if current is None or current.status != "disconnected" or not current.disconnected_at or current.disconnected_at > deadline - timedelta(days=30):
                continue
            if current.subject and not current.subject.startswith("sha256:"):
                # Older OAuth code rejects this marker rather than accepting a different account.
                current.subject = "sha256:" + hashlib.sha256(current.subject.encode()).hexdigest()
            current.email = ""
            current.encrypted_access = current.encrypted_refresh = ""
            current.scopes = []
            current.access_expires_at = None
            current.save(update_fields=["subject", "email", "scopes",
                "encrypted_access", "encrypted_refresh", "access_expires_at"])
            binding_ids = list(GoogleCalendarBinding.objects.filter(connection=current).exclude(
                calendar_name="").values_list("pk", flat=True)[:batch_size])
            GoogleCalendarBinding.objects.filter(pk__in=binding_ids).update(calendar_name="")
            # Keep request-key tombstones: replay must never silently create a second export.
            transfer_ids = list(GoogleSheetTransfer.objects.filter(connection=current).exclude(
                status="expired").values_list("pk", flat=True)[:batch_size])
            GoogleSheetTransfer.objects.filter(pk__in=transfer_ids).update(
                spreadsheet_id="", sheet_id=0, row_count=0, status="expired")
            result["connections"] += 1
    due_files = files.filter(Q(next_attempt_at__isnull=True) | Q(next_attempt_at__lte=now))
    for pk in list(due_files.order_by("pk").values_list("pk", flat=True)[:batch_size]):
        outcome = _delete_file(pk, now)
        if outcome != "skipped":
            result["files_" + outcome] += 1
    result["remaining"] = cleanup_google(business_id=business_id, now=now, batch_size=batch_size)
    if business_id is None:
        defaults = {"last_finished_at": timezone.now(), "counts": result}
        if not result["files_failed"] and not result["files_protected"]:
            defaults["last_success_at"] = timezone.now()
        GoogleRetentionState.objects.filter(key="google").update(**defaults)
    return result
