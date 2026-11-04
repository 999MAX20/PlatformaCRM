from django.db.models import Q
from rest_framework.exceptions import ValidationError

from apps.accounts.models import User
from apps.businesses.access import Resources
from apps.businesses.assignment_policy import resolve_assignment_member
from apps.core.domain_errors import AssigneeUnavailable


def validate_booking_responsible(business, user):
    if user is None:
        return None
    current = User.objects.filter(pk=user.pk, is_active=True).first()
    if business is None or current is None or not (
        business.owner_id == current.pk or business.members.filter(user=current, is_active=True).exists()
    ):
        raise ValidationError({"ai_booking_responsible_user": "Select an available member of this business."})
    resolve_assignment_member(business=business, user=current, resource=Resources.APPOINTMENTS)
    return current


def booking_responsible_options(business):
    candidates = User.objects.filter(is_active=True).filter(
        Q(pk=business.owner_id) | Q(business_memberships__business=business, business_memberships__is_active=True)
    ).distinct().order_by("full_name", "id")
    result = []
    for user in candidates:
        try:
            validate_booking_responsible(business, user)
        except (ValidationError, AssigneeUnavailable):
            continue
        result.append({"id": user.pk, "label": user.full_name or user.username})
    return result
