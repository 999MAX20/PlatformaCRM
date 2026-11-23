from rest_framework.exceptions import PermissionDenied, ValidationError

from apps.branches.access import assert_all_branch_access
from apps.businesses.access import Actions, Resources, assert_can, scope_queryset
from apps.integrations import google_oauth
from apps.scheduling.models import Appointment, Resource


def assert_connection(connection, actor):
    if not actor.is_active:
        raise PermissionDenied("This account is inactive.")
    google_oauth.assert_access(actor, connection.business)
    if connection.provider != "google_calendar":
        raise ValidationError("Select a Google Calendar connection.")
    # A specialist's busy time applies across all branches, not only the current one.
    assert_all_branch_access(actor, connection.business)
    assert_can(actor, connection.business, Resources.APPOINTMENTS, Actions.VIEW)
    assert_can(actor, connection.business, Resources.CLIENTS, Actions.VIEW)


def specialist(connection, actor, resource_id):
    assert_connection(connection, actor)
    resource = Resource.objects.filter(pk=resource_id, business=connection.business,
        resource_type=Resource.ResourceTypes.STAFF, is_active=True, retired_at__isnull=True).first()
    if resource is None:
        raise ValidationError("Select an active specialist of this business.")
    return resource


def appointments(connection):
    return scope_queryset(Appointment.objects.filter(business=connection.business),
        connection.actor, connection.business, Resources.APPOINTMENTS, Actions.VIEW)
