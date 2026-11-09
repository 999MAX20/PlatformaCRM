"""Synthetic CRM fixture, restricted to an explicitly disposable benchmark DB."""
from datetime import datetime, timedelta, timezone
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def main():
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
    from django.conf import settings
    database = settings.DATABASES["default"]
    if (os.environ.get("CRM_LOAD_DISPOSABLE") != "1" or database["HOST"] != "127.0.0.1"
            or database["NAME"] not in {"crm_bench_small", "crm_bench_large"}):
        raise RuntimeError("Benchmark fixture requires its disposable database")
    import django
    django.setup()
    from django.db import connection
    from apps.accounts.models import User
    from apps.accounts.device_sessions import attach_device_session
    from apps.businesses.models import Business, BusinessMember
    from apps.businesses.access import ensure_default_roles
    from apps.businesses.capabilities import ensure_business_capabilities
    from apps.clients.models import Client
    from apps.crm.models import Deal
    from apps.crm.services import ensure_default_pipeline
    from apps.scheduling.models import Appointment, Resource
    from apps.services.models import Service
    from apps.tasks.models import Task
    from apps.branches.single_location import ensure_initial_location
    from rest_framework_simplejwt.tokens import RefreshToken

    size = int(sys.argv[1])
    output = Path(sys.argv[2])
    subjects = []
    base = datetime(2026, 10, 15, 9, tzinfo=timezone.utc)
    for tenant in range(10):
        owner = User.objects.create_user(username=f"load-owner-{tenant}", email=f"load-owner-{tenant}@example.test", role="business_owner")
        business = Business.objects.create(owner=owner, name=f"Load business {tenant}", slug=f"load-business-{tenant}", timezone="UTC")
        ensure_default_roles(business)
        ensure_business_capabilities(business)
        branch = ensure_initial_location(business)
        role = business.roles.get(preset_key="admin")
        pipeline = ensure_default_pipeline(business)
        stage = pipeline.stages.order_by("order").first()
        service = Service.objects.create(business=business, name="Load service", duration_minutes=30, price_from=10000)
        resources = Resource.objects.bulk_create([Resource(business=business, name=f"Load specialist {i}") for i in range(10)])
        clients = Client.objects.bulk_create([Client(business=business, full_name=f"Load client {tenant} {i:05}",
            email=f"load-{tenant}-{i}@example.test", normalized_email=f"load-{tenant}-{i}@example.test") for i in range(size)], batch_size=1000)
        count = max(10, size // 2)
        visits = []
        for i in range(count):
            start = base + timedelta(days=i // 160, minutes=(i % 16) * 30)
            visits.append(Appointment(business=business, branch=branch, client=clients[i % size], service=service,
                resource=resources[(i // 16) % 10], start_at=start, end_at=start + timedelta(minutes=30),
                status="confirmed", booked_price=10000, booked_duration_minutes=30, branch_name=branch.name))
        Appointment.objects.bulk_create(visits, batch_size=1000)
        Deal.objects.bulk_create([Deal(business=business, client=clients[i % size], pipeline=pipeline, stage=stage,
            title=f"Load deal {i}", amount=10000, owner=owner) for i in range(count)], batch_size=1000)
        Task.objects.bulk_create([Task(business=business, client=clients[i % size], title=f"Load task {i}", created_by=owner,
            assignee=owner, due_at=base + timedelta(days=i % 30)) for i in range(max(10, size // 5))], batch_size=1000)
        for index in range(32):
            user = User.objects.create_user(username=f"load-user-{tenant}-{index}", email=f"load-user-{tenant}-{index}@example.test", role="business_manager")
            BusinessMember.objects.create(business=business, user=user, role="admin", business_role=role)
            refresh = RefreshToken.for_user(user)
            refresh["auth_epoch"] = user.auth_epoch
            attach_device_session(user, refresh)
            token = refresh.access_token
            token.set_exp(lifetime=timedelta(hours=4))
            subjects.append({"business": business.pk, "user": user.pk, "client": clients[index % size].pk, "token": str(token)})
    # Interleave tenants so even a small user stage exercises multiple businesses.
    subjects = [subjects[tenant * 32 + index] for index in range(32) for tenant in range(10)]
    with connection.cursor() as cursor:
        cursor.execute("ANALYZE")
    counts = {m._meta.label: m.objects.count() for m in (Business, User, Client, Appointment, Deal, Task)}
    output.write_text(json.dumps({"disposable": True, "database": database["NAME"], "subjects": subjects, "counts": counts}), encoding="utf-8")
    print(json.dumps({"database": database["NAME"], "counts": counts}))


if __name__ == "__main__":
    main()
