import os

from django.contrib.auth import get_user_model
from django.db import transaction


@transaction.atomic
def prepare():
    from completion_fixture import prepare_completion
    from apps.branches.models import BranchAccess
    from apps.businesses.models import BusinessMember, BusinessRole, RolePermission
    from apps.medical.models import MedicalEncounter, MedicalRoleAssignment
    from apps.medical.common_template_services import save_common_template_draft, submit_common_template
    from apps.medical.template_reviews import decide_template_review
    from apps.medical.document_rule_services import save_document_rules
    from apps.medical.document_services import save_primary_document_draft
    from apps.medical.document_review_services import transition_document_review
    entry = prepare_completion()
    encounter = MedicalEncounter.objects.select_related("patient", "primary_clinician__user", "business").get(appointment_id=entry["appointment_id"])
    actor = encounter.primary_clinician.user
    actor.full_name = "Synthetic correction clinician"
    actor.save(update_fields=["full_name"])
    patient = encounter.patient
    head = get_user_model().objects.create_user(username="head-" + entry["email"], email="head-" + entry["email"],
        password=os.environ["E2E_PASSWORD"], full_name="Synthetic correction lead")
    member = BusinessMember.objects.create(business=encounter.business, user=head, role="admin")
    BranchAccess.objects.create(member=member, all_branches=True)
    role = BusinessRole.objects.create(business=encounter.business, name="Synthetic correction lead")
    assignment = MedicalRoleAssignment.objects.create(member=member, business_role=role, kind="head", granted_by=encounter.business.owner)
    assignment.branches.add(encounter.branch)
    for action in ("view", "create", "update", "approve"):
        RolePermission.objects.create(business_role=role, resource="medical_documents", action=action, scope="business")
    doctor_role = MedicalRoleAssignment.objects.get(member=encounter.primary_clinician).business_role
    RolePermission.objects.create(business_role=doctor_role, resource="medical_documents", action="sign", scope="own")
    title = f"Synthetic final correction {patient.pk}"
    template, _ = save_common_template_draft(actor=head, business_id=patient.business_id,
        title=title, text="Synthetic original document", idempotency_key="template")
    submit_common_template(actor=head, business_id=patient.business_id, version_id=template.pk, idempotency_key="submit")
    decide_template_review(actor=head, business_id=patient.business_id, version_id=template.pk,
        decision="approved", reason="", idempotency_key="approve")
    save_document_rules(actor=head, business_id=patient.business_id, template_ids=[template.template_id], reason="Synthetic",
        idempotency_key="rules", content={"name": title, "services": [], "default": {"required_at": "optional",
            "required_fields": [], "reviewers": ["primary_clinician"], "signers": [], "issuable": False}})
    version, _ = save_primary_document_draft(actor=actor, business_id=patient.business_id, patient_id=patient.pk,
        encounter_id=encounter.pk, expected_encounter_revision=encounter.revision, expected_patient_revision=patient.revision,
        template_version_id=template.pk, document_text="Synthetic original document", idempotency_key="document")
    scope = dict(actor=actor, business_id=patient.business_id, patient_id=patient.pk,
        appointment_id=encounter.appointment_id, version_id=version.pk)
    transition_document_review(**scope, expected_state_revision=1, target="ready_for_review", reason="", idempotency_key="submit-doc")
    transition_document_review(**scope, expected_state_revision=2, target="reviewed", reason="", idempotency_key="review-doc")
    return entry | {"version_id": version.pk, "title": title, "business_id": patient.business_id, "patient_id": patient.pk}


def finalize_fixture(entry):
    from apps.medical.models import MedicalDocumentRevision
    from apps.medical.document_artifact_services import prepare_document_signing_pdf
    from apps.medical.document_finalization_services import finalize_document
    from apps.core.models import FileAttachment
    version = MedicalDocumentRevision.objects.select_related("author", "document__encounter").get(pk=entry["version_id"])
    scope = dict(actor=version.author, business_id=entry["business_id"], patient_id=entry["patient_id"],
        appointment_id=entry["appointment_id"], version_id=version.pk)
    artifact, _ = prepare_document_signing_pdf(**scope, language="ru")
    FileAttachment.objects.filter(pk=artifact.attachment_id).update(scan_status="clean", scan_sha256=artifact.sha256)
    finalize_document(**scope, artifact_id=artifact.pk, expected_state_revision=3, idempotency_key="fixture-finalize")
    return entry


def timed_fixture(entry):
    from apps.businesses.models import RolePermission
    from apps.medical.models import MedicalDocumentRevision, MedicalRoleAssignment
    from apps.medical.correction_access_services import request_correction_access, review_correction_access
    from apps.medical.encounter_content import CLINICAL_FIELDS
    from apps.medical.encounter_services import save_primary_encounter_draft
    from apps.medical.encounter_completion import complete_primary_encounter
    version = MedicalDocumentRevision.objects.select_related("author", "document__encounter__appointment", "document__encounter__patient").get(pk=entry["version_id"])
    encounter = version.document.encounter
    head = MedicalRoleAssignment.objects.select_related("member__user").get(member__business_id=entry["business_id"], kind="head")
    for action in ("view", "manage"):
        RolePermission.objects.create(business_role=head.business_role, resource="medical_records", action=action, scope="business")
    grant, _ = request_correction_access(actor=version.author, business_id=entry["business_id"],
        encounter_id=encounter.pk, document_id=version.document_id, expected_patient_revision=encounter.patient.revision,
        expected_target_revision=version.revision, reason="Synthetic final correction", idempotency_key="grant-request")
    grant, _ = review_correction_access(actor=head.member.user, business_id=entry["business_id"], request_id=grant.pk,
        expected_revision=1, decision="approve", reason="Synthetic exact document", idempotency_key="grant-approve")
    clinical, _ = save_primary_encounter_draft(actor=version.author, business_id=entry["business_id"], patient_id=entry["patient_id"],
        encounter_id=encounter.pk, expected_revision=encounter.revision,
        content={field: "Synthetic completed care" for field in CLINICAL_FIELDS}, idempotency_key="completed-care")
    complete_primary_encounter(actor=version.author, business_id=entry["business_id"], patient_id=entry["patient_id"],
        encounter_id=encounter.pk, expected_revision=clinical.revision, expected_appointment_updated_at=encounter.appointment.updated_at,
        reason="Synthetic early finish", idempotency_key="finish-care")
    return entry | {"grant_id": grant.pk}
