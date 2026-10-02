"""Explicit CRM lifecycle actions; no provider-supplied function dispatch."""
from rest_framework import serializers
from rest_framework.exceptions import ValidationError

TRANSITIONS = {
    "leads": ("start", "contact", "close", "lose", "reopen", "assign"),
    "deals": ("stage", "win", "lose", "reopen", "assign"),
    "tasks": ("start", "complete", "cancel", "reopen", "assign"),
    "appointments": ("confirm", "complete", "cancel", "no_show", "reschedule"),
}


def validate_transition(payload):
    entity, action = payload.get("entity"), payload.get("action")
    if action not in TRANSITIONS.get(entity, ()):
        raise ValidationError({"action": "Unsupported lifecycle action."})
    values = payload.get("values", {})
    allowed = {"assign": {"user_id"}, "stage": {"stage_id"}, "reschedule": {"start_at", "resource", "reason"}}.get(action, set())
    if not isinstance(values, dict) or set(values) - allowed:
        raise ValidationError({"values": "Unsupported lifecycle arguments."})
    if action in {"lose", "cancel", "no_show"} and len(str(payload.get("reason", "")).strip()) < 3:
        raise ValidationError({"reason": "A reason of at least three characters is required."})
    for field in ("user_id", "stage_id"):
        if field in allowed and (type(values.get(field)) is not int or values[field] <= 0):
            raise ValidationError({field: "Select an available record."})
    if action == "reschedule":
        serializers.DateTimeField().run_validation(values.get("start_at"))


def execute_transition(target, payload, actor, request):
    validate_transition(payload)
    entity, action = payload["entity"], payload["action"]
    values, reason = payload.get("values", {}), payload.get("reason", "")
    if entity == "leads":
        from apps.leads import services
        functions = {"start": services.take_lead_in_work, "contact": services.mark_lead_contacted,
            "close": services.mark_lead_closed, "lose": services.mark_lead_lost, "reopen": services.reopen_lead, "assign": services.assign_lead}
        kwargs = {"lost_reason": reason} if action == "lose" else {"user_id": values["user_id"]} if action == "assign" else {}
        return functions[action](lead=target, actor=actor, request=request, **kwargs)
    if entity == "deals":
        from apps.crm import services
        from apps.crm.models import PipelineStage
        if action == "stage":
            stage = PipelineStage.objects.filter(pk=values["stage_id"], business=target.business, pipeline=target.pipeline, is_active=True).first()
            if stage is None:
                raise ValidationError("Stage is not available in this pipeline.")
            return services.move_deal_stage(deal=target, stage=stage, actor=actor, request=request, payload={"lost_reason": reason})
        functions = {"win": services.mark_deal_won, "lose": services.mark_deal_lost, "reopen": services.reopen_deal, "assign": services.assign_deal_owner}
        kwargs = {"lost_reason": reason} if action == "lose" else {"user_id": values["user_id"]} if action == "assign" else {}
        return functions[action](deal=target, actor=actor, request=request, **kwargs)
    if entity == "tasks":
        from apps.tasks import services
        functions = {"start": services.start_task, "complete": services.complete_task, "cancel": services.cancel_task,
            "reopen": services.reopen_task, "assign": services.assign_task}
        kwargs = {"reason": reason} if action == "cancel" else {"user_id": values["user_id"]} if action == "assign" else {}
        return functions[action](task=target, actor=actor, request=request, **kwargs)
    from apps.scheduling import services
    if action == "reschedule":
        from apps.scheduling.serializers import AppointmentRescheduleSerializer
        serializer = AppointmentRescheduleSerializer(data=values, context={"appointment": target})
        serializer.is_valid(raise_exception=True)
        return services.reschedule_appointment(appointment=target, actor=actor, request=request, **serializer.validated_data)
    if action == "confirm":
        return services.confirm_appointment(appointment=target, actor=actor)
    functions = {"complete": services.complete_appointment, "cancel": services.cancel_appointment, "no_show": services.mark_appointment_no_show}
    kwargs = {"reason": reason} if action in {"cancel", "no_show"} else {}
    return functions[action](appointment=target, actor=actor, request=request, **kwargs)
