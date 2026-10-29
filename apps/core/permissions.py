from django.conf import settings
from django.utils import timezone
from rest_framework.permissions import BasePermission
from apps.core.tenant_ownership import resolve_tenant_business


def is_platform_admin(user):
    return bool(user and user.is_authenticated and (user.is_superuser or user.role == "platform_admin"))


def platform_admin_has_global_access(user):
    return is_platform_admin(user) and not settings.SUPPORT_REQUIRES_GRANT


def can_log_support_action(user, business):
    """Support-note writes always require an explicit, current owner grant."""
    return bool(is_platform_admin(user) and business.support_access_grants.filter(
        user=user, is_active=True, expires_at__gt=timezone.now(),
    ).exists())


def is_platform_user(user):
    return bool(user and user.is_authenticated and getattr(user, "is_platform_user", False))


def accessible_businesses(user):
    from apps.businesses.models import Business
    from apps.core.models import SupportAccessGrant

    if platform_admin_has_global_access(user):
        return Business.objects.all()

    owned_query = Business.objects.filter(owner=user)
    membership_query = Business.objects.filter(members__user=user, members__is_active=True)
    support_query = Business.objects.filter(
        support_access_grants__user=user,
        support_access_grants__is_active=True,
        support_access_grants__expires_at__gt=timezone.now(),
    )
    return (owned_query | membership_query | support_query).distinct()


def user_can_access_business(user, business):
    if platform_admin_has_global_access(user):
        return True
    if not user or not user.is_authenticated or business is None:
        return False
    return (
        business.owner_id == user.id or
        business.members.filter(user=user, is_active=True).exists()
        or business.support_access_grants.filter(user=user, is_active=True, expires_at__gt=timezone.now()).exists()
    )


class IsTenantMember(BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated)

    def has_object_permission(self, request, view, obj):
        business = resolve_tenant_business(obj, business_lookup=getattr(view, "business_lookup", "business"))
        return user_can_access_business(request.user, business)


class IsPlatformUser(BasePermission):
    def has_permission(self, request, view):
        return is_platform_user(request.user)


class IsPlatformAdmin(BasePermission):
    def has_permission(self, request, view):
        return is_platform_admin(request.user)
