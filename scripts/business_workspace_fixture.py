"""Synthetic business workspace fixtures, restricted to the disposable browser runtime."""
import json
import os
from datetime import time
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.browser_test_runtime import configure_browser_runtime


def prepare():
    configure_browser_runtime()
    import django
    django.setup()
    from apps.accounts.models import User, UserPreference
    from apps.businesses.models import Business, BusinessMember
    from apps.businesses.access import ensure_owner_memberships_for_user
    from apps.branches.models import BranchAccess, BranchService, BranchTravelTime, ScheduleDay, SpecialistBranch
    from apps.branches.services import create_branch
    from apps.branches.single_location import ensure_initial_location
    from apps.scheduling.models import Resource, WorkingHours
    from apps.services.models import Service

    result = {}
    for label in ("single", "network", "kk", "en", "recovery"):
        email = f"business-workspace-{label}@example.test"
        user = User.objects.create_user(username=f"business-workspace-{label}", email=email,
            password=os.environ["E2E_PASSWORD"], role="business_owner")
        UserPreference.objects.update_or_create(user=user, defaults={"language": label if label in {"kk", "en"} else "ru"})
        business = Business.objects.create(owner=user, name=f"Workspace {label}", slug=f"workspace-{label}",
            timezone="Asia/Almaty", address="Example street 12", phone="+77000000000")
        ensure_owner_memberships_for_user(user)
        branch = ensure_initial_location(business)
        service = Service.objects.create(business=business, name="Consultation", duration_minutes=30, price_from=12000)
        account = User.objects.create_user(username=f"workspace-account-{label}", email=f"workspace-account-{label}@example.test", password=os.environ["E2E_PASSWORD"])
        member = BusinessMember.objects.create(business=business, user=account, role="operator")
        staff = Resource.objects.create(business=business, name="Anna", linked_user=account, resource_type="staff")
        Resource.objects.create(business=business, name="Max", resource_type="staff")
        room = Resource.objects.create(business=business, branch=branch, name="Main room", resource_type="room")
        for weekday in range(7):
            WorkingHours.objects.create(business=business, weekday=weekday, start_time=time(9), end_time=time(18))
        second = None
        if label != "single":
            second = create_branch(business=business, actor=user, name="North", address="Example street 24")
            BranchService.objects.create(business=business, branch=second, service=service, duration_minutes=45, price_from=20000)
            BranchTravelTime.objects.create(business=business, from_branch=branch, to_branch=second, minutes=30)
            assignment = SpecialistBranch.objects.create(business=business, branch=second, resource=staff)
            assignment.services.add(service)
            for weekday in range(7):
                ScheduleDay.objects.update_or_create(branch=branch, resource=staff, weekday=weekday, date=None, defaults={"business": business, "intervals": [{"start": "09:00", "end": "12:00"}]})
                ScheduleDay.objects.create(business=business, branch=second, weekday=weekday, intervals=[{"start": "09:00", "end": "18:00"}])
                ScheduleDay.objects.create(business=business, branch=second, resource=staff, weekday=weekday, intervals=[{"start": "13:00", "end": "18:00"}])
            Resource.objects.create(business=business, branch=second, name="North room", resource_type="room")
        manager_email = f"workspace-manager-{label}@example.test"
        manager = User.objects.create_user(username=f"workspace-manager-{label}", email=manager_email, password=os.environ["E2E_PASSWORD"])
        manager_member = BusinessMember.objects.create(business=business, user=manager, role="manager")
        BranchAccess.objects.update_or_create(member=manager_member, defaults={"all_branches": True})
        result[label] = {"email": email, "business": business.pk, "branch": branch.pk,
            "second": second.pk if second else None, "staff": staff.pk, "room": room.pk,
            "service": service.pk, "member": member.pk, "manager_email": manager_email}
    output = ROOT / "output/business-implementation-20261111"
    output.mkdir(parents=True, exist_ok=True)
    (output / "browser-fixture.json").write_text(json.dumps(result, indent=2), encoding="utf-8")


if __name__ == "__main__":
    prepare()
