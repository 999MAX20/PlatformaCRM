import hashlib
import json
from copy import deepcopy

from django.conf import settings
from django.db import transaction
from rest_framework.exceptions import APIException, PermissionDenied, ValidationError

from apps.businesses.access import Actions, Resources, assert_can
from apps.businesses.capabilities import assert_resource_enabled
from apps.core.models import ImportWorkspace, ImportWorkspaceSource, safe_original_filename
from apps.core.permissions import user_can_access_business


class StaleImportVersion(APIException):
    status_code = 409
    default_detail = "The import draft changed. Reload before saving or confirming."
    default_code = "stale_import_version"


def assert_workspace_access(workspace, actor):
    if not actor.is_active or workspace.actor_id != actor.pk or not user_can_access_business(actor, workspace.business):
        raise PermissionDenied("This import draft is not available.")
    assert_resource_enabled(workspace.business, Resources.INTEGRATIONS)
    assert_can(actor, workspace.business, Resources.INTEGRATIONS, Actions.MANAGE)


def lock_workspace(workspace_id, actor, version, *, editable=True, operation_token=None):
    workspace = ImportWorkspace.objects.select_for_update().select_related("business").get(pk=workspace_id)
    assert_workspace_access(workspace, actor)
    operation = workspace.operation_json or {}
    if operation.get("status") in {"pending", "running"} and (not operation_token or operation.get("claim_token") != operation_token):
        raise StaleImportVersion("A background operation is in progress. Wait for its result.")
    if type(version) is not int or version != workspace.version:
        raise StaleImportVersion()
    if editable and workspace.state not in {ImportWorkspace.States.DRAFT, ImportWorkspace.States.READY}:
        raise ValidationError("This import draft can no longer be edited.")
    return workspace


def invalidate_preview(workspace):
    workspace.version += 1
    workspace.state = ImportWorkspace.States.DRAFT
    workspace.validated_version = None
    workspace.report_json = {}
    workspace.operation_json = {}
    workspace.save(update_fields=["version", "state", "validated_version", "report_json", "operation_json", "updated_at"])


def create_workspace(*, business, actor):
    workspace = ImportWorkspace(business=business, actor=actor)
    assert_workspace_access(workspace, actor)
    workspace.save()
    return workspace


def checked_rows(rows):
    if not isinstance(rows, list) or not 0 < len(rows) <= settings.IMPORT_MAX_ROWS:
        raise ValidationError("The source must contain a bounded non-empty list of rows.")
    headers = list(rows[0]) if isinstance(rows[0], dict) else []
    if not headers or len(headers) > settings.IMPORT_MAX_COLUMNS:
        raise ValidationError("The source has invalid columns.")
    if any(not isinstance(key, str) or not key.strip() or len(key) > 255 for key in headers):
        raise ValidationError("The source has invalid column names.")
    for row in rows:
        if not isinstance(row, dict) or set(row) != set(headers):
            raise ValidationError("Every source row must have the same columns.")
        if any(not isinstance(value, str) or len(value) > 20000 for value in row.values()):
            raise ValidationError("A source cell exceeds the supported text limit.")
    serialized = json.dumps(rows, ensure_ascii=False, sort_keys=True).encode("utf-8")
    if len(serialized) > settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024:
        raise ValidationError("The parsed source exceeds the import size limit.")
    return hashlib.sha256(serialized).hexdigest()


@transaction.atomic
def add_source(*, workspace_id, actor, version, rows, filename, entity_type, sheet_name=""):
    workspace = lock_workspace(workspace_id, actor, version)
    if workspace.sources.count() >= 12:
        raise ValidationError("An import draft supports at most 12 sources.")
    if entity_type not in ImportWorkspaceSource.Entities.values:
        raise ValidationError({"entity_type": "Unsupported import entity."})
    digest = checked_rows(rows)
    total = sum(len(item) for item in workspace.sources.values_list("rows_json", flat=True))
    if total + len(rows) > settings.IMPORT_MAX_ROWS:
        raise ValidationError("The combined sources exceed the import row limit.")
    source = ImportWorkspaceSource.objects.create(
        workspace=workspace, original_filename=safe_original_filename(filename),
        entity_type=entity_type, sheet_name=sheet_name[:255], rows_json=rows, digest=digest,
    )
    invalidate_preview(workspace)
    return workspace, source


def _row_number(value, size):
    if not isinstance(value, str) or not value.isascii() or not value.isdigit() or str(int(value)) != value:
        raise ValidationError("Invalid source row number.")
    number = int(value)
    if not 1 <= number <= size:
        raise ValidationError("Source row number is out of range.")
    return number


def checked_corrections(corrections, rows):
    if not isinstance(corrections, dict) or len(corrections) > len(rows):
        raise ValidationError({"corrections": "Expected source row numbers and changed cells."})
    headers = set(rows[0])
    for number, cells in corrections.items():
        _row_number(number, len(rows))
        if not isinstance(cells, dict) or set(cells) - headers:
            raise ValidationError({"corrections": "Unknown source column."})
        if any(not isinstance(value, str) or len(value) > 20000 for value in cells.values()):
            raise ValidationError({"corrections": "Cell values must be bounded text."})
    return deepcopy(corrections)


@transaction.atomic
def correct_source(*, workspace_id, source_id, actor, version, corrections, excluded):
    workspace = lock_workspace(workspace_id, actor, version)
    source = workspace.sources.filter(pk=source_id).first()
    if source is None:
        raise ValidationError("Source is not available in this draft.")
    corrected = checked_corrections(corrections, source.rows_json)
    if not isinstance(excluded, list) or len(excluded) > len(source.rows_json):
        raise ValidationError({"excluded": "Expected source row numbers."})
    if any(type(number) is not int or not 1 <= number <= len(source.rows_json) for number in excluded):
        raise ValidationError({"excluded": "Invalid source row number."})
    if len(set(excluded)) != len(excluded):
        raise ValidationError({"excluded": "Source row numbers must be unique."})
    effective = deepcopy(source.rows_json)
    for number, cells in corrected.items():
        effective[int(number) - 1].update(cells)
    checked_rows(effective)
    source.corrections_json = corrected
    source.excluded_json = sorted(excluded)
    source.save(update_fields=["corrections_json", "excluded_json"])
    invalidate_preview(workspace)
    return workspace, source


def prepared_rows(source, *, include_excluded=False):
    excluded = set(source.excluded_json)
    for number, original in enumerate(source.rows_json, start=1):
        if number in excluded and not include_excluded:
            continue
        yield {
            "row": number,
            "original": deepcopy(original),
            "values": {**original, **source.corrections_json.get(str(number), {})},
            "excluded": number in excluded,
        }
