from django.contrib.auth import get_user_model
from django.db.models import Q
from django.shortcuts import get_object_or_404
from rest_framework.exceptions import PermissionDenied

from apps.businesses.models import Business, BusinessMember
from apps.support.models import SupportCase


PLATFORM_ROLES = ("platform_admin", "platform_manager")


def active_platform_users():
    return get_user_model().objects.filter(is_active=True).filter(
        Q(role__in=PLATFORM_ROLES) | Q(is_superuser=True)
    )


def assert_active_actor(actor):
    if not actor or not actor.is_authenticated or not get_user_model().objects.filter(pk=actor.pk, is_active=True).exists():
        raise PermissionDenied("An active account is required.")


def assert_platform_actor(actor):
    assert_active_actor(actor)
    if not active_platform_users().filter(pk=actor.pk).exists():
        raise PermissionDenied("Platform support access is required.")


def clinic_businesses(actor):
    assert_active_actor(actor)
    # A support grant or global platform role never substitutes for membership.
    membership_ids = BusinessMember.objects.filter(user_id=actor.pk, is_active=True).values("business_id")
    return Business.objects.filter(Q(owner_id=actor.pk) | Q(pk__in=membership_ids))


def get_case_business(actor, business_id, *, platform=False):
    if platform:
        assert_platform_actor(actor)
        return get_object_or_404(Business, pk=business_id)
    return get_object_or_404(clinic_businesses(actor), pk=business_id)


def scoped_cases(actor, *, platform=False):
    if platform:
        assert_platform_actor(actor)
        return SupportCase.objects.all()
    businesses = clinic_businesses(actor)
    admin_ids = BusinessMember.objects.filter(
        user_id=actor.pk, is_active=True, role__in=[BusinessMember.Roles.OWNER, BusinessMember.Roles.ADMIN],
    ).values("business_id")
    return SupportCase.objects.filter(business__in=businesses).filter(
        Q(created_by_id=actor.pk) | Q(requester_id=actor.pk)
        | Q(business__owner_id=actor.pk) | Q(business_id__in=admin_ids)
    )


def get_case(actor, case_id, *, platform=False, lock=False):
    cases = scoped_cases(actor, platform=platform)
    if lock:
        cases = cases.select_for_update()
    return get_object_or_404(cases, pk=case_id)
