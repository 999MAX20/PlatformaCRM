from django.db import transaction

from apps.activities.services import write_activity_event
from apps.core.archive import archive_instance, restore_instance
from apps.core.audit import write_audit_log
from apps.core.domain_errors import InvalidTransition
from apps.core.models import AuditLog


@transaction.atomic
def upsert_catalog_service(*, business, payload, actor):
    """Catalog ingestion has the same authority as normal Service metadata writes."""
    from apps.businesses.access import Actions, Resources, assert_can
    from apps.businesses.capabilities import assert_resource_enabled
    from apps.services.models import Service

    # Authorize the actual object (or a new candidate), so shared branch and
    # object-scope rules cannot be skipped by integration-level admission.
    service = Service.objects.select_for_update().filter(business=business, name=payload["name"]).first()
    candidate = service or Service(business=business, name=payload["name"])
    assert_resource_enabled(business, Resources.SETTINGS)
    assert_can(actor, business, Resources.SETTINGS, Actions.UPDATE, obj=candidate)
    # Existing inactive/archive flags are intentional lifecycle state. Importing
    # metadata must not activate or restore a service; use explicit actions.
    return Service.objects.update_or_create(
        business=business,
        name=payload["name"],
        defaults={
            "description": payload.get("description", ""),
            "duration_minutes": payload.get("duration_minutes") or 30,
            "price_from": payload.get("price_from"),
        },
    )


@transaction.atomic
def set_service_active(*, request, service, is_active):
    from apps.businesses.models import Business
    Business.objects.select_for_update().get(pk=service.business_id)
    service.refresh_from_db()
    if not is_active:
        from apps.branches.management_lifecycle import assert_no_future
        assert_no_future(service)
    if service.is_archived:
        raise InvalidTransition("Restore the service before changing its status.")
    if service.is_active == is_active:
        return service

    previous = service.is_active
    service.is_active = is_active
    service.save(update_fields=["is_active", "updated_at"])
    event_type = "service_activated" if is_active else "service_deactivated"
    metadata = {
        "kind": "lifecycle",
        "event_type": event_type,
        "from_active": previous,
        "to_active": is_active,
    }
    write_audit_log(request, AuditLog.Actions.UPDATE, service, metadata=metadata)
    write_activity_event(
        request,
        event_type,
        service,
        text="Service activated" if is_active else "Service deactivated",
        metadata=metadata,
    )
    return service


@transaction.atomic
def archive_service(*, request, service, reason=""):
    from apps.businesses.models import Business
    Business.objects.select_for_update().get(pk=service.business_id)
    service.refresh_from_db()
    from apps.branches.management_lifecycle import assert_no_future
    assert_no_future(service)
    if service.is_archived:
        return service
    if service.is_active:
        service.is_active = False
        service.save(update_fields=["is_active", "updated_at"])
    return archive_instance(request, service, reason=reason)


@transaction.atomic
def restore_service(*, request, service):
    service = restore_instance(request, service)
    if service.is_active:
        service.is_active = False
        service.save(update_fields=["is_active", "updated_at"])
    return service
