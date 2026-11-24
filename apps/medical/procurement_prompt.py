import uuid
from django.conf import settings
from django.db import models, transaction
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied, ValidationError
from apps.core.domain_errors import InvalidTransition


class MedicalProcurementPrompt(models.Model):
    encounter = models.OneToOneField("medical.MedicalEncounter", on_delete=models.PROTECT)
    token = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    claimed_at = models.DateTimeField(default=timezone.now)
    acknowledged_at = models.DateTimeField(null=True, blank=True)
    decision = models.CharField(max_length=3, blank=True)
    decided_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [models.CheckConstraint(condition=models.Q(decision="", decided_at__isnull=True) |
            models.Q(decision__in=["yes", "no"], decided_at__isnull=False), name="medical_purchase_decision")]


def prompt_context(actor, business_id, encounter_id):
    from .models import MedicalEncounter
    from apps.businesses.models import Business
    from apps.procurement.dental_access import doctor_context
    if not actor or not actor.is_authenticated:
        raise PermissionDenied()
    business = Business.objects.select_for_update().filter(pk=business_id).first()
    encounter = MedicalEncounter.objects.select_related("appointment", "branch").filter(pk=encounter_id,
        business=business, branch__business=business, finalized_by=actor, state="finalized",
        finalized_at__isnull=False, appointment__business=business, appointment__status="completed").first()
    if business is None or encounter is None:
        raise PermissionDenied()
    current, _, _ = doctor_context(actor, business_id, encounter.branch_id)
    return current, encounter


@transaction.atomic
def claim_prompt(*, actor, business_id, encounter_id):
    actor, encounter = prompt_context(actor, business_id, encounter_id)
    if MedicalProcurementPrompt.objects.filter(encounter=encounter).exists():
        return {"show": False}
    event = MedicalProcurementPrompt.objects.create(encounter=encounter, actor=actor)
    return {"show": True, "token": str(event.token), "branch": {"id":encounter.branch_id,"name":encounter.branch.name}}


@transaction.atomic
def record_prompt_decision(*, actor, business_id, token, decision):
    event = MedicalProcurementPrompt.objects.filter(token=token, actor=actor, encounter__business_id=business_id).first()
    if event is None:
        raise PermissionDenied()
    actor, _ = prompt_context(actor, business_id, event.encounter_id)
    event.refresh_from_db()
    if decision not in ("ack", "yes", "no"):
        raise ValidationError({"decision":"Choose a valid prompt action."})
    if decision == "ack":
        if event.acknowledged_at is None:
            event.acknowledged_at = timezone.now()
            event.save(update_fields=["acknowledged_at"])
    else:
        if event.decision and event.decision != decision:
            raise InvalidTransition("This prompt has already been answered.")
        if not event.decision:
            event.decision, event.decided_at = decision, timezone.now()
            event.save(update_fields=["decision", "decided_at"])
    return {"recorded":True}
