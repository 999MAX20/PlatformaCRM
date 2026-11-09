import csv
from io import BytesIO, StringIO
from pathlib import Path

from django.conf import settings
from django.db import transaction
from rest_framework.exceptions import ValidationError

from apps.core.antivirus import ScanUnavailable, scan_stream
from apps.core.domain_errors import FileScanUnavailable
from apps.core.file_validation import validate_file_upload
from apps.core.import_export import normalize_tabular_rows
from apps.core.xlsx_reader import read_xlsx_rows, validate_xlsx_archive
from .drafts import add_source, lock_workspace


def parse_upload(upload):
    validate_file_upload(upload, allowed_extensions=["csv", "xlsx"], allowed_content_types=[
        "text/csv", "application/csv", "application/vnd.ms-excel",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", "application/octet-stream",
    ])
    upload.seek(0)
    content = upload.read(settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024 + 1)
    if len(content) > settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024:
        raise ValidationError("Import file exceeds the upload size limit.")
    try:
        scanned = scan_stream(BytesIO(content))
    except ScanUnavailable:
        raise FileScanUnavailable() from None
    if not scanned.clean:
        raise ValidationError("File was blocked by the security check.")
    if Path(upload.name).suffix.lower() == ".csv":
        try:
            reader = csv.DictReader(StringIO(content.decode("utf-8-sig"), newline=""))
            headers = [item.strip() for item in reader.fieldnames or []]
            if not headers or any(not item for item in headers) or len(set(headers)) != len(headers):
                raise ValidationError("CSV headers must be non-empty and unique.")
            rows = []
            for row in reader:
                if None in row or any(value is None for value in row.values()):
                    raise ValidationError("CSV rows must match the header columns.")
                rows.append(row)
                if len(rows) > settings.IMPORT_MAX_ROWS:
                    raise ValidationError("Import file has too many rows.")
            return [("", normalize_tabular_rows(rows))]
        except (UnicodeDecodeError, csv.Error):
            raise ValidationError("Use a UTF-8 CSV file with comma separators.") from None
    from openpyxl import load_workbook

    validate_xlsx_archive(content)
    try:
        workbook = load_workbook(BytesIO(content), read_only=True, data_only=True, keep_links=False)
        try:
            names = [sheet.title for sheet in workbook.worksheets]
        finally:
            workbook.close()
        if not names or len(names) > 12:
            raise ValidationError("An import supports between one and 12 worksheets.")
        sources = []
        for name in names:
            rows = read_xlsx_rows(content, sheet_name=name)
            try:
                sources.append((name, normalize_tabular_rows(rows)))
            finally:
                rows.close()
        return sources
    except (KeyError, ValueError, TypeError, OSError):
        raise ValidationError("XLSX file is invalid or unsupported.") from None


@transaction.atomic
def upload_sources(*, workspace_id, actor, version, upload, entity_type):
    workspace = lock_workspace(workspace_id, actor, version)
    sheets = parse_upload(upload)
    sources = []
    for sheet_name, rows in sheets:
        workspace, source = add_source(workspace_id=workspace.pk, actor=actor, version=workspace.version,
            rows=rows, filename=upload.name, entity_type=entity_type, sheet_name=sheet_name)
        sources.append(source)
    return workspace, sources
