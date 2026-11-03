"""Entity-specific side effects for approved staff AI detail commands."""
from django.db import transaction
from rest_framework.exceptions import ValidationError

from apps.activities.services import write_activity_event
from apps.core.audit import write_audit_log
from apps.core.models import AuditLog


@transaction.atomic
def save_details(serializer, *, entity, actor, request):
    creating = serializer.instance is None
    previous_amount = getattr(serializer.instance, "amount", None)
    previous_currency = getattr(serializer.instance, "currency", None)
    assignment_field = {"leads": "responsible_user", "deals": "owner"}.get(entity)
    assignment = None
    assignment_changed = not creating and assignment_field in serializer.validated_data
    if assignment_changed:
        assignment = serializer.validated_data.pop(assignment_field)
        if assignment is None:
            raise ValidationError({assignment_field: "Select an active assignee."})
    if entity == "tasks":
        if creating:
            serializer.validated_data["created_by"] = actor
        elif serializer.instance.status not in {"open", "in_progress"}:
            raise ValidationError("Reopen the task before editing its details.")
    if entity == "appointments" and creating:
        from apps.scheduling.record_commands import create_record
        return create_record(actor=actor, **serializer.validated_data)
    target = serializer.save()
    if assignment_changed:
        if entity == "leads":
            from apps.leads.services import assign_lead
            target = assign_lead(lead=target, actor=actor, user_id=assignment.pk, request=request)
        else:
            from apps.crm.services import assign_deal_owner
            target = assign_deal_owner(deal=target, actor=actor, user_id=assignment.pk, request=request)
    if entity == "deals" and not creating:
        from apps.crm.services import record_deal_value_change
        record_deal_value_change(deal=target, previous_amount=previous_amount, previous_currency=previous_currency, actor=actor, request=request, metadata={"reason": "ai_confirmed_update"})
    # Lead/deal serializers initialize state and creation history in the domain.
    # The command audit still records the exact approved tool call separately.
    if not (creating and entity in {"leads", "deals"}):
        action = AuditLog.Actions.CREATE if creating else AuditLog.Actions.UPDATE
        write_audit_log(request, action, target, metadata={"source": "ai_confirmed"})
        write_activity_event(request, f"{target.__class__.__name__.lower()}.{'created' if creating else 'updated'}", target)
    if creating and entity == "leads":
        from apps.automations.engine import run_automations_for_event
        from apps.automations.models import AutomationRule
        run_automations_for_event(business=target.business, trigger_type=AutomationRule.TriggerTypes.LEAD_CREATED, entity=target,
            payload={"trigger_type": AutomationRule.TriggerTypes.LEAD_CREATED, "lead_id": target.pk})
    if creating and entity == "tasks":
        from apps.tasks.services import create_task_notification
        create_task_notification(target, f"New task: {target.title}")
    return target
