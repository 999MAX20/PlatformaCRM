"""Create a deal with one coherent initial stage, status and history snapshot."""
from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from apps.activities.services import create_activity_event
from apps.activities.taxonomy import ActivityEvents
from apps.businesses.access import Actions, Resources, assert_can
from apps.businesses.capabilities import assert_resource_enabled
from apps.core.audit import write_actor_audit_log, write_audit_log
from apps.core.models import AuditLog
from apps.crm.models import Deal, DealStageHistory
from apps.crm.services import validate_deal_amount, validate_pipeline_links, validate_stage_requirements


def validate_initial_deal_state(*, stage, status=None, lost_reason=""):
    if stage.is_won and stage.is_lost:
        raise ValidationError({"stage": "Stage cannot be both won and lost."})
    initial_status = Deal.Statuses.WON if stage.is_won else Deal.Statuses.LOST if stage.is_lost else Deal.Statuses.OPEN
    if status is not None and status != initial_status:
        raise ValidationError({"status": "Initial status must match the selected stage."})
    reason = (lost_reason or "").strip()
    if initial_status == Deal.Statuses.LOST and not reason:
        raise ValidationError({"lost_reason": "Reason is required when deal is lost."})
    if initial_status != Deal.Statuses.LOST and reason:
        raise ValidationError({"lost_reason": "Loss reason is only allowed for a lost deal."})
    return {"status": initial_status, "lost_reason": reason}


@transaction.atomic
def create_deal(*, business, pipeline, stage, title, actor, client=None, lead=None,
                amount=0, currency="KZT", owner=None, source="", notes="",
                expected_close_at=None, next_action_at=None, status=None,
                lost_reason="", request=None, activity_source="api"):
    state = validate_initial_deal_state(stage=stage, status=status, lost_reason=lost_reason)
    validate_pipeline_links(business=business, pipeline=pipeline, stages={"stage": stage})
    for field, linked in (("client", client), ("lead", lead)):
        if linked and linked.business_id != business.pk:
            raise ValidationError({field: "Related record must belong to the selected business."})
    if owner and (not owner.is_active or (
        owner.pk != business.owner_id and not business.members.filter(user=owner, is_active=True).exists()
    )):
        raise ValidationError({"owner": "Owner must be an active business member."})
    now = timezone.now()
    deal = Deal(business=business, pipeline=pipeline, stage=stage, title=title,
                client=client, lead=lead, amount=validate_deal_amount(amount), currency=currency,
                owner=owner, source=source, notes=notes, expected_close_at=expected_close_at,
                next_action_at=next_action_at, probability=stage.probability, stage_entered_at=now, **state)
    assert_resource_enabled(business, Resources.DEALS)
    assert_can(actor, business, Resources.DEALS, Actions.CREATE, obj=deal)
    validate_stage_requirements(deal=deal, stage=stage, actor=actor, payload={"lost_reason": deal.lost_reason})
    if deal.status == Deal.Statuses.WON:
        deal.won_at = now
    elif deal.status == Deal.Statuses.LOST:
        deal.lost_at = now
        deal.lost_by = actor
    deal.save()
    metadata = {"kind": "initial_lifecycle", "initial_status": deal.status,
                "to_status": deal.status, "to_stage": stage.pk}
    if deal.status == Deal.Statuses.LOST:
        metadata.update(lost_reason=deal.lost_reason, lost_at=deal.lost_at.isoformat())
    if deal.status == Deal.Statuses.WON:
        metadata["won_at"] = deal.won_at.isoformat()
    DealStageHistory.objects.create(business=business, deal=deal, to_stage=stage,
        to_status=deal.status, amount_after=deal.amount, actor=actor, source=activity_source, metadata=metadata)
    create_activity_event(business=business, client=client, actor=actor, instance=deal,
        event_type=ActivityEvents.DEAL_CREATED, source=activity_source, metadata=metadata)
    if request is not None:
        write_audit_log(request, AuditLog.Actions.CREATE, deal, metadata=metadata)
    else:
        write_actor_audit_log(actor=actor, action=AuditLog.Actions.CREATE, instance=deal, metadata=metadata)
    return deal
