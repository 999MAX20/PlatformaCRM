"""Plan access is the union of readable Appointment candidates, never assignment."""
from rest_framework.exceptions import PermissionDenied

from apps.branches.access import assert_branch_access
from apps.businesses.access import Actions, Resources, assert_can
from apps.businesses.capabilities import assert_resource_enabled
from apps.scheduling.models import Appointment


def assert_plan_context(plan, actor):
    assert_resource_enabled(plan.business, Resources.APPOINTMENTS)
    assert_resource_enabled(plan.business, Resources.CLIENTS)
    assert_can(actor, plan.business, Resources.CLIENTS, Actions.VIEW, obj=plan.client)


def step_candidate(plan, step=None):
    if step is not None and step.appointment_id:
        return step.appointment
    return Appointment(business=plan.business, client=plan.client,
                       resource=step.resource if step else None,
                       branch=step.branch if step else None)


def assert_step_access(plan, step, actor, action):
    assert_plan_context(plan, actor)
    candidate = step_candidate(plan, step)
    assert_can(actor, plan.business, Resources.APPOINTMENTS, action, obj=candidate)
    if candidate.branch_id:
        assert_branch_access(actor, plan.business, candidate.branch)


def visible_steps(plan, actor):
    assert_plan_context(plan, actor)
    result = []
    steps = list(plan.steps.all())
    for step in steps:
        try:
            assert_step_access(plan, step, actor, Actions.VIEW)
        except PermissionDenied:
            continue
        result.append(step)
    if not result:
        if steps:
            raise PermissionDenied("No plan steps are available.")
        # Empty plans have no linked specialist and cannot confer OWN/TEAM access.
        assert_step_access(plan, None, actor, Actions.VIEW)
    return result


def assert_plan_change(plan, actor, action=Actions.UPDATE):
    steps = list(plan.steps.all())
    for step in steps or [None]:
        assert_step_access(plan, step, actor, action)
