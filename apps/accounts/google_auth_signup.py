"""Shared owner initialization after the caller validates identity and signup data."""
from django.db import transaction
from django.utils.text import slugify
from apps.accounts.models import User
from apps.businesses.models import Business, BusinessMember, BusinessRole
from apps.businesses.access import ensure_default_roles
from apps.businesses.profiles import create_profiled_business, reject_profile_input
from apps.crm.services import ensure_default_pipeline


def unique_business_slug(name):
    base = slugify(name) or "business"
    slug = base
    counter = 2
    while Business.objects.filter(slug=slug).exists():
        slug = f"{base}-{counter}"
        counter += 1
    return slug


@transaction.atomic
def create_owner_account(data):
    reject_profile_input(data)
    email = data["email"].strip().lower()
    user = User.objects.create_user(
        username=email,
        email=email,
        password=data.get("password"),
        full_name=data.get("full_name", "").strip(),
        phone=data.get("phone", "").strip(),
        role=User.Roles.BUSINESS_OWNER,
        is_active=True,
    )
    business = create_profiled_business(
        owner=user,
        name=data["business_name"].strip(),
        slug=unique_business_slug(data["business_name"]),
        business_type=data.get("business_type") or Business.BusinessTypes.OTHER,
        city=data.get("city", "").strip(),
        phone=data.get("phone", "").strip(),
        whatsapp=data.get("phone", "").strip(),
        timezone="Asia/Almaty",
        status=Business.Statuses.TRIAL,
    )
    ensure_default_roles(business)
    from apps.branches.single_location import ensure_initial_location
    ensure_initial_location(business)
    ensure_default_pipeline(business)
    owner_role = BusinessRole.objects.filter(
        business=business,
        preset_key=BusinessMember.Roles.OWNER,
        is_active=True,
    ).first()
    BusinessMember.objects.create(
        business=business,
        user=user,
        role=BusinessMember.Roles.OWNER,
        business_role=owner_role,
        is_active=True,
    )
    return user, business
