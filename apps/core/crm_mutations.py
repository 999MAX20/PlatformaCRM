"""Keep CRM commands, their history and follow-on effects in one transaction."""
from functools import wraps

from django.db import transaction

from apps.businesses.access import Actions, assert_can
from apps.businesses.models import Business
from apps.core.domain_errors import InvalidTransition


class LockedCRMUpdateMixin:
    """Generic edits must not save a stale snapshot over a lifecycle command."""

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        with transaction.atomic():
            Business.objects.select_for_update().get(pk=instance.business_id)
            instance.__class__.objects.select_for_update().only("pk").get(pk=instance.pk)
            # DRF loads/authorizes the instance again inside this lock, then
            # validates, saves and records the ordinary update's effects.
            return super().update(request, *args, **kwargs)


def locked_crm_change(argument, *, resource=None, action=Actions.UPDATE):
    """Reload before validation; use the same Business-first lock as scheduling.

    Callers supply the existing endpoint permission, when applicable. Internal
    domain transitions reuse their outer command's authorization.
    """
    def decorate(operation):
        @wraps(operation)
        def change(**kwargs):
            original = kwargs[argument]
            with transaction.atomic():
                Business.objects.select_for_update().get(pk=original.business_id)
                current = original.__class__.objects.select_for_update().get(
                    pk=original.pk, business_id=original.business_id,
                )
                request = kwargs.get("request")
                if request is not None and resource is not None:
                    assert_can(request.user, current.business, resource, action, obj=current)
                if current.is_archived:
                    raise InvalidTransition(errors={argument: "Restore the archived record before changing it."})
                result = operation(**{**kwargs, argument: current})
                # Several callers retain the model passed to the service.
                original.refresh_from_db()
                return result
        return change
    return decorate
