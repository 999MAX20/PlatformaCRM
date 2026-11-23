"""Fresh clinic-level matrix scope for each completion browser scenario."""
import os
from datetime import timedelta
from uuid import uuid4

from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone


@transaction.atomic
def prepare_completion():
    from apps.branches.models import Branch, BranchAccess
    from apps.businesses.models import Business, BusinessMember, BusinessCapability, BusinessRole, RolePermission
    from apps.clients.models import Client
    from apps.scheduling.models import Appointment, Resource
    from apps.services.models import Service
    from apps.medical.models import PatientProfile, MedicalRoleAssignment
    from apps.medical.record_services import open_dental_record
    from apps.medical.encounter_services import open_primary_encounter

    suffix = uuid4().hex[:12]
    source = Business.objects.get(slug="medical-role")
    email = f"completion-{suffix}@example.test"
    doctor = get_user_model().objects.create_user(username=f"completion-{suffix}", email=email,
        password=os.environ["E2E_PASSWORD"], first_name="Synthetic", last_name="Clinician")
    business = Business.objects.create(owner=source.owner, name=f"Synthetic completion {suffix}",
        slug=f"completion-{suffix}", business_type="dentistry", profile_key="dentistry", profile_version=2,
        profile_assigned_at=timezone.now())
    for key in ("medical_records", "clients", "appointments"):
        BusinessCapability.objects.create(business=business, module_key=key, is_enabled=True)
    branch = Branch.objects.create(business=business, name="Synthetic completion branch")
    member = BusinessMember.objects.create(business=business, user=doctor, role="specialist")
    BranchAccess.objects.create(member=member, all_branches=True)
    role = BusinessRole.objects.create(business=business, name="Synthetic clinician")
    assignment = MedicalRoleAssignment.objects.create(member=member, business_role=role, kind="doctor", granted_by=source.owner)
    assignment.branches.add(branch)
    for resource in ("medical_records", "medical_documents", "medical_patients"):
        for action in ("view", "create", "update"):
            RolePermission.objects.create(business_role=role, resource=resource, action=action, scope="own", is_allowed=True)
    client = Client.objects.create(business=business, full_name=f"Synthetic completion patient {suffix}")
    patient = PatientProfile.objects.create(business=business, client=client, created_by=source.owner,
        identity_status="verified", verified_at=timezone.now(), verified_by=source.owner,
        verification_evidence_encrypted="synthetic-fixture-only")
    service = Service.objects.create(business=business, name="Synthetic consultation")
    specialist = Resource.objects.create(business=business, name="Synthetic clinician", linked_user=doctor)
    start = timezone.now() + timedelta(days=1)
    appointment = Appointment.objects.create(business=business, branch=branch, client=client, service=service,
        resource=specialist, start_at=start, end_at=start + timedelta(hours=1))
    record, _ = open_dental_record(actor=doctor, business_id=business.pk, patient_id=patient.pk,
        appointment_id=appointment.pk, expected_patient_revision=patient.revision, number=f"SYN-{suffix}", idempotency_key="record")
    open_primary_encounter(actor=doctor, business_id=business.pk, patient_id=patient.pk, record_id=record.pk,
        appointment_id=appointment.pk, expected_patient_revision=patient.revision,
        expected_appointment_updated_at=appointment.updated_at, idempotency_key="encounter")
    return {"appointment_id": appointment.pk, "client_id": client.pk, "email": email}
