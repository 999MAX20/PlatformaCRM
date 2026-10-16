"""Shared lock boundary for membership writes and ownership transfer."""
from rest_framework.exceptions import ValidationError

from apps.businesses.models import Business, BusinessMember


def lock_member(member):
    business = Business.objects.select_for_update().get(pk=member.business_id)
    member = BusinessMember.objects.select_for_update().get(pk=member.pk)
    member.business = business
    return member


def assert_member_deletable(member):
    if member.user_id == member.business.owner_id:
        raise ValidationError("The current owner's membership cannot be deleted.")
