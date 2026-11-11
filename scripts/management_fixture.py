"""Synthetic fixtures for the isolated Management browser gate."""
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.browser_test_runtime import configure_browser_runtime


def prepare():
    fixture_path = Path(os.environ["MANAGEMENT_FIXTURE"])
    configure_browser_runtime()
    import django
    django.setup()
    from apps.accounts.models import User, UserPreference
    from apps.businesses.models import Business, BusinessMember
    from apps.businesses.access import ensure_owner_memberships_for_user
    from apps.branches.models import BranchAccess, BranchService, ScheduleDay, SpecialistBranch
    from apps.branches.single_location import ensure_initial_location
    from apps.scheduling.models import Resource
    from apps.services.models import Service
    result = {}
    for label in ("desktop", "mobile", "kk", "en", "recovery"):
        email = f"management-{label}@example.test"
        user = User.objects.create_user(username=f"management-{label}", email=email,
            password=os.environ["E2E_PASSWORD"], role="business_owner")
        UserPreference.objects.update_or_create(user=user, defaults={"language": label if label in {"kk", "en"} else "ru"})
        business = Business.objects.create(owner=user, name=f"Management {label}", slug=f"management-{label}",
            timezone="Asia/Almaty", address="Example street 12", phone="+77000000000")
        ensure_owner_memberships_for_user(user)
        branch = ensure_initial_location(business)
        staff = Resource.objects.create(business=business, name="Anna", resource_type="staff")
        room = Resource.objects.create(business=business, branch=branch, name="Main room", resource_type="room")
        service = Service.objects.create(business=business, name="Consultation", duration_minutes=30, price_from=12000)
        BranchService.objects.create(business=business, branch=branch, service=service, duration_minutes=30, price_from=12000)
        assignment = SpecialistBranch.objects.create(business=business, branch=branch, resource=staff)
        assignment.services.add(service)
        for resource in (None, staff):
            for weekday in range(7):
                ScheduleDay.objects.update_or_create(branch=branch, resource=resource, weekday=weekday, date=None,
                    defaults={"business": business, "intervals": [{"start": "09:00", "end": "18:00"}]})
        manager_email = f"management-manager-{label}@example.test"
        manager = User.objects.create_user(username=f"management-manager-{label}", email=manager_email, password=os.environ["E2E_PASSWORD"])
        membership = BusinessMember.objects.create(business=business, user=manager, role="manager")
        BranchAccess.objects.update_or_create(member=membership, defaults={"all_branches": True})
        result[label] = {"email": email, "business": business.pk, "branch": branch.pk,
            "staff": staff.pk, "room": room.pk, "service": service.pk, "manager_email": manager_email}
    fixture_path.write_text(json.dumps(result, indent=2), encoding="utf-8")


if __name__ == "__main__":
    prepare()
