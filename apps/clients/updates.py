"""Conditional metadata writes for client editors holding a read snapshot."""
from datetime import timedelta

from django.utils import timezone

from apps.clients.identity import normalize_client_identity
from apps.clients.models import Client
from apps.core.domain_errors import DomainAPIException


class ClientEditConflict(DomainAPIException):
    status_code = 409
    error_code = "client_edit_conflict"
    default_code = error_code
    default_detail = "This client changed. Review the latest values before saving."
    category = "conflict"


def update_client_snapshot(*, client, expected_updated_at, values):
    values = dict(values)
    # QuerySet.update must preserve the identity fields maintained by Client.save.
    identity = normalize_client_identity(
        phone=values.get("phone", client.phone), email=values.get("email", client.email),
    )
    if "phone" in values:
        values["normalized_phone"] = identity["normalized_phone"]
    if "email" in values:
        values["normalized_email"] = identity["normalized_email"]
    values["updated_at"] = max(timezone.now(), client.updated_at + timedelta(microseconds=1))
    changed = Client.objects.filter(
        pk=client.pk, business_id=client.business_id, updated_at=expected_updated_at,
    ).update(**values)
    if not changed:
        raise ClientEditConflict()
    for name, value in values.items():
        setattr(client, name, value)
    return client
