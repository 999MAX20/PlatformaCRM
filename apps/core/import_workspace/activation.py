from django.core import signing
from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from apps.businesses.access import Actions, Resources, assert_can
from apps.businesses.models import Business
from apps.core.audit import write_actor_audit_log
from apps.core.models import AuditLog, ImportWorkspace
from apps.integrations.models import BusinessEvent
from apps.scheduling.models import Appointment
from apps.scheduling.services import handle_appointment_created
from .drafts import assert_workspace_access, StaleImportVersion
from .entities import accessible_entity


SALT = "import-workspace-activation-v1"


def eligible_records(workspace, actor):
    assert_workspace_access(workspace, actor)
    if workspace.state != ImportWorkspace.States.IMPORTED:
        raise ValidationError("Only a completed import can activate future appointments.")
    ids = {row["id"] for row in workspace.result_json.get("rows", [])
           if row.get("entity_type") == "appointments" and row.get("id") and row.get("outcome") != "skipped"}
    records = []
    for record in Appointment.objects.filter(business=workspace.business, pk__in=ids, start_at__gt=timezone.now(),
            status__in=["created", "confirmed"], is_archived=False).select_related("client", "service", "resource"):
        accessible_entity(business=workspace.business, actor=actor, entity_type="appointments", pk=record.pk, action=Actions.UPDATE)
        assert_can(actor, workspace.business, Resources.CLIENTS, Actions.VIEW, obj=record.client)
        if BusinessEvent.objects.filter(business=workspace.business, deduplication_key=f"appointment:{record.pk}:created").exists():
            continue
        if not BusinessEvent.objects.filter(business=workspace.business, event_type="appointment.imported",
                deduplication_key=f"appointment:{record.pk}:imported").exists():
            continue
        records.append(record)
    return sorted(records, key=lambda record: record.pk)


def activation_preview(workspace, actor):
    records = eligible_records(workspace, actor)
    versions = {str(record.pk): record.updated_at.isoformat() for record in records}
    token = signing.dumps({"workspace": workspace.pk, "actor": actor.pk, "versions": versions}, salt=SALT)
    return {"token": token, "records": [{"id": record.pk, "start_at": record.start_at,
        "client_name": record.client.full_name, "service_name": record.service.name,
        "specialist_name": record.resource.name if record.resource else ""} for record in records]}


@transaction.atomic
def activate_records(*, workspace_id, actor, token, ids):
    workspace = ImportWorkspace.objects.select_for_update().select_related("business").get(pk=workspace_id)
    assert_workspace_access(workspace, actor)
    Business.objects.select_for_update().get(pk=workspace.business_id)
    try:
        payload = signing.loads(token, salt=SALT, max_age=3600)
    except signing.BadSignature:
        raise StaleImportVersion("The activation preview expired. Review the current appointments again.") from None
    if payload.get("workspace") != workspace.pk or payload.get("actor") != actor.pk:
        raise ValidationError("This activation preview is not available.")
    if not ids or len(set(ids)) != len(ids) or any(str(pk) not in payload["versions"] for pk in ids):
        raise ValidationError("Select only appointments shown in this preview.")
    records = list(Appointment.objects.select_for_update().filter(business=workspace.business, pk__in=ids).order_by("pk"))
    eligible = {record.pk: record for record in eligible_records(workspace, actor)}
    activated = []
    for record in records:
        accessible_entity(business=workspace.business, actor=actor, entity_type="appointments", pk=record.pk, action=Actions.UPDATE)
        if BusinessEvent.objects.filter(business=workspace.business, deduplication_key=f"appointment:{record.pk}:created").exists():
            activated.append(record.pk)
            continue
        if record.pk not in eligible or record.updated_at.isoformat() != payload["versions"][str(record.pk)]:
            raise StaleImportVersion("Appointments changed. Review the activation list again.")
        handle_appointment_created(record)
        write_actor_audit_log(actor=actor, action=AuditLog.Actions.UPDATE, instance=record,
            metadata={"kind": "import_effects_activated", "workspace_id": workspace.pk})
        activated.append(record.pk)
    if len(activated) != len(ids):
        raise StaleImportVersion("Appointments changed. Review the activation list again.")
    return {"activated": activated}
