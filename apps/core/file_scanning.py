"""Durable quarantine and scan leases; never release an unverified attachment."""
from datetime import timedelta
import hashlib
from tempfile import SpooledTemporaryFile
from uuid import uuid4

from django.conf import settings
from django.db import transaction
from django.db.models import F, Q
from django.db.models.functions import Coalesce
from django.utils import timezone
from rest_framework.exceptions import APIException

from apps.core.antivirus import ScanUnavailable, scan_stream
from apps.core.models import AuditLog, FileAttachment


class FileQuarantined(APIException):
    status_code = 423
    default_detail = "File is unavailable until its security check succeeds."
    default_code = "file_quarantined"


def due_scans(now=None):
    now = now or timezone.now()
    return (
        Q(scan_status="pending")
        | Q(scan_status="error", scan_next_attempt_at__lte=now)
        | Q(scan_status="error", scan_next_attempt_at__isnull=True)
        | Q(scan_status="scanning", scan_started_at__lte=now - timedelta(seconds=settings.FILE_SCAN_LEASE_SECONDS))
        | Q(scan_status="scanning", scan_started_at__isnull=True)
    )


def scan_attachment(attachment_id, business_id):
    now = timezone.now()
    token = uuid4()
    rows = FileAttachment.objects.filter(id=attachment_id, business_id=business_id)
    claimed = rows.filter(due_scans(now)).update(
        scan_status="scanning", scan_token=token, scan_started_at=now,
        scan_attempts=F("scan_attempts") + 1, scan_error_code="",
        scan_sha256="", scanned_at=None,
    )
    if not claimed:
        return None
    attachment = rows.get(scan_token=token)
    result = None
    error_code = ""
    try:
        with attachment.file.open("rb") as source:
            result = scan_stream(source)
        if result.size != attachment.size:
            raise ScanUnavailable("file_size_changed")
        state = "clean" if result.clean else "infected"
    except ScanUnavailable as exc:
        state, error_code = "error", exc.code
    except Exception:
        # Storage providers may include signed URLs/keys in their exceptions.
        state, error_code = "error", "storage_unavailable"
    finished = timezone.now()
    delay = min(3600, 30 * 2 ** min(attachment.scan_attempts - 1, 7))
    with transaction.atomic():
        changed = rows.filter(scan_token=token, scan_status="scanning", file=attachment.file.name).update(
            scan_status=state, scan_token=None, scan_started_at=None,
            scanned_at=finished if state != "error" else None,
            scan_next_attempt_at=finished + timedelta(seconds=delay) if state == "error" else None,
            scan_error_code=error_code,
            scan_sha256=result.sha256 if result and state != "error" else "",
            scan_engine=result.engine if result else "",
        )
        if changed:
            AuditLog.objects.create(
                business_id=business_id, action=AuditLog.Actions.UPDATE,
                category=AuditLog.Categories.SYSTEM,
                risk_level=AuditLog.RiskLevels.HIGH if state == "infected" else AuditLog.RiskLevels.LOW,
                entity_type="FileAttachment", entity_id=str(attachment_id),
                metadata={"kind": "file_security_scan", "status": state, "error_code": error_code},
            )
    return state if changed else None


def scan_due_attachments(limit=10):
    candidates = list(FileAttachment.objects.filter(due_scans()).annotate(scan_due_at=Coalesce("scan_next_attempt_at", "created_at")).order_by("scan_due_at", "id")
                      .values_list("id", "business_id")[:max(1, min(int(limit), 100))])
    return sum(scan_attachment(pk, business_id) is not None for pk, business_id in candidates)


def open_clean_attachment(attachment):
    """Serve an immutable checked snapshot, never bytes replaced after the scan."""
    if attachment.scan_status != "clean" or not attachment.scan_sha256:
        raise FileQuarantined()
    snapshot = SpooledTemporaryFile(max_size=1024 * 1024, mode="w+b")
    try:
        digest = hashlib.sha256()
        size = 0
        with attachment.file.open("rb") as source:
            while chunk := source.read(64 * 1024):
                size += len(chunk)
                if size > settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024:
                    raise FileQuarantined()
                digest.update(chunk)
                snapshot.write(chunk)
        if size != attachment.size or digest.hexdigest() != attachment.scan_sha256:
            raise FileQuarantined()
        # A concurrent quarantine/replacement invalidates this request too.
        if not FileAttachment.objects.filter(
            pk=attachment.pk, business_id=attachment.business_id, scan_status="clean",
            scan_sha256=attachment.scan_sha256, file=attachment.file.name,
        ).exists():
            raise FileQuarantined()
        snapshot.seek(0)
        return snapshot
    except Exception:
        snapshot.close()
        with transaction.atomic():
            changed = FileAttachment.objects.filter(
                pk=attachment.pk, scan_status="clean", scan_sha256=attachment.scan_sha256,
            ).update(
                scan_status="error", scan_error_code="file_integrity_unavailable",
                scan_sha256="", scan_next_attempt_at=timezone.now(),
            )
            if changed:
                AuditLog.objects.create(
                    business_id=attachment.business_id, action=AuditLog.Actions.UPDATE,
                    category=AuditLog.Categories.SYSTEM, risk_level=AuditLog.RiskLevels.HIGH,
                    entity_type="FileAttachment", entity_id=str(attachment.pk),
                    metadata={"kind": "file_security_quarantine", "error_code": "file_integrity_unavailable"},
                )
        raise FileQuarantined() from None
