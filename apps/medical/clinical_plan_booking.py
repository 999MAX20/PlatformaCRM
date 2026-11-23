from copy import deepcopy
from datetime import datetime
from decimal import Decimal, InvalidOperation
from uuid import UUID

from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied, ValidationError

from apps.branches.models import Branch
from apps.businesses.access import Actions
from apps.core.domain_errors import InvalidTransition
from apps.core.idempotency import CRMCommandResult, run_idempotent_crm_command
from apps.scheduling.models import Resource, VisitPlan, VisitPlanStep
from apps.scheduling.plan_access import assert_plan_change, assert_step_access
from apps.scheduling.plan_services import create_plan, change_plan
from apps.scheduling.record_commands import validate_responsible
from apps.services.models import Service
from .audit import write_patient_audit
from .clinical_plan_links import patient_visit_steps, visit_step_snapshot
from .encounter_content import read_encounter_revision
from .encounter_services import primary_draft_context, save_primary_encounter_draft
from .identity_crypto import medical_request_digest
from .models import MedicalEncounterRevision


def _reference(model, identifier, business):
    obj = model.objects.filter(pk=identifier, business=business).first()
    if obj is None:
        raise PermissionDenied()
    return obj


@transaction.atomic
def book_clinical_plan_step(*, actor, business_id, patient_id, encounter_id, expected_revision,
                           step_id, service_id, resource_id, branch_id, start_at, expected_price,
                           expected_duration_minutes, confirmed, idempotency_key, responsible_user_id=None,
                           expected_plan_revision=None, participation_id=None, notes=""):
    identifiers = [business_id, patient_id, encounter_id, expected_revision, service_id, resource_id, branch_id,
                   expected_duration_minutes]
    identifiers += [value for value in (responsible_user_id, expected_plan_revision, participation_id) if value is not None]
    if any(type(value) is not int or value <= 0 for value in identifiers) or confirmed is not True:
        raise ValidationError({"booking": "Provide valid identifiers and explicitly confirm the booking."})
    if not isinstance(start_at, datetime) or timezone.is_naive(start_at):
        raise ValidationError({"start_at": "Provide a timestamp with timezone."})
    if not isinstance(idempotency_key, str) or not idempotency_key.strip() or len(idempotency_key) > 128:
        raise ValidationError({"idempotency_key": "Provide an idempotency key of at most 128 characters."})
    if not isinstance(notes, str) or len(notes) > 10000:
        raise ValidationError({"notes": "Provide at most 10000 characters."})
    try:
        if not isinstance(step_id, str) or str(UUID(step_id)) != step_id:
            raise ValueError
        price = None if expected_price is None else Decimal(str(expected_price))
        if price is not None and (not price.is_finite() or price < 0):
            raise ValueError
    except (ValueError, InvalidOperation):
        raise ValidationError({"booking": "Provide a valid step identifier and expected price."}) from None
    business, patient, encounter, _ = primary_draft_context(actor=actor, business_id=business_id,
        patient_id=patient_id, encounter_id=encounter_id, participation_id=participation_id)
    source = MedicalEncounterRevision.objects.filter(encounter=encounter, revision=expected_revision).first()
    if source is None:
        raise InvalidTransition("The clinical plan changed; reload its saved version.")
    write_patient_audit(actor=actor, business=business, patient=patient, action="read", encounter_version=source)
    content = read_encounter_revision(source)["content"]
    clinical_step = next((step for step in content.get("plan_steps", []) if step["id"] == step_id), None)
    if clinical_step is None:
        raise InvalidTransition("Select a saved clinical plan step.")
    service = _reference(Service, service_id, business)
    resource = _reference(Resource, resource_id, business)
    branch = _reference(Branch, branch_id, business)
    responsible = get_user_model().objects.filter(pk=responsible_user_id or actor.pk).first()
    validate_responsible(business=business, actor=actor, user=responsible)
    candidate = VisitPlan(business=business, client=patient.client, responsible_user=responsible, created_by=actor)
    candidate_step = VisitPlanStep(plan=candidate, service=service, resource=resource, branch=branch)
    for action in (Actions.CREATE, Actions.UPDATE, Actions.VIEW):
        assert_step_access(candidate, candidate_step, actor, action)
    linked = None
    if "visit_step" in clinical_step:
        linked = patient_visit_steps(business_id=business_id, client_id=patient.client_id).select_related(
            "plan", "service", "resource", "branch", "appointment").filter(pk=clinical_step["visit_step"]["id"]).first()
        if linked is None:
            raise PermissionDenied()
        assert_plan_change(linked.plan, actor)
        if expected_plan_revision is None or linked.service_id != service_id:
            raise InvalidTransition("Review the linked plan and its service before booking.")
        if (linked.responsible_user_id or linked.plan.responsible_user_id) != responsible.pk:
            raise InvalidTransition("Review the responsible user of the linked plan.")

    key = medical_request_digest({"key": idempotency_key}, business_id=business_id)
    def operation():
        if encounter.revision != expected_revision:
            raise InvalidTransition("The clinical plan changed; review its saved version.")
        if linked is None:
            plan, _ = create_plan(business=business, actor=actor, client=patient.client, responsible_user=responsible,
                steps=[{"service": service, "resource": resource, "branch": branch}], idempotency_key=f"{key}:plan")
            step = plan.steps.get()
            plan_revision = plan.revision
        else:
            plan, step, plan_revision = linked.plan, linked, expected_plan_revision
        change_plan(plan=plan, actor=actor, command="schedule", expected_revision=plan_revision,
            idempotency_key=f"{key}:schedule", data={"step_id": step.pk, "start_at": start_at,
                "resource": resource, "branch": branch, "expected_price": price,
                "expected_duration_minutes": expected_duration_minutes, "notes": notes})
        step.refresh_from_db()
        updated = deepcopy(content)
        next(item for item in updated["plan_steps"] if item["id"] == step_id)["visit_step"] = visit_step_snapshot(step)
        version, _ = save_primary_encounter_draft(actor=actor, business_id=business_id, patient_id=patient_id,
            encounter_id=encounter_id, expected_revision=expected_revision, content=updated,
            participation_id=participation_id, idempotency_key=f"{key}:clinical")
        return CRMCommandResult(data={}, resource=version)

    digest = medical_request_digest({"encounter": encounter_id, "patient": patient_id, "revision": expected_revision,
        "step": step_id, "service": service_id, "resource": resource_id, "branch": branch_id,
        "start_at": start_at.isoformat(), "price": str(price) if price is not None else None,
        "duration": expected_duration_minutes, "responsible": responsible.pk, "plan_revision": expected_plan_revision,
        "participation": participation_id, "notes": notes}, business_id=business_id)
    result = run_idempotent_crm_command(business=business, actor=actor, action="medical.plan.book",
        idempotency_key=key, payload={"digest": digest}, operation=operation)
    version = MedicalEncounterRevision.objects.get(encounter=encounter,
        pk=result.resource_id if result.replayed else result.resource.pk)
    saved = read_encounter_revision(version)["content"]
    reference = next(step["visit_step"] for step in saved["plan_steps"] if step["id"] == step_id)
    step = patient_visit_steps(business_id=business_id, client_id=patient.client_id).select_related(
        "plan", "appointment", "resource", "branch").get(pk=reference["id"])
    assert_step_access(step.plan, step, actor, Actions.VIEW)
    return {"version_id": version.pk, "revision": version.revision, "plan_id": step.plan_id,
            "visit_step_id": step.pk, "appointment_id": step.appointment_id, "replayed": result.replayed}
