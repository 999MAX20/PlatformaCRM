from django.conf import settings
from django.db import transaction
from django.utils import timezone

from apps.core.audit import write_actor_audit_log
from apps.core.domain_errors import InvalidTransition
from apps.core.models import AuditLog
from .models import Business, BusinessCapability
from .profiles import CORE_MODULES, profile_spec


def _changes(business):
    spec = profile_spec(business)
    if business.business_type != Business.BusinessTypes.DENTISTRY:
        raise InvalidTransition("Medical rollout is limited to dentistry businesses.")
    if spec is not None and spec.version == 2:
        return None
    if spec is not None and (spec.key, spec.version) != ("dentistry", 1):
        raise InvalidTransition("This profile cannot be upgraded by the medical rollout.")
    stored = dict(business.capabilities.values_list("module_key", "is_enabled"))
    additions = {key: True for key in CORE_MODULES if key not in stored}
    plans = stored.get("clients", True) and stored.get("appointments", True)
    for key in ("visit_plans", "plan_payments"):
        if key not in stored:
            additions[key] = plans
    if "medical_records" not in stored:
        additions["medical_records"] = True
    return {"additions": additions, "enable_medical": stored.get("medical_records") is False,
            "previous_profile": None if spec is None else {"key": spec.key, "version": spec.version}}


def preview_medical_rollout(*, business_id):
    business = Business.objects.get(pk=business_id)
    changes = _changes(business)
    return {"business_id": business.pk, "status": "planned" if changes is not None else "unchanged"}


@transaction.atomic
def activate_medical_profile(*, business_id):
    """Trusted release operation; never called by merchant requests or read paths."""
    if not settings.DENTAL_MEDICAL_RELEASE_ENABLED:
        raise InvalidTransition("The medical release has not been enabled.")
    business = Business.objects.select_for_update().get(pk=business_id)
    changes = _changes(business)
    if changes is None:
        return {"business_id": business.pk, "status": "unchanged"}
    BusinessCapability.objects.bulk_create([
        BusinessCapability(business=business, module_key=key, is_enabled=value)
        for key, value in changes["additions"].items()
    ])
    if changes["enable_medical"]:
        BusinessCapability.objects.filter(business=business, module_key="medical_records").update(
            is_enabled=True, configured_by=None, updated_at=timezone.now())
    business.profile_key = "dentistry"
    business.profile_version = 2
    business.profile_assigned_at = timezone.now()
    business.save(update_fields=["profile_key", "profile_version", "profile_assigned_at", "updated_at"])
    write_actor_audit_log(actor=None, business=business, action=AuditLog.Actions.UPDATE, instance=business,
        metadata={"kind": "dental_medical_profile_activated", "category": AuditLog.Categories.ACCESS,
                  "risk_level": AuditLog.RiskLevels.HIGH, "previous_profile": changes["previous_profile"],
                  "profile_key": "dentistry", "profile_version": 2,
                  "added_capabilities": sorted(changes["additions"]), "medical_enabled": True})
    return {"business_id": business.pk, "status": "activated"}
