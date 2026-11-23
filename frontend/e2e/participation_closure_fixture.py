from django.db import transaction
from django.utils import timezone


@transaction.atomic
def prepare(*, with_head=False):
    from completion_fixture import prepare_completion
    from apps.businesses.models import RolePermission
    from apps.medical.models import MedicalEncounter, MedicalRoleAssignment, TreatmentParticipation
    entry = prepare_completion()
    encounter = MedicalEncounter.objects.select_related("business", "primary_clinician").get(appointment_id=entry["appointment_id"])
    role = MedicalRoleAssignment.objects.get(member=encounter.primary_clinician)
    for action in ("view", "update"):
        RolePermission.objects.create(business_role=role.business_role, resource="medical_participation", action=action, scope="own")
    now = timezone.now()
    item = TreatmentParticipation.objects.create(patient=encounter.patient, member=encounter.primary_clinician,
        branch=encounter.branch, proposed_by=encounter.business.owner, proposed_at=now, accepted_at=now, state="active", revision=2)
    if with_head:
        import os
        from django.contrib.auth import get_user_model
        from apps.businesses.models import BusinessMember, BusinessRole
        from apps.branches.models import BranchAccess
        email = "head-" + entry["email"]
        user = get_user_model().objects.create_user(username=email, email=email, password=os.environ["E2E_PASSWORD"], full_name="Synthetic Lead")
        member = BusinessMember.objects.create(business=encounter.business, user=user, role="admin")
        BranchAccess.objects.create(member=member, all_branches=True)
        head_role = BusinessRole.objects.create(business=encounter.business, name="Synthetic closure lead")
        head = MedicalRoleAssignment.objects.create(member=member, business_role=head_role, kind="head", granted_by=encounter.business.owner)
        head.branches.add(encounter.branch)
        for action in ("view", "manage"):
            RolePermission.objects.create(business_role=head_role, resource="medical_participation", action=action, scope="business")
        entry["email"] = email
    return entry | {"participation_id": item.pk, "patient_id": encounter.patient_id, "business_id": encounter.business_id}


@transaction.atomic
def resolve(participation_id):
    from apps.medical.models import TreatmentParticipation, MedicalEncounter
    from apps.medical.encounter_content import CLINICAL_FIELDS
    from apps.medical.encounter_services import save_primary_encounter_draft
    from apps.medical.encounter_completion import complete_primary_encounter
    item = TreatmentParticipation.objects.select_related("member__user", "patient").get(pk=participation_id)
    encounter = MedicalEncounter.objects.select_related("appointment").get(patient=item.patient, primary_clinician=item.member)
    save_primary_encounter_draft(actor=item.member.user, business_id=item.patient.business_id, patient_id=item.patient_id,
        encounter_id=encounter.pk, expected_revision=encounter.revision,
        content={field: f"Synthetic closure {item.pk} {field}" for field in CLINICAL_FIELDS}, idempotency_key="closure-ready")
    encounter.refresh_from_db()
    complete_primary_encounter(actor=item.member.user, business_id=item.patient.business_id, patient_id=item.patient_id,
        encounter_id=encounter.pk, expected_revision=encounter.revision,
        expected_appointment_updated_at=encounter.appointment.updated_at, reason="Synthetic early completion", idempotency_key="closure-complete")
    return {"resolved": item.pk}
