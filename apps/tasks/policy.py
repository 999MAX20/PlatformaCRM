"""Task-specific assignment and linked-context rules, using existing permissions."""
from rest_framework.exceptions import PermissionDenied, ValidationError

from apps.businesses.access import Actions, Resources, can, team_user_ids_for
from apps.businesses.assignment_policy import assert_assignment_allowed, resolve_assignment_member
from apps.businesses.models import RolePermission


LINK_RESOURCES = {
    "client": Resources.CLIENTS, "lead": Resources.LEADS, "deal": Resources.DEALS,
    "appointment": Resources.APPOINTMENTS, "conversation": Resources.CONVERSATIONS,
    "parent_task": Resources.TASKS, "specialist": Resources.SETTINGS,
}


def validate_assignment(*, business, actor, assignee, creating=False):
    permission = can(actor, business, Resources.TASKS, Actions.CREATE if creating else Actions.UPDATE)
    if assignee is not None:
        if not assignee.is_active or not business.members.filter(user=assignee, is_active=True).exists():
            raise ValidationError({"assignee": "Select an active CRM member of this business."})
        if creating:
            resolve_assignment_member(business=business, user=assignee, resource=Resources.TASKS)
            if not permission.allowed:
                raise PermissionDenied("Task creation is not allowed.")
            if permission.scope == RolePermission.Scopes.OWN and assignee.id != actor.id:
                raise PermissionDenied("You can create a task only for yourself.")
            if permission.scope == RolePermission.Scopes.TEAM and assignee.id not in team_user_ids_for(actor, business):
                raise PermissionDenied("Select a member of your team.")
        else:
            assert_assignment_allowed(actor=actor, business=business, target_user=assignee, resource=Resources.TASKS)
    elif actor and permission.scope == RolePermission.Scopes.OWN:
        raise ValidationError({"assignee": "Choose yourself as the responsible CRM user."})


def can_view_link(actor, business, field, obj):
    return obj is not None and can(actor, business, LINK_RESOURCES[field], Actions.VIEW, obj=obj).allowed


def validate_task_links(*, business, actor, attrs, task=None):
    values = {field: attrs.get(field, getattr(task, field, None)) for field in LINK_RESOURCES}
    for field, obj in values.items():
        if obj is None:
            continue
        if obj.business_id != business.id:
            raise ValidationError({field: "Must belong to the task business."})
        if field in attrs and not can_view_link(actor, business, field, obj):
            raise PermissionDenied("A selected linked record is not available.")
    client_ids = {values["client"].id} if values["client"] else set()
    for field in ("lead", "deal", "appointment", "conversation"):
        client_id = getattr(values[field], "client_id", None)
        if client_id:
            client_ids.add(client_id)
    if len(client_ids) > 1:
        raise ValidationError({"client": "Linked records must refer to the same client."})
    parent = values["parent_task"]
    visited = {task.pk} if task and task.pk else set()
    while parent:
        if parent.pk in visited:
            raise ValidationError({"parent_task": "Task links cannot form a cycle."})
        visited.add(parent.pk)
        parent = parent.parent_task
    specialist = values["specialist"]
    if specialist and (getattr(specialist, "retired_at", None) or not specialist.is_active):
        if "specialist" in attrs and (task is None or task.specialist_id != specialist.pk):
            raise ValidationError({"specialist": "Select an active specialist."})


def task_available_actions(task, actor):
    if not actor or task.is_archived:
        return []
    if not can(actor, task.business, Resources.TASKS, Actions.UPDATE, obj=task).allowed:
        return []
    active = task.status in {"open", "in_progress", "waiting"}
    actions = ["comment"]
    if active:
        actions += ["edit", "assign", "complete", "cancel", "snooze", "watch"]
    if task.status == "open":
        actions.append("start")
    if task.status in {"open", "in_progress"}:
        actions.append("wait")
    if task.status == "waiting":
        actions.append("resume")
    if task.status in {"done", "cancelled"}:
        actions.append("reopen")
    return actions
