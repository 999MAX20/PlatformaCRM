from django.db import transaction

from apps.billing.models import Subscription
from apps.core.audit import write_audit_log
from apps.core.models import AuditLog


@transaction.atomic
def update_subscription_metadata(*, request, subscription, changes):
    subscription = Subscription.objects.select_for_update().select_related("plan").get(pk=subscription.pk)
    changed = {field: value for field, value in changes.items() if getattr(subscription, field) != value}
    if changed:
        for field, value in changed.items():
            setattr(subscription, field, value)
        subscription.save(update_fields=[*changed, "updated_at"])
        # Billing contact and invoice data must not be copied into audit payloads.
        write_audit_log(request, AuditLog.Actions.UPDATE, subscription, metadata={"fields": sorted(changed)})
    return subscription
