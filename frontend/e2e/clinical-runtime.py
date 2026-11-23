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
roles_fixture = os.environ.get("E2E_MEDICAL_ROLES") == "1"
templates_fixture = os.environ.get("E2E_MEDICAL_TEMPLATES") == "1"
orders_fixture = os.environ.get("E2E_MEDICAL_ORDERS") == "1"
plan_links_fixture = os.environ.get("E2E_MEDICAL_PLAN_LINKS") == "1"
plan_booking_fixture = os.environ.get("E2E_MEDICAL_PLAN_BOOKING") == "1"
rollout_fixture = os.environ.get("E2E_MEDICAL_ROLLOUT") == "1"
configure_browser_runtime()
import django
django.setup()
from django.conf import settings
from django.core.management import call_command

if rollout_fixture:
    settings.DENTAL_MEDICAL_RELEASE_ENABLED = True

directory = Path(settings.DATABASES["default"]["NAME"]).parent
key_file = directory / "medical-browser-keys.json"
if not key_file.exists():
    key_file.write_text(json.dumps([base64.urlsafe_b64encode(secrets.token_bytes(32)).decode("ascii") for _ in range(2)]), encoding="ascii")
keys = json.loads(key_file.read_text(encoding="ascii"))
if templates_fixture:
    from threading import Lock

    class SerialTemplateBrowserMiddleware:
        """Keep SQLite UI fixtures serial without blocking independent browser sockets."""
        lock = Lock()

        def __init__(self, get_response):
            self.get_response = get_response

        def __call__(self, request):
            with self.lock:
                return self.get_response(request)

    settings.MIDDLEWARE = ["__main__.SerialTemplateBrowserMiddleware", *settings.MIDDLEWARE]
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
if plan_booking_fixture:
    from datetime import time
    from apps.branches.models import Branch
    from apps.scheduling.models import WorkingHours
    from apps.services.models import Service
    business = Business.objects.get(slug="medical-role")
    business.timezone = "UTC"
    business.save(update_fields=["timezone"])
    Branch.objects.filter(business=business).update(uses_business_defaults=True)
    Service.objects.filter(business=business).update(price_from=100, duration_minutes=30)
    for weekday in range(7):
        WorkingHours.objects.get_or_create(business=business, resource=None, weekday=weekday,
                                          defaults={"start_time": time(8), "end_time": time(20)})
if plan_links_fixture:
    from apps.scheduling.models import VisitPlan, VisitPlanStep
    business = Business.objects.get(slug="medical-role")
    for appointment in Appointment.objects.filter(business=business).select_related("resource"):
        plan, created = VisitPlan.objects.get_or_create(business=business, client_id=appointment.client_id,
            defaults={"responsible_user_id": appointment.resource.linked_user_id, "created_by_id": business.owner_id})
        if created:
            for position in (1, 2):
                VisitPlanStep.objects.create(plan=plan, position=position, service_id=appointment.service_id,
                    resource_id=appointment.resource_id, branch_id=appointment.branch_id)
if rollout_fixture:
    from apps.businesses.medical_rollout import activate_medical_profile
    from apps.core.models import AuditLog
    business = Business.objects.get(slug="medical-role")
    rollout_audit = AuditLog.objects.filter(business=business, metadata__kind="dental_medical_profile_activated")
    if not rollout_audit.exists():
        business.profile_version = 1
        business.save(update_fields=["profile_version"])
        business.capabilities.filter(module_key="medical_records").update(is_enabled=False)
        assert activate_medical_profile(business_id=business.pk)["status"] == "activated"
    business.refresh_from_db()
    assert business.profile_version == 2 and rollout_audit.count() == 1
if orders_fixture:
    from apps.businesses.models import RolePermission
    from apps.medical.models import MedicalRoleAssignment
    order_assignment = MedicalRoleAssignment.objects.get(member__user__email="medical-role-doctor@example.test")
    for order_action in ("view", "create", "update"):
        RolePermission.objects.get_or_create(business_role=order_assignment.business_role,
            resource="medical_prescriptions", action=order_action, defaults={"scope": "own", "is_allowed": True})
if templates_fixture:
    from django.contrib.auth import get_user_model
    from apps.services.models import Service
    from apps.businesses.models import BusinessMember, BusinessRole, RolePermission
    from apps.medical.models import MedicalRoleAssignment
    assignment = MedicalRoleAssignment.objects.get(member__user__email="medical-role-doctor@example.test")
    for index in range(1, 26):
        Service.objects.get_or_create(business=assignment.member.business,
            name=f"Synthetic classification service {index:02d}")
    Service.objects.get_or_create(business=assignment.member.business,
        name="Synthetic long service " + "Ә" * 220)
    assignment.member.role = "specialist"
    assignment.member.save(update_fields=["role"])
    for action in ("view", "create", "update"):
        RolePermission.objects.get_or_create(business_role=assignment.business_role,
            resource="medical_documents", action=action, defaults={"scope": "own", "is_allowed": True})
    head, created = get_user_model().objects.get_or_create(username="medical-template-head",
        defaults={"email": "medical-template-head@example.test", "full_name": "Synthetic template reviewer"})
    if created:
        head.set_password(os.environ["E2E_PASSWORD"])
        head.save(update_fields=["password"])
        business = assignment.member.business
        member = BusinessMember.objects.create(business=business, user=head, role="specialist")
        role = BusinessRole.objects.create(business=business, name="Synthetic template reviewer")
        MedicalRoleAssignment.objects.create(member=member, business_role=role, kind="head", granted_by=business.owner)
        for action in ("view", "create", "update", "approve"):
            RolePermission.objects.create(business_role=role, resource="medical_documents",
                action=action, scope="business", is_allowed=True)
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
if roles_fixture:
    from django.contrib.auth import get_user_model
    from apps.branches.models import Branch, BranchAccess
    from apps.businesses.models import BusinessMember
    business = Business.objects.get(slug="medical-role")
    owner = business.owner
    owner.set_password(os.environ["E2E_PASSWORD"])
    owner.full_name = "Synthetic owner"
    owner.save(update_fields=["password", "full_name"])
    BusinessMember.objects.get_or_create(business=business, user=owner, defaults={"role": "owner"})
    for index in range(7):
        user, _ = get_user_model().objects.get_or_create(username=f"medical-role-target-{index}",
            defaults={"email": f"medical-role-target-{index}@example.test", "full_name": f"Synthetic role target {index}"})
        member, _ = BusinessMember.objects.get_or_create(business=business, user=user, defaults={"role": "specialist"})
        grant, _ = BranchAccess.objects.get_or_create(member=member, defaults={"all_branches": False})
        grant.branches.add(Branch.objects.get(business=business, name="First"))
settings.REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"]["auth_login"] = "200/min"
if rollout_fixture:
    from django.contrib.auth import get_user_model
    from apps.accounts.google_auth_signup import create_owner_account
    if not get_user_model().objects.filter(email="rollout-other@example.test").exists():
        create_owner_account({"email": "rollout-other@example.test", "password": os.environ["E2E_PASSWORD"],
            "business_name": "Synthetic other industry", "business_type": "beauty"})
if roles_fixture and len(sys.argv) > 1 and sys.argv[1] in ("disable-role-module", "enable-role-module"):
    BusinessCapability.objects.filter(business__slug="medical-role", module_key="medical_records").update(
        is_enabled=sys.argv[1] == "enable-role-module")
    sys.exit(0)
if len(sys.argv) > 2 and sys.argv[1] == "clinical-representatives-populate":
    from datetime import timedelta
    from apps.medical.models import PatientRepresentative
    from apps.medical.identity_crypto import encrypt_medical_value
    appointment = Appointment.objects.get(pk=int(sys.argv[2]), business__slug="medical-role")
    patient = PatientProfile.objects.get(business=appointment.business, client=appointment.client)
    now = timezone.now()
    for index in range(int(sys.argv[3])):
        state = ("active", "scheduled", "expired", "revoked")[index % 4]
        start = now + timedelta(days=1) if state == "scheduled" else now - timedelta(days=2)
        end = now - timedelta(days=1) if state == "expired" else now + timedelta(days=2)
        client = Client.objects.create(business=appointment.business, full_name=f"Synthetic representative {index} {state}")
        relation = PatientRepresentative.objects.create(patient=patient, representative_client=client,
            authority_encrypted="pending", verified_by=appointment.business.owner, verified_at=now-timedelta(days=3),
            valid_from=start, valid_until=end)
        authority = {"patient_id": patient.pk, "representative_client_id": client.pk,
            "valid_from": start.isoformat(), "valid_until": end.isoformat(), "permissions": ["give_consent"],
            "permission_labels": {"give_consent": {"ru": "Согласие", "kk": "Келісім", "en": "Consent"}}}
        relation.authority_encrypted = encrypt_medical_value(json.dumps(authority), business_id=patient.business_id,
            subject_id=relation.pk, purpose="representative_authority")
        if state == "revoked":
            relation.revoked_at, relation.revoked_by, relation.revocation_encrypted = now, appointment.business.owner, "synthetic"
        relation.save()
    sys.exit(0)
if len(sys.argv) > 2 and sys.argv[1] == "historical-documents-populate":
    from apps.medical.models import MedicalEncounter
    from apps.medical.template_services import save_personal_template_draft
    from apps.medical.template_reviews import submit_personal_template, decide_template_review
    from apps.medical.document_services import save_primary_document_draft
    encounter = MedicalEncounter.objects.select_related("patient", "primary_clinician__user").get(
        appointment_id=int(sys.argv[2]), business__slug="medical-role")
    actor, patient = encounter.primary_clinician.user, encounter.patient
    head = get_user_model().objects.get(username="medical-template-head")
    template, _ = save_personal_template_draft(actor=actor, business_id=patient.business_id,
        title=f"Synthetic historical document {patient.pk}", text="Synthetic source",
        idempotency_key=f"history-document-template-{patient.pk}")
    submit_personal_template(actor=actor, business_id=patient.business_id, version_id=template.pk,
        idempotency_key=f"history-document-submit-{patient.pk}")
    decide_template_review(actor=head, business_id=patient.business_id, version_id=template.pk,
        decision="approved", reason="Synthetic review", idempotency_key=f"history-document-approve-{patient.pk}")
    for index in range(int(sys.argv[3])):
        payload = dict(actor=actor, business_id=patient.business_id, patient_id=patient.pk,
            encounter_id=encounter.pk, expected_encounter_revision=encounter.revision,
            expected_patient_revision=patient.revision, template_version_id=template.pk)
        first, _ = save_primary_document_draft(**payload, idempotency_key=f"history-document-{patient.pk}-{index}",
            document_text=f"Synthetic historical document {index} v1")
        if index == 0:
            save_primary_document_draft(**payload, document_id=first.document_id, expected_document_revision=1,
                idempotency_key=f"history-document-update-{patient.pk}", reason="Synthetic correction",
                document_text="Synthetic historical document 0 v2")
    now = timezone.now()
    MedicalEncounter.objects.filter(pk=encounter.pk).update(state="finalized", ended_at=now, finalized_at=now, finalized_by=actor)
    Appointment.objects.filter(pk=encounter.appointment_id).update(status="completed")
    sys.exit(0)
if len(sys.argv) > 2 and sys.argv[1] in ("historical-orders-context", "historical-orders-populate", "historical-orders-end"):
    from apps.medical.record_services import open_dental_record
    from apps.medical.encounter_services import open_primary_encounter
    from apps.medical.order_services import save_order_draft
    from apps.medical.models import MedicalEncounter, TreatmentParticipation
    appointment = Appointment.objects.select_related("business", "resource__linked_user").get(
        pk=int(sys.argv[2]), business__slug="medical-role")
    patient = PatientProfile.objects.get(business=appointment.business, client=appointment.client)
    actor = appointment.resource.linked_user
    if sys.argv[1] == "historical-orders-context":
        record, _ = open_dental_record(actor=actor, business_id=patient.business_id, patient_id=patient.pk,
            appointment_id=appointment.pk, expected_patient_revision=patient.revision,
            number=f"HISTORY-{patient.pk}", idempotency_key=f"history-record-{patient.pk}")
        version, _ = open_primary_encounter(actor=actor, business_id=patient.business_id, patient_id=patient.pk,
            record_id=record.pk, appointment_id=appointment.pk, expected_patient_revision=patient.revision,
            expected_appointment_updated_at=appointment.updated_at, idempotency_key=f"history-encounter-{patient.pk}")
        encounter = version.encounter
        now = timezone.now()
        TreatmentParticipation.objects.get_or_create(patient=patient, member=encounter.primary_clinician,
            branch=encounter.branch, defaults={"state": "active", "proposed_by": appointment.business.owner,
                "proposed_at": now, "accepted_at": now})
    elif sys.argv[1] == "historical-orders-end":
        TreatmentParticipation.objects.filter(patient=patient, state="active").update(
            state="ended", closed_at=timezone.now(), closed_by=appointment.business.owner)
    else:
        encounter = MedicalEncounter.objects.get(appointment=appointment)
        for index in range(int(sys.argv[3])):
            payload = dict(actor=actor, business_id=patient.business_id, patient_id=patient.pk,
                encounter_id=encounter.pk, expected_encounter_revision=encounter.revision,
                expected_patient_revision=patient.revision)
            first, _ = save_order_draft(**payload, idempotency_key=f"history-order-{patient.pk}-{index}",
                content={"kind": "other", "text": f"Synthetic historical order {index} v1", "medication": {}})
            if index == 0:
                save_order_draft(**payload, order_id=first.order_id, expected_order_revision=1,
                    idempotency_key=f"history-order-update-{patient.pk}", reason="Synthetic correction",
                    content={"kind": "other", "text": "Synthetic historical order 0 v2", "medication": {}})
        now = timezone.now()
        MedicalEncounter.objects.filter(pk=encounter.pk).update(state="finalized", ended_at=now,
            finalized_at=now, finalized_by=actor)
        Appointment.objects.filter(pk=appointment.pk).update(status="completed")
    sys.exit(0)
if len(sys.argv) > 2 and sys.argv[1] in ("client-entry-pages", "client-entry-empty"):
    from copy import copy
    base = Appointment.objects.get(pk=int(sys.argv[2]), business__slug="medical-role")
    if sys.argv[1] == "client-entry-empty":
        Appointment.objects.filter(business=base.business, client=base.client).update(status="cancelled")
    else:
        for index in range(21):
            item = copy(base)
            item.pk = None
            item.start_at = base.start_at + timedelta(days=index + 1)
            item.end_at = base.end_at + timedelta(days=index + 1)
            item.save()
    sys.exit(0)
if len(sys.argv) > 1 and sys.argv[1] == "overview-demographics":
    from apps.medical.identity_crypto import encrypt_medical_value
    for patient in PatientProfile.objects.filter(business__slug="medical-role"):
        patient.demographics_encrypted = encrypt_medical_value(json.dumps({"date_of_birth": "2000-02-29"}),
            business_id=patient.business_id, subject_id=patient.client_id, purpose="demographics")
        patient.save(update_fields=["demographics_encrypted"])
    sys.exit(0)
if len(sys.argv) > 1 and sys.argv[1] in ("revoke", "restore"):
    from apps.medical.models import MedicalRoleAssignment
    MedicalRoleAssignment.objects.filter(member__business__slug="medical-role").update(revoked_at=timezone.now() if sys.argv[1] == "revoke" else None)
    sys.exit(0)
call_command("runserver", f"127.0.0.1:{os.environ['E2E_DJANGO_PORT']}", use_reloader=False,
             use_threading=templates_fixture)
