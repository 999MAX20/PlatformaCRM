"""Manual single-visit command; legacy Lead/AI booking remains separate."""
from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied, ValidationError

from apps.activities.services import create_activity_event
from apps.activities.taxonomy import ActivityEvents
from apps.businesses.access import Actions, Resources, assert_can, can, team_user_ids_for
from apps.businesses.assignment_policy import resolve_assignment_member
from apps.businesses.capabilities import assert_resource_enabled
from apps.businesses.models import Business, RolePermission
from apps.core.audit import write_actor_audit_log
from apps.core.domain_errors import ScheduleConflict
from apps.core.models import AuditLog
from apps.scheduling.models import Appointment, Resource

UNSPECIFIED_PRICE = object()

def validate_responsible(*, business, actor, user):
    if not user or not user.is_active or not (business.owner_id == user.pk or business.members.filter(user=user, is_active=True).exists()):
        raise ValidationError({"responsible_user": "Select an active member of this business."})
    resolve_assignment_member(business=business, user=user, resource=Resources.APPOINTMENTS)
    permission = can(actor, business, Resources.APPOINTMENTS, Actions.CREATE)
    if not permission.allowed:
        raise PermissionDenied("Appointment creation is not allowed.")
    if permission.scope == RolePermission.Scopes.OWN and user.pk != actor.pk:
        raise PermissionDenied("Select yourself as responsible.")
    if permission.scope == RolePermission.Scopes.TEAM and user.pk not in team_user_ids_for(actor, business):
        raise PermissionDenied("Select a member of your team.")


@transaction.atomic
def create_record(*, business, actor, client, service, resource, start_at, branch=None,
                  responsible_user=None, source_conversation=None, notes="",
                  expected_price=UNSPECIFIED_PRICE, expected_duration_minutes=None, lead=None):
    from apps.branches.access import assert_branch_access
    from apps.branches.schedule import appointment_snapshot
    from apps.scheduling.services import handle_appointment_created, validate_appointment_availability

    business = Business.objects.select_for_update().get(pk=business.pk)
    assert_resource_enabled(business, Resources.APPOINTMENTS)
    assert_resource_enabled(business, Resources.CLIENTS)
    if start_at <= timezone.now():
        raise ValidationError({"start_at": "Select a future appointment time."})
    # Reload all submitted references after obtaining the scheduling lock.
    client.refresh_from_db()
    service.refresh_from_db()
    if resource is None:
        raise ValidationError({"resource": "Select an active specialist."})
    resource.refresh_from_db()
    if any(item.business_id != business.pk for item in (client, service, resource)):
        raise ValidationError("All links must belong to this business.")
    if client.is_archived or not service.is_active or service.is_archived:
        raise ValidationError("Select an active client and service.")
    if resource.resource_type != Resource.ResourceTypes.STAFF or not resource.is_active or resource.retired_at:
        raise ValidationError({"resource": "Select an active specialist."})
    assert_can(actor, business, Resources.CLIENTS, Actions.VIEW, obj=client)
    responsible_user = responsible_user or actor
    responsible_user.refresh_from_db()
    validate_responsible(business=business, actor=actor, user=responsible_user)
    source = Appointment.Sources.MANUAL
    if lead:
        lead.refresh_from_db()
        if lead.business_id != business.pk or lead.client_id != client.pk:
            raise ValidationError({"lead": "Lead must match the client and business."})
        assert_can(actor, business, Resources.LEADS, Actions.VIEW, obj=lead)
    if source_conversation:
        assert_resource_enabled(business, Resources.CONVERSATIONS)
        source_conversation = type(source_conversation).objects.select_for_update().get(pk=source_conversation.pk)
        if source_conversation.business_id != business.pk or source_conversation.client_id != client.pk:
            raise ValidationError({"source_conversation": "Conversation and client must match this business."})
        assert_can(actor, business, Resources.CONVERSATIONS, Actions.VIEW, obj=source_conversation)
        assert_can(actor, business, Resources.CONVERSATIONS, Actions.UPDATE, obj=source_conversation)
        lead = source_conversation.lead
        if lead and (lead.business_id != business.pk or lead.client_id != client.pk):
            raise ValidationError("Conversation lead must match the client and business.")
        from apps.conversations.booking import _appointment_source
        source = _appointment_source(source_conversation.channel)
    snapshot = appointment_snapshot(business, service, resource, branch)
    if snapshot["branch"]:
        assert_branch_access(actor, business, snapshot["branch"], active=True)
    candidate = Appointment(business=business, client=client, service=service, resource=resource, **snapshot)
    assert_can(actor, business, Resources.APPOINTMENTS, Actions.CREATE, obj=candidate)
    if ((expected_price is not UNSPECIFIED_PRICE and snapshot["booked_price"] != expected_price)
            or (expected_duration_minutes is not None and snapshot["booked_duration_minutes"] != expected_duration_minutes)):
        from apps.core.domain_errors import InvalidTransition
        raise InvalidTransition("Booking terms changed. Review the current price, duration and slot.",
                                errors={"service": "Refresh the booking terms before submitting again."})
    try:
        end_at = validate_appointment_availability(business, service, start_at, resource=resource, branch=snapshot["branch"])
    except ValueError as exc:
        raise ScheduleConflict(errors={"start_at": "Choose another available time."}) from exc
    appointment = Appointment.objects.create(
        business=business, client=client, service=service, resource=resource,
        responsible_user=responsible_user, source_conversation=source_conversation, lead=lead,
        start_at=start_at, end_at=end_at, source=source, notes=notes, **snapshot,
    )
    metadata = {"conversation_id": source_conversation.pk if source_conversation else None,
                "responsible_user_id": responsible_user.pk}
    write_actor_audit_log(actor=actor, action=AuditLog.Actions.CREATE, instance=appointment, metadata=metadata)
    create_activity_event(business=business, client=client, actor=actor, instance=appointment,
                          event_type=ActivityEvents.APPOINTMENT_CREATED, category="appointment",
                          source="inbox" if source_conversation else "api", text="Appointment created", metadata=metadata)
    handle_appointment_created(appointment)
    return appointment
