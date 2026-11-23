"""Synthetic correction access browser fixture, confined to a disposable database."""
import base64
import json
import os
from pathlib import Path
import secrets
import sys
from threading import Lock

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from scripts.browser_test_runtime import configure_browser_runtime
plan_links_fixture = os.environ.get("E2E_MEDICAL_PLAN_LINKS") == "1"
configure_browser_runtime()
import django
django.setup()
from django.conf import settings
from django.core.management import call_command


class SerialMedicalBrowserMiddleware:
    lock = Lock()

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        with self.lock:
            return self.get_response(request)


settings.MIDDLEWARE = ["__main__.SerialMedicalBrowserMiddleware", *settings.MIDDLEWARE]
directory = Path(settings.DATABASES["default"]["NAME"]).parent
key_file = directory / "correction-access-browser-keys.json"
if not key_file.exists():
    key_file.write_text(json.dumps([base64.urlsafe_b64encode(secrets.token_bytes(32)).decode("ascii") for _ in range(2)]), encoding="ascii")
keys = json.loads(key_file.read_text(encoding="ascii"))
settings.MEDICAL_DATA_KEYS = {"browser": keys[0]}
settings.MEDICAL_DATA_ACTIVE_KEY_ID = "browser"
settings.MEDICAL_IDENTITY_INDEX_KEY = keys[1]
call_command("migrate", interactive=False, verbosity=0)
from apps.businesses.models import Business, BusinessCapability
from apps.businesses.profiles import PROFILE_MODULES
from apps.medical.tests_correction_documents import CorrectionDocumentTests
from apps.medical.tests_document_template_source import DocumentTemplateSourceTests

if not Business.objects.filter(slug="medical-role").exists():
    fixture = type("CorrectionBrowserFixture", (), {})
    CorrectionDocumentTests.setUpTestData.__func__(fixture)
    DocumentTemplateSourceTests.setUp(fixture)
    DocumentTemplateSourceTests.approve(fixture)
    DocumentTemplateSourceTests.save(fixture)
    for user in (fixture.doctor, fixture.head):
        user.set_password(os.environ["E2E_PASSWORD"])
        user.save(update_fields=["password"])
    for assignment in fixture.business.members.filter(user__in=[fixture.doctor, fixture.head]):
        assignment.role = "admin"
        assignment.save(update_fields=["role"])
    for module in PROFILE_MODULES:
        BusinessCapability.objects.update_or_create(business=fixture.business, module_key=module, defaults={"is_enabled": True})
    from apps.medical.correction_access_services import request_correction_access, review_correction_access, close_correction_access
    sample, _ = request_correction_access(actor=fixture.doctor, business_id=fixture.business.pk,
        encounter_id=fixture.encounter_record.pk, expected_patient_revision=fixture.patient.revision,
        expected_target_revision=1, reason="Synthetic history request", idempotency_key="browser-history-request")
    review_correction_access(actor=fixture.head, business_id=fixture.business.pk, request_id=sample.pk,
        expected_revision=1, decision="approve", reason="Synthetic history approval", idempotency_key="browser-history-review")
    close_correction_access(actor=fixture.doctor, business_id=fixture.business.pk, request_id=sample.pk,
        expected_revision=2, decision="complete", reason="Synthetic history completion", idempotency_key="browser-history-close")
    fixture.appointment.status = "completed"
    fixture.appointment.save(update_fields=["status"])
    if plan_links_fixture:
        from apps.scheduling.models import VisitPlan, VisitPlanStep
        plan = VisitPlan.objects.create(business=fixture.business, client=fixture.patient.client,
                                       responsible_user=fixture.doctor, created_by=fixture.owner)
        VisitPlanStep.objects.create(plan=plan, position=1, service=fixture.appointment.service,
                                    resource=fixture.appointment.resource, branch=fixture.first)
call_command("runserver", f"127.0.0.1:{os.environ['E2E_DJANGO_PORT']}", use_reloader=False)
