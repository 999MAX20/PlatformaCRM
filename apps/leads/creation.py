"""Initial lead state is a creation snapshot, not a synthetic status transition."""
from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from apps.activities.services import create_activity_event
from apps.activities.taxonomy import ActivityEvents
from apps.businesses.access import Actions, Resources, assert_can
from apps.businesses.capabilities import assert_resource_enabled
from apps.core.audit import write_actor_audit_log, write_audit_log
from apps.core.models import AuditLog
from apps.leads.models import Lead


def validate_initial_lead_state(*, status=Lead.Statuses.NEW, lost_reason=""):
    if status not in Lead.Statuses.values:
        raise ValidationError({"status": "Invalid lead status."})
    reason = (lost_reason or "").strip()
    if status == Lead.Statuses.LOST and not reason:
        raise ValidationError({"lost_reason": "Reason is required when lead is lost."})
    if status != Lead.Statuses.LOST and reason:
        raise ValidationError({"lost_reason": "Loss reason is only allowed for a lost lead."})
    return {"status": status, "lost_reason": reason}


@transaction.atomic
def create_lead(*, business, client, actor, service=None, source=Lead.Sources.MANUAL,
                message="", status=Lead.Statuses.NEW, lost_reason="",
                responsible_user=None, request=None, activity_source="api"):
    state = validate_initial_lead_state(status=status, lost_reason=lost_reason)
    if client.business_id != business.pk:
        raise ValidationError({"client": "Client must belong to the selected business."})
    if service and service.business_id != business.pk:
        raise ValidationError({"service": "Service must belong to the selected business."})
    if responsible_user and (not responsible_user.is_active or (
        responsible_user.pk != business.owner_id
        and not business.members.filter(user=responsible_user, is_active=True).exists()
    )):
        raise ValidationError({"responsible_user": "Responsible user must be an active business member."})
    lead = Lead(business=business, client=client, service=service, source=source,
                message=message, responsible_user=responsible_user, **state)
    assert_resource_enabled(business, Resources.LEADS)
    assert_can(actor, business, Resources.LEADS, Actions.CREATE, obj=lead)
    if status == Lead.Statuses.LOST:
        lead.lost_at = timezone.now()
        lead.lost_by = actor
    lead.save()
    metadata = {"kind": "initial_lifecycle", "initial_status": lead.status, "to_status": lead.status}
    if lead.status == Lead.Statuses.LOST:
        metadata.update(lost_reason=lead.lost_reason, lost_at=lead.lost_at.isoformat())
    create_activity_event(business=business, client=client, actor=actor, instance=lead,
                          event_type=ActivityEvents.LEAD_CREATED, source=activity_source, metadata=metadata)
    if request is not None:
        write_audit_log(request, AuditLog.Actions.CREATE, lead, metadata=metadata)
    else:
        write_actor_audit_log(actor=actor, action=AuditLog.Actions.CREATE, instance=lead, metadata=metadata)
    return lead
