"""The form's configured default is an assignment, not an unchecked user ID."""
from rest_framework.exceptions import ValidationError

from apps.businesses.access import Resources
from apps.businesses.assignment_policy import assert_assignment_allowed, resolve_assignment_member


FORM_ASSIGNEE_ERROR = "Select an active member of this business."


def validate_form_assignee(*, business, user, actor=None):
    if not user.is_active or not business.members.filter(user=user, user__is_active=True, is_active=True).exists():
        raise ValidationError({"default_responsible_user": [FORM_ASSIGNEE_ERROR]})
    if actor is not None:
        return assert_assignment_allowed(actor=actor, business=business, target_user=user, resource=Resources.LEADS)
    return resolve_assignment_member(business=business, user=user, resource=Resources.LEADS)
