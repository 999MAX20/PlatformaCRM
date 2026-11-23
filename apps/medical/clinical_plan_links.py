from django.db.models import Q
from rest_framework.exceptions import PermissionDenied

from apps.businesses.access import Actions
from apps.core.domain_errors import InvalidTransition
from apps.scheduling.models import VisitPlanStep
from apps.scheduling.plan_access import assert_step_access
from .identity_crypto import MedicalDataUnavailable
from .models import MedicalEncounterRevision, MedicalPlanStepLink


def visit_step_snapshot(step):
    return {"id": step.pk, "plan_id": step.plan_id, "position": step.position, "service_name": step.service.name}


def _references(content):
    return {step["id"]: step["visit_step"] for step in content.get("plan_steps", []) if "visit_step" in step}


def patient_visit_steps(*, business_id, client_id):
    return VisitPlanStep.objects.filter(plan__business_id=business_id, plan__client_id=client_id,
        plan__client__business_id=business_id, service__business_id=business_id).filter(
        Q(branch__isnull=True) | Q(branch__business_id=business_id),
        Q(resource__isnull=True) | Q(resource__business_id=business_id),
        Q(appointment__isnull=True) | Q(appointment__business_id=business_id, appointment__client_id=client_id))


def validate_plan_links_for_write(*, encounter, actor, content):
    """The encounter writer holds the Business lock and authorizes its clinical scope."""
    references = _references(content)
    if not references:
        return
    previous = MedicalEncounterRevision.objects.filter(encounter=encounter, revision=encounter.revision - 1).first()
    previous_links = {}
    if previous is not None:
        from .encounter_content import read_encounter_revision
        previous_links = _references(read_encounter_revision(previous)["content"])
    steps = {step.pk: step for step in patient_visit_steps(business_id=encounter.business_id,
        client_id=encounter.patient.client_id).select_related("plan__client", "plan__business", "service",
        "resource", "branch", "appointment__resource", "appointment__branch").filter(
        pk__in=[link["id"] for link in references.values()])}
    for key, link in references.items():
        step = steps.get(link["id"])
        if step is None or step.plan_id != link["plan_id"]:
            raise PermissionDenied()
        if previous_links.get(key) == link:
            continue
        assert_step_access(step.plan, step, actor, Actions.VIEW)
        if step.removed_at or step.plan.is_archived or step.plan.terminated_at:
            raise InvalidTransition("The visit step is no longer available for a new link.")
        if visit_step_snapshot(step) != link:
            raise InvalidTransition("The visit step changed; select it again.")


def store_plan_links(*, version, content):
    MedicalPlanStepLink.objects.bulk_create([MedicalPlanStepLink(version=version, step_id=key, visit_step_id=link["id"])
                                           for key, link in _references(content).items()])


def verify_plan_links(*, version, content):
    references = _references(content)
    if not references:
        return
    encounter = version.encounter
    rows = MedicalPlanStepLink.objects.filter(version=version, visit_step_id__in=patient_visit_steps(
        business_id=encounter.business_id, client_id=encounter.patient.client_id).values("pk"))
    actual = {str(key): (step, plan) for key, step, plan in rows.values_list("step_id", "visit_step_id", "visit_step__plan_id")}
    if actual != {key: (value["id"], value["plan_id"]) for key, value in references.items()}:
        raise MedicalDataUnavailable()
