"""Import scheduling commands preserve booking guards without creating delivery work."""
from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from apps.activities.services import create_activity_event
from apps.businesses.access import Actions, Resources, assert_can
from apps.businesses.capabilities import assert_resource_enabled
from apps.businesses.models import Business
from apps.core.audit import write_actor_audit_log
from apps.core.models import AuditLog
from apps.scheduling.models import Appointment, Resource
from apps.scheduling.record_commands import validate_responsible


@transaction.atomic
def create_imported_record(*, business, actor, client, service, specialist, start_at,
                           status="created", notes="", reason="", import_reference=""):
    from apps.branches.access import assert_branch_access
    from apps.branches.schedule import appointment_snapshot
    from apps.scheduling.availability import validate_appointment_availability

    business = Business.objects.select_for_update().get(pk=business.pk)
    assert_resource_enabled(business, Resources.APPOINTMENTS)
    assert_resource_enabled(business, Resources.CLIENTS)
    client = type(client).objects.select_for_update().get(pk=client.pk)
    service = type(service).objects.select_for_update().get(pk=service.pk)
    specialist = type(specialist).objects.select_for_update().get(pk=specialist.pk)
    for item in (client, service, specialist):
        if item.business_id != business.pk:
            raise ValidationError("All links must belong to the import business.")
    if client.is_archived or service.is_archived or not service.is_active:
        raise ValidationError("Select an active client and service.")
    if specialist.resource_type != Resource.ResourceTypes.STAFF or not specialist.is_active or specialist.retired_at:
        raise ValidationError("Select an active specialist.")
    if status not in {"created", "confirmed", "completed", "cancelled", "no_show"}:
        raise ValidationError({"status": "Select a supported import status."})
    if start_at > timezone.now() and status in {"completed", "no_show"}:
        raise ValidationError({"status": "A future visit cannot already be completed or missed."})
    if status in {"cancelled", "no_show"} and not reason.strip():
        raise ValidationError({"reason": "Provide the reason recorded in the source."})
    assert_can(actor, business, Resources.CLIENTS, Actions.VIEW, obj=client)
    validate_responsible(business=business, actor=actor, user=actor)
    snapshot = appointment_snapshot(business, service, specialist)
    if snapshot["branch"]:
        assert_branch_access(actor, business, snapshot["branch"], active=True)
    candidate = Appointment(business=business, client=client, service=service, resource=specialist,
                            responsible_user=actor, **snapshot)
    assert_can(actor, business, Resources.APPOINTMENTS, Actions.CREATE, obj=candidate)
    end_at = validate_appointment_availability(business, service, start_at, resource=specialist, branch=snapshot["branch"])
    appointment = Appointment.objects.create(business=business, client=client, service=service, resource=specialist,
        responsible_user=actor, start_at=start_at, end_at=end_at, status=status, notes=notes,
        source=Appointment.Sources.MANUAL, **snapshot)
    metadata = {"kind": "import", "reference": import_reference, "status": status,
                "reason": reason, "creation_effects": "suppressed"}
    write_actor_audit_log(actor=actor, action=AuditLog.Actions.CREATE, instance=appointment, metadata=metadata)
    create_activity_event(business=business, actor=actor, client=client, instance=appointment,
        event_type="appointment_imported", category="appointment", source="import", text="Appointment imported", metadata=metadata)
    from apps.integrations.models import BusinessEvent
    BusinessEvent.objects.create(business=business, source="manual_import", event_type="appointment.imported",
        deduplication_key=f"appointment:{appointment.pk}:imported", external_id=str(appointment.pk),
        occurred_at=start_at, processed_at=timezone.now(), status=BusinessEvent.Statuses.PROCESSED,
        payload_json={"appointment_id": appointment.pk, "creation_effects": "suppressed", "reference": import_reference})
    return appointment
