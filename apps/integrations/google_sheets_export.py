import csv
import io
import json
from urllib.parse import urlencode

from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from apps.businesses.access import Actions
from apps.core.import_export import entity_export_queryset, export_entity_response
from apps.integrations import google_oauth
from apps.integrations.google_http import google_request
from apps.integrations.google_models import GoogleSheetTransfer
from apps.integrations.google_sheets import MAX_COLUMNS, MAX_ROWS, assert_clients, locked_connection, read_metadata, spreadsheet_id


def transfer_status(transfer):
    return {"id": str(transfer.pk), "request_key": str(transfer.request_key), "status": transfer.status,
            "spreadsheet_id": transfer.spreadsheet_id, "row_count": transfer.row_count,
            "updated_at": transfer.updated_at}


def export_rows(connection, actor):
    assert_clients(connection, actor, Actions.VIEW)
    if entity_export_queryset(connection.business, "clients", user=actor).count() > MAX_ROWS:
        raise ValidationError("Google Sheets export supports at most 5000 clients.")
    response = export_entity_response(connection.business, "clients", user=actor)
    rows = list(csv.reader(io.StringIO(response.content.decode("utf-8-sig"))))
    if len(rows) > MAX_ROWS + 1 or any(len(row) > MAX_COLUMNS for row in rows):
        raise ValidationError("Google Sheets export exceeds the row or column limit.")
    if len(json.dumps(rows).encode("utf-8")) > 1024 * 1024:
        raise ValidationError("Google Sheets export exceeds the transfer size limit.")
    return rows


def export_clients(connection, actor, *, request_key, refresh=False):
    assert_clients(connection, actor, Actions.VIEW)
    token = google_oauth.access_token(connection, actor)
    with transaction.atomic():
        locked_connection(connection, actor)
        export_rows(connection, actor)
        transfer, created = GoogleSheetTransfer.objects.get_or_create(connection=connection, request_key=request_key,
            defaults={"kind": "export", "status": "creating"})
        if transfer.kind != "export":
            raise ValidationError("This request identifier was already used for an import.")
        if transfer.status == "expired":
            raise ValidationError("This export has expired. Start a new export.")
        if transfer.status == "succeeded" and not refresh:
            return transfer_status(transfer)

    # The reservation survives ambiguous provider errors and process termination.
    # Existing reservations discover by appProperties and never blindly create again.
    with transaction.atomic():
        locked_connection(connection, actor)
        assert_clients(connection, actor, Actions.VIEW)
        transfer = GoogleSheetTransfer.objects.select_for_update().get(pk=transfer.pk)
        if not transfer.spreadsheet_id:
            if created:
                remote = google_request("https://www.googleapis.com/drive/v3/files?fields=id", method="POST", token=token,
                    payload={"name": "PlatformaCRM Clients", "mimeType": "application/vnd.google-apps.spreadsheet",
                             "appProperties": {"platformaTransfer": str(transfer.pk)}})
                file_id = remote.get("id", "")
            else:
                query = "trashed = false and appProperties has { key='platformaTransfer' and value='" + str(transfer.pk) + "' }"
                remote = google_request("https://www.googleapis.com/drive/v3/files?" + urlencode({
                    "q": query, "fields": "files(id),nextPageToken", "pageSize": 2}), token=token)
                files = remote.get("files", [])
                if len(files) != 1 or remote.get("nextPageToken"):
                    raise ValidationError("Google has not confirmed the spreadsheet creation. Retry this export later; do not start a new export.")
                file_id = files[0].get("id", "")
            transfer.spreadsheet_id = spreadsheet_id(file_id)
            transfer.status = "ready"
            transfer.save(update_fields=["spreadsheet_id", "status", "updated_at"])

    with transaction.atomic():
        connection = locked_connection(connection, actor)
        transfer = GoogleSheetTransfer.objects.select_for_update().get(pk=transfer.pk)
        if transfer.status == "succeeded" and not refresh:
            return transfer_status(transfer)
        rows = export_rows(connection, actor)
        info = read_metadata(token, transfer.spreadsheet_id)
        if not info["sheets"]:
            raise ValidationError("The export spreadsheet no longer contains a grid sheet.")
        if transfer.status == "ready":
            transfer.sheet_id = info["sheets"][0]["sheetId"]
        sheet = next((item for item in info["sheets"] if item["sheetId"] == transfer.sheet_id), None)
        if sheet is None:
            raise ValidationError("The export sheet was deleted. Create a new export.")
        grid = sheet.get("gridProperties", {})
        requests = [
            {"updateSheetProperties": {"properties": {"sheetId": transfer.sheet_id, "gridProperties": {
                "rowCount": max(grid.get("rowCount", 0), len(rows)),
                "columnCount": max(grid.get("columnCount", 0), max(map(len, rows), default=1))}},
                "fields": "gridProperties.rowCount,gridProperties.columnCount"}},
            {"updateCells": {"range": {"sheetId": transfer.sheet_id}, "fields": "userEnteredValue",
                "rows": [{"values": [{"userEnteredValue": {"stringValue": cell}} for cell in row]} for row in rows]}},
        ]
        google_request("https://sheets.googleapis.com/v4/spreadsheets/" + transfer.spreadsheet_id + ":batchUpdate",
                       method="POST", token=token, payload={"requests": requests})
        transfer.status = "succeeded"
        transfer.row_count = max(0, len(rows) - 1)
        transfer.save(update_fields=["sheet_id", "status", "row_count", "updated_at"])
        connection.last_sync_at = timezone.now()
        connection.save(update_fields=["last_sync_at", "updated_at"])
        google_oauth.audit(connection, actor, "google_sheet_export")
        return transfer_status(transfer)
