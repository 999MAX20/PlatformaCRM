import hmac
import re

from django.db import transaction
from rest_framework.exceptions import NotFound, PermissionDenied, ValidationError

from apps.businesses.models import Business
from apps.core.domain_errors import InvalidTransition
from apps.core.idempotency import CRMCommandResult, run_idempotent_crm_command
from .appointment_access import assert_appointment_medical_basis
from .audit import write_patient_audit
from .clinical_identity import assert_verified_clinical_identity
from .identity_crypto import encrypt_medical_value, medical_request_digest
from .models import MedicalEncounter, MedicalOrder, MedicalOrderRevision, MedicalRoleAssignment, PatientProfile
from .order_content import encrypt_order_revision, read_order_revision, validate_order_content
from .participation_access import assert_treatment_medical_basis
from .role_access import assert_medical_branch_permission, assert_medical_role_permission


def order_access_context(*, actor, business_id, patient_id, appointment_id=None, participation_id=None):
    """Caller holds an atomic transaction and audits before returning patient data."""
    if (appointment_id is None) == (participation_id is None):
        raise ValidationError({"basis": "Select one current treatment access basis."})
    ids = [business_id, patient_id, appointment_id if appointment_id is not None else participation_id]
    if any(type(value) is not int or value <= 0 for value in ids):
        raise ValidationError({"order": "Provide valid identifiers."})
    business = Business.objects.select_for_update().filter(pk=business_id).first()
    if business is None:
        raise NotFound()
    assert_medical_role_permission(actor, business, "medical_prescriptions", "view")
    patient = PatientProfile.objects.select_for_update().filter(pk=patient_id,
        business=business, client__business_id=business_id).first()
    if patient is None:
        raise NotFound()
    if appointment_id is not None:
        assert_appointment_medical_basis(actor=actor, business=business, patient_id=patient_id,
            appointment_id=appointment_id, resource="medical_prescriptions")
    else:
        assert_treatment_medical_basis(actor=actor, business=business, patient_id=patient_id,
            participation_id=participation_id, resource="medical_prescriptions")
    return business, patient


def assert_order_writer(*, actor, business, patient, encounter, action, participation_id=None):
    context = assert_medical_branch_permission(actor, business, "medical_prescriptions", action,
                                               branch=encounter.branch)
    if (context.kind not in (MedicalRoleAssignment.Kinds.DOCTOR, MedicalRoleAssignment.Kinds.HEAD)
            or encounter.primary_clinician_id != context.member_id):
        raise PermissionDenied()
    encounter.clean()
    if participation_id is None:
        assert_appointment_medical_basis(actor=actor, business=business, patient_id=patient.pk,
            appointment_id=encounter.appointment_id, resource="medical_prescriptions", action=action)
    else:
        basis = assert_treatment_medical_basis(actor=actor, business=business, patient_id=patient.pk,
            participation_id=participation_id, resource="medical_prescriptions", action=action)
        if basis.branch_id != encounter.branch_id:
            raise PermissionDenied()
    assert_verified_clinical_identity(patient)


@transaction.atomic
def save_order_draft(*, actor, business_id, patient_id, encounter_id, expected_encounter_revision,
                     expected_patient_revision, content, idempotency_key, order_id=None,
                     expected_order_revision=None, reason="", participation_id=None,
                     template_version_id=None, expected_source_digest=None):
    ids = [business_id, patient_id, encounter_id, expected_encounter_revision, expected_patient_revision]
    if order_id is not None:
        ids.extend([order_id, expected_order_revision])
    elif expected_order_revision is not None:
        raise ValidationError({"order": "A new order has no expected revision."})
    if participation_id is not None:
        ids.append(participation_id)
    if any(type(value) is not int or value <= 0 for value in ids):
        raise ValidationError({"order": "Provide valid identifiers and revisions."})
    if not isinstance(idempotency_key, str) or not idempotency_key.strip() or len(idempotency_key) > 128:
        raise ValidationError({"idempotency_key": "Provide an idempotency key of at most 128 characters."})
    if not isinstance(reason, str) or len(reason) > 2000:
        raise ValidationError({"reason": "Provide a reason of at most 2000 characters."})
    content = validate_order_content(content)
    if template_version_id is not None:
        if (type(template_version_id) is not int or template_version_id <= 0 or
                not isinstance(expected_source_digest, str) or not re.fullmatch(r"[a-f0-9]{64}", expected_source_digest)):
            raise ValidationError({"template": "Provide an approved template and its preview digest."})
    elif expected_source_digest is not None:
        raise ValidationError({"template": "A source digest requires a template version."})
    business = Business.objects.select_for_update().filter(pk=business_id).first()
    if business is None:
        raise NotFound()
    action = "update" if order_id is not None else "create"
    assert_medical_role_permission(actor, business, "medical_prescriptions", action)
    patient = PatientProfile.objects.select_for_update().filter(pk=patient_id,
        business=business, client__business_id=business_id).first()
    if patient is None:
        raise NotFound()
    encounter = MedicalEncounter.objects.select_for_update().select_related("record", "branch").filter(
        pk=encounter_id, business=business, patient=patient).first()
    if encounter is None:
        raise PermissionDenied()
    assert_order_writer(actor=actor, business=business, patient=patient, encounter=encounter,
                        action=action, participation_id=participation_id)
    order = None
    if order_id is not None:
        order = MedicalOrder.objects.select_for_update().filter(pk=order_id,
            business=business, encounter=encounter, author=actor).first()
        if order is None:
            raise PermissionDenied()
    if template_version_id is not None:
        from .order_templates import order_template_source
        order_template_source(actor=actor, encounter=encounter, template_version_id=template_version_id,
                              participation_id=participation_id)

    def operation():
        if (patient.revision != expected_patient_revision or encounter.revision != expected_encounter_revision
                or encounter.state != "draft" or encounter.record.state != "active"):
            raise InvalidTransition("The patient or encounter changed; reload before saving.")
        if order is not None and (order.revision != expected_order_revision or order.state != "draft"):
            raise InvalidTransition("The order changed; reload before saving.")
        source_version, provenance, retained_template_id = None, None, None
        if template_version_id is not None:
            source_version, provenance, _ = order_template_source(actor=actor, encounter=encounter,
                template_version_id=template_version_id, participation_id=participation_id)
            if not hmac.compare_digest(provenance["source_digest"], expected_source_digest):
                raise InvalidTransition("The template source changed; preview it again before saving.")
            retained_template_id = template_version_id
        elif order is not None:
            previous = MedicalOrderRevision.objects.select_related("order").get(order=order, revision=order.revision)
            provenance = read_order_revision(previous).get("template_source")
            source_version = previous.source_version
            retained_template_id = previous.template_version_id
        draft = order or MedicalOrder(business=business, encounter=encounter, author=actor)
        draft.full_clean()
        draft.revision += 1
        draft.save()
        staging = encrypt_medical_value("{}", business_id=business.pk,
                                       subject_id=draft.pk, purpose="order_staging")
        version = MedicalOrderRevision.objects.create(order=draft, revision=draft.revision,
            author=actor, content_encrypted=staging, template_version_id=retained_template_id, source_version=source_version)
        version.content_encrypted = encrypt_order_revision(version, content=content, reason=reason, template_source=provenance)
        version.save(update_fields=["content_encrypted"])
        if template_version_id is not None:
            _, final_source, _ = order_template_source(actor=actor, encounter=encounter,
                template_version_id=template_version_id, participation_id=participation_id)
            if not hmac.compare_digest(final_source["source_digest"], expected_source_digest):
                raise InvalidTransition("The template source changed during saving; preview it again.")
        write_patient_audit(actor=actor, business=business, patient=patient, order_version=version,
                            action="order_draft_saved" if order is not None else "order_draft_created")
        return CRMCommandResult(data={}, resource=version, status_code=200 if order is not None else 201)

    result = run_idempotent_crm_command(business=business, actor=actor, action="medical.order.draft",
        idempotency_key=medical_request_digest({"key": idempotency_key}, business_id=business_id),
        payload={"patient": patient_id, "encounter": encounter_id, "order": order_id,
            "patient_revision": expected_patient_revision, "encounter_revision": expected_encounter_revision,
            "order_revision": expected_order_revision, "participation": participation_id,
            "content_digest": medical_request_digest({"content": content, "reason": reason}, business_id=business_id),
            **({"template_version": template_version_id, "source_digest": expected_source_digest}
               if template_version_id is not None else {})},
        operation=operation)
    version = MedicalOrderRevision.objects.select_related("order").get(
        pk=result.resource_id if result.replayed else result.resource.pk,
        order__business=business, order__encounter=encounter, order__author=actor)
    return version, result.replayed


def order_version_payload(*, actor, business, patient, version):
    write_patient_audit(actor=actor, business=business, patient=patient, action="read", order_version=version)
    return {"order_id": version.order_id, "version_id": version.pk, "revision": version.revision,
            "encounter_id": version.order.encounter_id, "state": version.order.state,
            "author_id": version.author_id, "author_name": version.author.full_name, "created_at": version.created_at,
            **read_order_revision(version)}


@transaction.atomic
def read_order_version(*, actor, business_id, patient_id, version_id, appointment_id=None, participation_id=None):
    if type(version_id) is not int or version_id <= 0:
        raise ValidationError({"version": "Provide a valid version."})
    business, patient = order_access_context(actor=actor, business_id=business_id, patient_id=patient_id,
        appointment_id=appointment_id, participation_id=participation_id)
    version = MedicalOrderRevision.objects.select_related("order").filter(pk=version_id,
        order__business=business, order__encounter__business=business, order__encounter__patient=patient).first()
    if version is None:
        raise PermissionDenied()
    return order_version_payload(actor=actor, business=business, patient=patient, version=version)
