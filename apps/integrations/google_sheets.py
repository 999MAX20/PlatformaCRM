import csv
import io
import re
from urllib.parse import quote, urlencode

from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from apps.businesses.access import Actions, Resources, assert_can
from apps.businesses.capabilities import assert_resource_enabled
from apps.core.file_validation import validate_file_upload
from apps.core.import_export import build_import_preview
from apps.core.models import ImportJob
from apps.integrations import google_oauth
from apps.integrations.google_http import google_request
from apps.integrations.google_models import GoogleConnection, GoogleSheetTransfer


MAX_ROWS = 5000
MAX_COLUMNS = 100


def assert_clients(connection, actor, action):
    google_oauth.assert_access(actor, connection.business)
    assert_can(actor, connection.business, Resources.CLIENTS, action)
    assert_resource_enabled(connection.business, Resources.CLIENTS)


def spreadsheet_id(value):
    if not re.fullmatch(r"[A-Za-z0-9_-]{10,255}", value):
        raise ValidationError("Invalid spreadsheet identifier.")
    return value


def locked_connection(connection, actor):
    current = GoogleConnection.objects.select_for_update().get(pk=connection.pk, actor=actor)
    google_oauth.assert_access(actor, current.business)
    if current.status != "connected" or current.revision != connection.revision:
        raise ValidationError("Google connection changed. Connect again.")
    return current


def metadata(connection, actor, file_id):
    assert_clients(connection, actor, Actions.CREATE)
    token = google_oauth.access_token(connection, actor)
    with transaction.atomic():
        locked_connection(connection, actor)
        return read_metadata(token, file_id)


def read_metadata(token, file_id):
    url = "https://sheets.googleapis.com/v4/spreadsheets/" + spreadsheet_id(file_id)
    result = google_request(url + "?" + urlencode({
        "fields": "spreadsheetId,properties(title),sheets(properties(sheetId,title,sheetType,gridProperties))"
    }), token=token)
    return {"id": file_id, "title": result.get("properties", {}).get("title", ""),
            "sheets": [sheet["properties"] for sheet in result.get("sheets", [])
                       if sheet.get("properties", {}).get("sheetType") == "GRID"]}


def import_snapshot(connection, actor, *, file_id, sheet_id, request_key, request):
    assert_clients(connection, actor, Actions.CREATE)
    token = google_oauth.access_token(connection, actor)
    saved_file = None
    try:
        with transaction.atomic():
            connection = locked_connection(connection, actor)
            assert_clients(connection, actor, Actions.CREATE)
            transfer = GoogleSheetTransfer.objects.filter(connection=connection, request_key=request_key).first()
            if transfer:
                if transfer.kind != "import" or transfer.spreadsheet_id != file_id or transfer.sheet_id != sheet_id:
                    raise ValidationError("This request identifier was already used for another transfer.")
                if transfer.import_job_id:
                    return transfer.import_job
                raise ValidationError("The import snapshot is unavailable. Start a new import.")
            info = read_metadata(token, file_id)
            sheet = next((item for item in info["sheets"] if item["sheetId"] == sheet_id), None)
            if sheet is None:
                raise ValidationError("Select an existing grid sheet.")
            grid = sheet.get("gridProperties", {})
            # Read the complete bounded grid; never silently import a truncated sheet.
            if grid.get("rowCount", 0) > MAX_ROWS + 1 or grid.get("columnCount", 0) > MAX_COLUMNS:
                raise ValidationError("Use a sheet with at most 5001 grid rows and 100 columns; remove unused rows or columns first.")
            sheet_range = "'" + sheet["title"].replace("'", "''") + "'"
            result = google_request("https://sheets.googleapis.com/v4/spreadsheets/" + spreadsheet_id(file_id)
                + "/values/" + quote(sheet_range, safe="") + "?valueRenderOption=FORMATTED_VALUE", token=token)
            rows = result.get("values", [])
            if len(rows) < 2:
                raise ValidationError("The sheet must contain a header and at least one client row.")
            if len(rows) > MAX_ROWS + 1 or any(len(row) > MAX_COLUMNS for row in rows):
                raise ValidationError("The sheet exceeds the import limit.")
            headers = [str(cell).strip() for cell in rows[0]]
            if not all(headers) or len(set(headers)) != len(headers) or any(len(row) > len(headers) for row in rows):
                raise ValidationError("Each populated column must have a unique, non-empty header.")
            buffer = io.StringIO()
            writer = csv.writer(buffer)
            writer.writerow(headers)
            writer.writerows(rows[1:])
            upload = SimpleUploadedFile("google-sheets.csv", buffer.getvalue().encode("utf-8"), content_type="text/csv")
            validate_file_upload(upload, allowed_extensions=["csv"], allowed_content_types=["text/csv"])
            job = ImportJob.objects.create(business=connection.business, actor=actor,
                entity_type=ImportJob.EntityTypes.CLIENTS, source_file=upload, original_filename="google-sheets.csv")
            saved_file = job.source_file
            job = build_import_preview(job, request=request)
            GoogleSheetTransfer.objects.create(connection=connection, request_key=request_key, kind="import",
                spreadsheet_id=file_id, sheet_id=sheet_id, import_job=job, status="snapshot", row_count=job.total_rows)
            connection.last_sync_at = timezone.now()
            connection.save(update_fields=["last_sync_at", "updated_at"])
            google_oauth.audit(connection, actor, "google_sheet_import_snapshot")
            return job
    except Exception:
        if saved_file:
            saved_file.delete(save=False)
        raise
