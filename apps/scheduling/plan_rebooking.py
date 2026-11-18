"""Rebook cancelled time without discarding its record or changing agreed prices."""
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from apps.core.domain_errors import InvalidTransition
from apps.payments.models import PlanTerms
from apps.payments.plan_balances import composition, current_terms


def rebook_step(plan, actor, data):
    if data.get("consent") is not True or not str(data.get("reason", "")).strip():
        raise ValidationError({"consent": "Confirm the replacement and provide a reason."})
    step = plan.steps.select_related("appointment").filter(pk=data.get("step_id"), removed_at__isnull=True).first()
    if not step or not step.appointment_id or step.appointment.status not in {"cancelled", "no_show"} or hasattr(step, "rebooked_as"):
        raise InvalidTransition("Select a cancelled or missed visit without a replacement.")
    terms = current_terms(plan)
    if terms and terms.composition != composition(plan):
        raise InvalidTransition("Accept current plan prices before rebooking.")
    from apps.scheduling.plan_services import _validate_step
    replacement = _validate_step(plan, actor, {name: getattr(step, name)
        for name in ("service", "resource", "branch", "responsible_user")})
    replacement.rebooked_from = step
    replacement.position = plan.steps.order_by("-position").first().position + 1
    replacement.save()
    step.removed_at = timezone.now()
    step.save(update_fields=["removed_at", "updated_at"])
    if terms:
        PlanTerms.objects.create(plan=plan, revision=plan.revision + 1, previous=terms,
            mode=terms.mode, currency=terms.currency, total=terms.total,
            lines=[{**line, "step": replacement.pk if line["step"] == step.pk else line["step"]} for line in terms.lines],
            composition=composition(plan), reason=data["reason"].strip(), consent=True, actor=actor)


def replaces_appointment(step, appointment_id):
    previous = step.rebooked_from
    while previous:
        if previous.appointment_id == appointment_id:
            return True
        previous = previous.rebooked_from
    return False
