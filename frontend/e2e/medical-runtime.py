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
call_command("migrate", interactive=False, verbosity=0)

from apps.medical.tests_patient_services import PatientCreationTests
from apps.businesses.models import Business, BusinessCapability, RolePermission
from apps.businesses.profiles import PROFILE_MODULES
from apps.clients.models import Client
from apps.medical.models import MedicalRoleAssignment

if not Business.objects.filter(slug="patient-creation").exists():
    fixture = type("BrowserFixture", (), {})
    PatientCreationTests.setUpTestData.__func__(fixture)
    fixture.reception.set_password(os.environ["E2E_PASSWORD"])
    fixture.reception.save(update_fields=["password"])
    fixture.member.role = "admin"
    fixture.member.save(update_fields=["role"])
    for module in PROFILE_MODULES:
        BusinessCapability.objects.update_or_create(business=fixture.business, module_key=module, defaults={"is_enabled": True})
    for action in ("view", "update", "approve"):
        RolePermission.objects.create(business_role=fixture.assignment.business_role, resource="medical_patients", action=action, scope="business")
    for locale in ("ru", "kk", "en"):
        for width in ("desktop", "mobile"):
            Client.objects.create(business=fixture.business, full_name=f"Synthetic {locale} {width}")
    for locale in ("ru", "kk", "en"):
        for width in ("desktop", "mobile"):
            Client.objects.create(business=fixture.business, full_name=f"Representative fixture {locale} {width}")

    Client.objects.create(business=fixture.business, full_name="Representative boundary patient")

business = Business.objects.get(slug="patient-creation")
assignment = MedicalRoleAssignment.objects.get(member__business=business)
if len(sys.argv) > 1 and sys.argv[1] == "revoke":
    from django.utils import timezone
    assignment.revoked_at = timezone.now()
    assignment.save(update_fields=["revoked_at"])
    sys.exit(0)
if len(sys.argv) > 1 and sys.argv[1] == "setup-boundaries":
    from apps.branches.models import Branch, BranchAccess
    assignment.revoked_at = None
    assignment.save(update_fields=["revoked_at"])
    second, _ = Branch.objects.get_or_create(business=business, name="Second synthetic branch")
    assignment.branches.add(second)
    BranchAccess.objects.get(member=assignment.member).branches.add(second)
    Client.objects.filter(pk=2, business=business).update(full_name="Synthetic long name " * 10)
    sys.exit(0)
settings.MEDICAL_IDENTITY_VERIFICATION_POLICIES = {str(business.pk): {
    "reference": "synthetic-browser-v1", "approval_reference": "synthetic-only-not-external-approval",
    "trained_member_ids": [assignment.member_id], "methods": {"synthetic": {
        "required_fields": ["basis"], "optional_fields": [],
        "label": {"ru": "Учебная проверка", "kk": "Оқу тексеруі", "en": "Synthetic check"},
        "field_labels": {"basis": {"ru": "Учебное основание", "kk": "Оқу негіздемесі", "en": "Synthetic basis"}},
    }},
}}
settings.REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"]["auth_login"] = "200/min"
settings.MEDICAL_REPRESENTATIVE_POLICIES = {str(business.pk): {
    **settings.MEDICAL_IDENTITY_VERIFICATION_POLICIES[str(business.pk)],
    "reference": "synthetic-representation-browser-v1", "permissions": ["receive_documents"],
    "requires_expiry": True,
    "permission_labels": {"receive_documents": {"ru": "Получение документов", "kk": "Құжаттарды алу", "en": "Receive documents"}},
}}
call_command("runserver", f"127.0.0.1:{os.environ['E2E_DJANGO_PORT']}", use_reloader=False)
