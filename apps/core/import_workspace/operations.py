import uuid
import logging

from django.db import transaction
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from rest_framework.exceptions import ValidationError

from apps.core.models import ImportWorkspace
from .drafts import assert_workspace_access, StaleImportVersion


def enqueue(workspace_id, operation_id):
    from apps.core.tasks import process_import_workspace_task
    try:
        process_import_workspace_task.delay(workspace_id, operation_id)
    except Exception:
        with transaction.atomic():
            workspace = ImportWorkspace.objects.select_for_update().get(pk=workspace_id)
            if workspace.operation_json.get("id") == operation_id and workspace.operation_json.get("status") == "pending":
                workspace.operation_json = {**workspace.operation_json, "status": "failed", "error": "queue_unavailable"}
                workspace.save(update_fields=["operation_json", "updated_at"])


@transaction.atomic
def request_operation(*, workspace_id, actor, version, action):
    workspace = ImportWorkspace.objects.select_for_update().select_related("business").get(pk=workspace_id)
    assert_workspace_access(workspace, actor)
    if action not in {"preview", "confirm"}:
        raise ValidationError("Unsupported import operation.")
    if workspace.version != version:
        raise StaleImportVersion()
    current = workspace.operation_json or {}
    if current.get("status") in {"pending", "running"}:
        if current.get("action") != action:
            raise StaleImportVersion("Another import operation is in progress.")
        transaction.on_commit(lambda: enqueue(workspace.pk, current["id"]))
        return workspace
    if workspace.state == "imported" and action == "confirm":
        return workspace
    if workspace.state not in {"draft", "ready"}:
        raise ValidationError("This draft can no longer be processed.")
    if action == "confirm" and (workspace.state != "ready" or workspace.validated_version != version):
        raise ValidationError("Check the current draft before confirming.")
    operation_id = uuid.uuid4().hex
    workspace.operation_json = {"id": operation_id, "action": action, "status": "pending", "version": version,
        "requested_at": timezone.now().isoformat(), "total_rows": sum(len(source.rows_json) for source in workspace.sources.all())}
    workspace.save(update_fields=["operation_json", "updated_at"])
    transaction.on_commit(lambda: enqueue(workspace.pk, operation_id))
    return workspace


def process_operation(workspace_id, operation_id):
    with transaction.atomic():
        workspace = ImportWorkspace.objects.select_for_update().get(pk=workspace_id)
        operation = workspace.operation_json or {}
        if operation.get("id") != operation_id or operation.get("status") not in {"pending", "running"}:
            return
        started = parse_datetime(operation.get("started_at", ""))
        if operation["status"] == "running" and started and started > timezone.now() - timezone.timedelta(minutes=5):
            return
        claim_token = uuid.uuid4().hex
        workspace.operation_json = {**operation, "status": "running", "claim_token": claim_token, "started_at": timezone.now().isoformat()}
        workspace.save(update_fields=["operation_json", "updated_at"])
    try:
        with transaction.atomic():
            workspace = ImportWorkspace.objects.select_for_update().select_related("business", "actor").get(pk=workspace_id)
            operation = workspace.operation_json
            if operation.get("id") != operation_id or operation.get("claim_token") != claim_token:
                return
            from .engine import preview_workspace, confirm_workspace
            execute = preview_workspace if operation["action"] == "preview" else confirm_workspace
            workspace = execute(workspace_id=workspace_id, actor=workspace.actor,
                version=operation["version"], operation_token=claim_token)
            workspace.operation_json = {**operation, "status": "succeeded", "completed_at": timezone.now().isoformat()}
            workspace.save(update_fields=["operation_json", "updated_at"])
    except Exception as exc:
        from rest_framework.exceptions import APIException
        code = "operation_failed"
        if isinstance(exc, StaleImportVersion):
            code = "preview_changed"
        elif isinstance(exc, APIException):
            code = "validation_failed" if exc.status_code == 400 else "access_changed"
        logging.getLogger(__name__).warning("imports.operation_failed", extra={"workspace_id": workspace_id, "operation_id": operation_id, "error_type": type(exc).__name__, "error_code": code})
        with transaction.atomic():
            workspace = ImportWorkspace.objects.select_for_update().get(pk=workspace_id)
            if workspace.operation_json.get("id") == operation_id and workspace.operation_json.get("claim_token") == claim_token:
                workspace.operation_json = {**workspace.operation_json, "status": "failed", "error": code}
                workspace.save(update_fields=["operation_json", "updated_at"])
