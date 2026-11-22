"""Synthetic medical browser fixture; refuses every non-disposable database."""
import base64
import json
import os
from pathlib import Path
import secrets
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from scripts.browser_test_runtime import configure_browser_runtime

participation_fixture = os.environ.get("E2E_PARTICIPATION") == "1"
proposal_fixture = os.environ.get("E2E_PROPOSAL") == "1"
configure_browser_runtime()
import django
django.setup()
from django.conf import settings
from django.core.management import call_command

directory = Path(settings.DATABASES["default"]["NAME"]).parent
key_file = directory / "medical-browser-keys.json"
if not key_file.exists():
    key_file.write_text(json.dumps([base64.urlsafe_b64encode(secrets.token_bytes(32)).decode("ascii") for _ in range(2)]), encoding="ascii")
keys = json.loads(key_file.read_text(encoding="ascii"))
settings.MEDICAL_DATA_KEYS = {"browser": keys[0]}
settings.MEDICAL_DATA_ACTIVE_KEY_ID = "browser"
settings.MEDICAL_IDENTITY_INDEX_KEY = keys[1]
settings.MEDICAL_TOOTH_SURFACE_POLICIES = {"1": {
    "reference": "synthetic-browser-v1", "approval_reference": "synthetic-test-only",
    "teeth": {"11": ["a", "b", "constructor"]},
    "labels": {code: {lang: f"Synthetic {code.upper()} {lang.upper()}" for lang in ("ru", "kk", "en")} for code in ("a", "b", "constructor")},
}}
call_command("migrate", interactive=False, verbosity=0)

from datetime import timedelta
from django.utils import timezone
from apps.medical.tests_encounter_open import OpenPrimaryEncounterTests
from apps.businesses.models import Business, BusinessCapability
from apps.businesses.profiles import PROFILE_MODULES
from apps.clients.models import Client
from apps.medical.models import PatientProfile
from apps.scheduling.models import Appointment

if not Business.objects.filter(slug="medical-role").exists():
    fixture = type("ClinicalBrowserFixture", (), {})
    OpenPrimaryEncounterTests.setUpTestData.__func__(fixture)
    fixture.doctor.set_password(os.environ["E2E_PASSWORD"])
    fixture.doctor.full_name = "Synthetic clinician"
    fixture.doctor.save(update_fields=["password", "full_name"])
    fixture.member.role = "admin"
    fixture.member.save(update_fields=["role"])
    fixture.record.delete()
    for module in PROFILE_MODULES:
        BusinessCapability.objects.update_or_create(business=fixture.business, module_key=module, defaults={"is_enabled": True})
    for index in range(2, 15):
        client = Client.objects.create(business=fixture.business, full_name=f"Synthetic clinical patient {index}")
        PatientProfile.objects.create(business=fixture.business, client=client, created_by=fixture.owner,
            identity_status="verified", verified_at=timezone.now(), verified_by=fixture.owner,
            verification_evidence_encrypted="synthetic-fixture-only")
        Appointment.objects.create(business=fixture.business, client=client, service=fixture.service,
            resource=fixture.staff, branch=fixture.first,
            start_at=fixture.appointment.start_at + timedelta(days=index),
            end_at=fixture.appointment.end_at + timedelta(days=index))
if participation_fixture:
    from django.contrib.auth import get_user_model
    from apps.branches.models import BranchAccess
    from apps.businesses.models import BusinessMember, RolePermission
    from apps.medical.models import MedicalRoleAssignment
    business = Business.objects.get(slug="medical-role")
    doctor_assignment = MedicalRoleAssignment.objects.get(member__user__email="medical-role-doctor@example.test")
    for action in ("view", "create", "approve", "manage"):
        RolePermission.objects.get_or_create(business_role=doctor_assignment.business_role,
            resource="medical_participation", action=action, defaults={"scope": "business", "is_allowed": True})
    RolePermission.objects.get_or_create(business_role=doctor_assignment.business_role,
        resource="medical_patients", action="view", defaults={"scope": "business", "is_allowed": True})
    head, created = get_user_model().objects.get_or_create(username="medical-participation-head",
        defaults={"email": "medical-participation-head@example.test", "full_name": "Synthetic medical head"})
    if created:
        head.set_password(os.environ["E2E_PASSWORD"])
        head.save(update_fields=["password"])
        member = BusinessMember.objects.create(business=business, user=head, role="admin")
        BranchAccess.objects.create(member=member, all_branches=True)
        assignment = MedicalRoleAssignment.objects.create(member=member, business_role=doctor_assignment.business_role,
            kind="head", granted_by=business.owner)
        assignment.branches.set(doctor_assignment.branches.all())
if proposal_fixture:
    from django.contrib.auth import get_user_model
    from apps.branches.models import Branch, BranchAccess
    from apps.businesses.models import BusinessMember
    from apps.medical.models import MedicalRoleAssignment
    business = Business.objects.get(slug="medical-role")
    source = MedicalRoleAssignment.objects.get(member__user__email="medical-role-doctor@example.test")
    recipient, created = get_user_model().objects.get_or_create(username="medical-transfer-recipient",
        defaults={"email": "medical-transfer-recipient@example.test", "full_name": "Synthetic second-branch clinician"})
    if created:
        recipient.set_password(os.environ["E2E_PASSWORD"])
        recipient.save(update_fields=["password"])
        member = BusinessMember.objects.create(business=business, user=recipient, role="admin")
        branch = Branch.objects.get(business=business, name="Second")
        grant = BranchAccess.objects.create(member=member, all_branches=False)
        grant.branches.add(branch)
        assignment = MedicalRoleAssignment.objects.create(member=member, business_role=source.business_role,
            kind="doctor", granted_by=business.owner)
        assignment.branches.add(branch)
settings.REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"]["auth_login"] = "200/min"
if len(sys.argv) > 1 and sys.argv[1] in ("revoke", "restore"):
    from apps.medical.models import MedicalRoleAssignment
    MedicalRoleAssignment.objects.filter(member__business__slug="medical-role").update(revoked_at=timezone.now() if sys.argv[1] == "revoke" else None)
    sys.exit(0)
call_command("runserver", f"127.0.0.1:{os.environ['E2E_DJANGO_PORT']}", use_reloader=False, use_threading=False)
