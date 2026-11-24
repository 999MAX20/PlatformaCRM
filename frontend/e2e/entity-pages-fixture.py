"""Fresh entities for standalone-page UI checks in the guarded test database."""
import json
import os
import sys
from pathlib import Path
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from scripts.browser_test_runtime import configure_browser_runtime
configure_browser_runtime()
import django
django.setup()
from django.conf import settings
keys = json.loads((Path(settings.DATABASES["default"]["NAME"]).parent / "medical-browser-keys.json").read_text(encoding="ascii"))
settings.MEDICAL_DATA_KEYS = {"browser": keys[0]}
settings.MEDICAL_DATA_ACTIVE_KEY_ID = "browser"
settings.MEDICAL_IDENTITY_INDEX_KEY = keys[1]
from django.contrib.auth import get_user_model
from django.db import transaction
from apps.businesses.models import Business, BusinessMember, BusinessRole, RolePermission
from apps.branches.models import BranchAccess
from apps.medical.models import MedicalRoleAssignment
from apps.clients.models import Client
from apps.scheduling.models import Appointment
from completion_fixture import prepare_completion

with transaction.atomic():
    result = prepare_completion(actual=True)
    if "--primary-head" in sys.argv:
        MedicalRoleAssignment.objects.filter(member__user__email=result["email"]).update(kind="head")
    appointment = Appointment.objects.select_related("business", "client").get(pk=result["appointment_id"])
    suffix = uuid4().hex[:12]
    owner = get_user_model().objects.create_user(username=f"page-owner-{suffix}", email=f"page-owner-{suffix}@example.test",
        password=os.environ["E2E_PASSWORD"], full_name="Synthetic page owner")
    Business.objects.filter(pk=appointment.business_id).update(owner=owner)
    BusinessMember.objects.create(business_id=appointment.business_id, user=owner, role="owner")
    Client.objects.filter(pk=appointment.client_id).update(full_name=f"Анна Тестова {suffix}", notes="Предпочитает утренние приёмы. Синтетические данные.")
    Client.objects.bulk_create([Client(business_id=appointment.business_id, full_name=f"Synthetic list row {suffix}-{index}") for index in range(21)])
    actors = {}
    for kind in ("head", "reception", "assistant"):
        actor = get_user_model().objects.create_user(username=f"page-{kind}-{suffix}", email=f"page-{kind}-{suffix}@example.test",
            password=os.environ["E2E_PASSWORD"], full_name=f"Synthetic {kind}")
        role = BusinessRole.objects.create(business_id=appointment.business_id, name=f"Synthetic {kind}")
        member = BusinessMember.objects.create(business_id=appointment.business_id, user=actor, role="specialist", business_role=role)
        BranchAccess.objects.create(member=member, all_branches=True)
        assignment = MedicalRoleAssignment.objects.create(member=member, business_role=role, kind=kind, granted_by=owner)
        assignment.branches.add(appointment.branch)
        for resource in ("appointments", "clients"):
            RolePermission.objects.create(business_role=role, resource=resource, action="view", scope="all", is_allowed=True)
        RolePermission.objects.create(business_role=role, resource="medical_records", action="view", scope="business" if kind == "head" else "team", is_allowed=True)
        actors[kind + "_email"] = actor.email
    print(json.dumps(result | actors | {"owner_email": owner.email, "client_id": appointment.client_id, "business_id": appointment.business_id}))
