from apps.businesses.models import Business, BusinessCapability
from django.db import transaction
from apps.businesses.profiles import (
    CORE_MODULES, PROFILE_MODULES, profile_spec, profile_module_enabled,
)
from apps.core.domain_errors import InvalidTransition, ModuleDisabled


MODULE_REGISTRY = PROFILE_MODULES

RESOURCE_MODULES = {
    "visit_plans": "visit_plans",
    "plan_payments": "plan_payments",
    "medical_patients": "medical_records",
    "medical_records": "medical_records",
    "medical_documents": "medical_records",
    "medical_prescriptions": "medical_records",
    "medical_files": "medical_records",
    "payments": "clients",
    "conversations": "inbox",
    "leads": "leads",
    "clients": "clients",
    "appointments": "appointments",
    "tasks": "tasks",
    "deals": "deals",
    "analytics": "analytics",
    "ai_assistant": "ai",
    "ai_analyst": "ai",
    "ai_pipeline": "ai",
    "ai_outreach": "ai",
    "ai_automation": "ai",
    "automations": "automations",
    "integrations": "integrations",
}


def default_capabilities(business_type):
    # Business type is descriptive metadata until an owner explicitly enables
    # a future vertical profile. The generic CRM foundation stays intact.
    return {module: True for module in CORE_MODULES}


def ensure_business_capabilities(business, *, configured_by=None):
    current = Business.objects.get(pk=business.pk)
    if profile_spec(current) is not None:
        return business.capabilities.all()
    defaults = default_capabilities(business.business_type)
    existing = {item.module_key: item for item in business.capabilities.all()}
    created = []
    for module_key, is_enabled in defaults.items():
        if module_key not in existing:
            created.append(
                BusinessCapability(
                    business=business,
                    module_key=module_key,
                    is_enabled=is_enabled,
                    configured_by=configured_by,
                )
            )
    if created:
        BusinessCapability.objects.bulk_create(created, ignore_conflicts=True)
    queryset = business.capabilities.all()
    business._capability_map = {item.module_key: item.is_enabled for item in queryset}
    return queryset


@transaction.atomic
def apply_business_type_defaults(business, *, configured_by=None):
    current = Business.objects.select_for_update().get(pk=business.pk)
    if profile_spec(current) is not None:
        raise InvalidTransition()
    defaults = default_capabilities(current.business_type)
    for module_key, is_enabled in defaults.items():
        BusinessCapability.objects.update_or_create(
            business=business,
            module_key=module_key,
            defaults={"is_enabled": is_enabled, "configured_by": configured_by},
        )
    if hasattr(business, "_capability_map"):
        del business._capability_map
    return business.capabilities.all()


def module_for_resource(resource):
    return RESOURCE_MODULES.get(resource)


def is_module_enabled(business, module_key):
    if not module_key:
        return True
    capability_map = getattr(business, "_capability_map", None)
    # Retain the existing per-instance legacy snapshot for ordinary CRM reads.
    # Clinical/profile-managed resources always resolve current database state.
    if module_key in CORE_MODULES and capability_map is not None and profile_spec(business) is None:
        return capability_map.get(module_key, True)
    current = Business.objects.get(pk=business.pk)
    spec = profile_spec(current)
    if spec is not None:
        stored = dict(current.capabilities.values_list("module_key", "is_enabled"))
        return profile_module_enabled(spec, stored, module_key)
    if module_key == "medical_records":
        return False
    if module_key in {"visit_plans", "plan_payments"}:
        return is_module_enabled(business, "clients") and is_module_enabled(business, "appointments")
    if module_key not in CORE_MODULES:
        return False
    capability_map = getattr(business, "_capability_map", None)
    if capability_map is None:
        capability_map = dict(current.capabilities.values_list("module_key", "is_enabled"))
        if set(CORE_MODULES) - capability_map.keys():
            ensure_business_capabilities(business)
            capability_map = business._capability_map
        else:
            business._capability_map = capability_map
    return capability_map.get(module_key, default_capabilities(business.business_type).get(module_key, True))


def resource_is_enabled(business, resource):
    return is_module_enabled(business, module_for_resource(resource))


def assert_resource_enabled(business, resource):
    module_key = module_for_resource(resource)
    if module_key and not is_module_enabled(business, module_key):
        raise ModuleDisabled(errors={"module": module_key})


def capability_payload(business):
    current = Business.objects.get(pk=business.pk)
    spec = profile_spec(current)
    if spec is not None:
        stored = dict(current.capabilities.values_list("module_key", "is_enabled"))
        return {
            "business": current.pk,
            "business_type": current.business_type,
            "workflow_mode": "standard_crm",
            "profile": {"key": spec.key, "version": spec.version,
                        "assigned_at": current.profile_assigned_at.isoformat()},
            "modules": {key: profile_module_enabled(spec, stored, key) for key in MODULE_REGISTRY},
        }
    ensure_business_capabilities(business)
    enabled = business._capability_map
    return {
        "business": business.id,
        "business_type": business.business_type,
        "workflow_mode": "standard_crm",
        "profile": None,
        "modules": {
            **{module: enabled.get(module, True) for module in CORE_MODULES},
            "visit_plans": enabled.get("clients", True) and enabled.get("appointments", True),
            "plan_payments": enabled.get("clients", True) and enabled.get("appointments", True),
            "medical_records": False,
        },
    }
