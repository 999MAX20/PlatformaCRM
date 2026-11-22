from dataclasses import dataclass
from types import MappingProxyType
from django.conf import settings
from django.db import transaction
from django.utils import timezone

from rest_framework.exceptions import ValidationError

from apps.businesses.models import Business, BusinessCapability
from apps.core.domain_errors import DomainAPIException, InvalidTransition


CORE_MODULES = (
    "inbox", "leads", "clients", "appointments", "tasks", "deals",
    "analytics", "ai", "automations", "integrations",
)
PROFILE_MODULES = (*CORE_MODULES, "visit_plans", "plan_payments", "medical_records")
PROFILE_FIELDS = ("profile_key", "profile_version", "profile_assigned_at")
PROFILE_INPUT_KEYS = (*PROFILE_FIELDS, "profile", "modules", "capabilities")


class BusinessProfileInvalid(DomainAPIException):
    status_code = 503
    error_code = "business_profile_invalid"
    default_code = error_code
    default_detail = "The business profile configuration is invalid."
    category = "configuration"


@dataclass(frozen=True)
class ProfileSpec:
    key: str
    version: int
    business_types: frozenset[str]
    modules: frozenset[str]


PROFILE_SPECS = MappingProxyType({
    ("core", 1): ProfileSpec(
        "core", 1,
        frozenset(Business.BusinessTypes.values) - {Business.BusinessTypes.DENTISTRY},
        frozenset(CORE_MODULES),
    ),
    ("dentistry", 1): ProfileSpec(
        "dentistry", 1, frozenset({Business.BusinessTypes.DENTISTRY}),
        frozenset((*CORE_MODULES, "visit_plans", "plan_payments")),
    ),
    ("dentistry", 2): ProfileSpec(
        "dentistry", 2, frozenset({Business.BusinessTypes.DENTISTRY}),
        frozenset(PROFILE_MODULES),
    ),
})

MODULE_DEPENDENCIES = MappingProxyType({
    "visit_plans": frozenset({"clients", "appointments"}),
    "plan_payments": frozenset({"clients", "appointments", "visit_plans"}),
    "medical_records": frozenset({"clients", "appointments"}),
})


def profile_spec(business):
    values = tuple(getattr(business, name) for name in PROFILE_FIELDS)
    if all(value is None for value in values):
        return None
    if any(value is None for value in values):
        raise BusinessProfileInvalid()
    spec = PROFILE_SPECS.get((business.profile_key, business.profile_version))
    if spec is None or business.business_type not in spec.business_types:
        raise BusinessProfileInvalid()
    return spec


def reject_profile_input(data):
    supplied = set(data).intersection(PROFILE_INPUT_KEYS)
    if supplied:
        raise ValidationError({key: "This field is assigned by the server." for key in sorted(supplied)})


def profile_module_enabled(spec, stored, module_key):
    if module_key not in spec.modules or stored.get(module_key) is not True:
        return False
    return all(
        dependency in spec.modules and stored.get(dependency) is True
        for dependency in MODULE_DEPENDENCIES.get(module_key, ())
    )


def profile_for_business_type(business_type):
    if business_type not in Business.BusinessTypes.values:
        raise ValidationError({"business_type": "Select a supported business type."})
    if business_type == "dentistry":
        return PROFILE_SPECS[("dentistry", 2 if settings.DENTAL_MEDICAL_RELEASE_ENABLED else 1)]
    return PROFILE_SPECS[("core", 1)]


@transaction.atomic
def initialize_business_profile(business, *, actor):
    from apps.core.audit import write_actor_audit_log
    from apps.core.models import AuditLog

    if not business._state.adding or business.pk is not None:
        current = Business.objects.select_for_update().get(pk=business.pk)
        spec = profile_spec(current)
        if spec is None:
            raise InvalidTransition(errors={"profile": "Existing businesses require an explicit migration."})
        expected = {key: key in spec.modules for key in PROFILE_MODULES}
        if dict(current.capabilities.values_list("module_key", "is_enabled")) != expected:
            raise BusinessProfileInvalid()
        return current

    if any(getattr(business, key) is not None for key in PROFILE_FIELDS):
        raise ValidationError({"profile": "The profile is assigned by the server."})
    spec = profile_for_business_type(business.business_type)
    business.profile_key = spec.key
    business.profile_version = spec.version
    business.profile_assigned_at = timezone.now()
    business.save(force_insert=True)
    BusinessCapability.objects.bulk_create([
        BusinessCapability(business=business, module_key=key, is_enabled=key in spec.modules,
                           configured_by=actor)
        for key in PROFILE_MODULES
    ])
    write_actor_audit_log(
        actor=actor, action=AuditLog.Actions.CREATE, instance=business, business=business,
        metadata={"kind": "business_profile_assigned", "profile_key": spec.key,
                  "profile_version": spec.version},
    )
    return business


def create_profiled_business(*, owner, actor=None, **attributes):
    reject_profile_input(attributes)
    return initialize_business_profile(Business(owner=owner, **attributes), actor=actor or owner)


def assert_business_type_change_allowed(business, business_type):
    if profile_spec(business) is not None and business_type != business.business_type:
        raise InvalidTransition(errors={"business_type": "The assigned business profile is fixed."})


@transaction.atomic
def update_business_capability(*, capability, actor, is_enabled):
    from apps.businesses.access import Actions, Resources, assert_can
    from apps.core.audit import write_actor_audit_log
    from apps.core.models import AuditLog

    business = Business.objects.select_for_update().get(pk=capability.business_id)
    assert_can(actor, business, Resources.SETTINGS, Actions.UPDATE)
    current = BusinessCapability.objects.select_for_update().get(pk=capability.pk, business=business)
    spec = profile_spec(business)
    if current.module_key not in CORE_MODULES and spec is None:
        raise InvalidTransition()
    if is_enabled is not None and type(is_enabled) is not bool:
        raise ValidationError({"is_enabled": "Expected a boolean."})
    if is_enabled is None or current.is_enabled == is_enabled:
        return current
    if spec is not None:
        raise InvalidTransition(errors={"is_enabled": "The assigned business profile is fixed."})
    current.is_enabled = is_enabled
    current.configured_by = actor
    current.save(update_fields=["is_enabled", "configured_by", "updated_at"])
    write_actor_audit_log(
        actor=actor, action=AuditLog.Actions.UPDATE, instance=current, business=business,
        metadata={"kind": "business_capability", "module_key": current.module_key,
                  "is_enabled": current.is_enabled},
    )
    cached_business = capability._state.fields_cache.get("business")
    if cached_business is not None and hasattr(cached_business, "_capability_map"):
        del cached_business._capability_map
    return current
