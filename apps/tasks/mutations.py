"""Serialize task changes and keep entity, activity and notifications atomic."""
from functools import wraps

from django.db import transaction
from django.utils.dateparse import parse_datetime

from apps.businesses.access import Actions, Resources, assert_can
from apps.core.domain_errors import InvalidTransition
from apps.core.idempotency import CRMCommandResult, run_idempotent_crm_command
from rest_framework.response import Response
from apps.tasks.models import Task


def check_task_version(task, request):
    expected = getattr(request, "headers", {}).get("X-Task-Version") if request else None
    if expected and parse_datetime(expected) != task.updated_at:
        raise InvalidTransition(errors={"version": "Task changed. Refresh before applying your changes."})


def locked_task_change(operation):
    @wraps(operation)
    def change(*, task, **kwargs):
        with transaction.atomic():
            locked = Task.objects.select_for_update().get(pk=task.pk)
            request = kwargs.get("request")
            if request is not None:
                assert_can(request.user, locked.business, Resources.TASKS, Actions.UPDATE, obj=locked)
            if locked.is_archived:
                raise InvalidTransition(errors={"task": "Restore the archived task before changing it."})
            check_task_version(locked, request)
            result = operation(task=locked, **kwargs)
            # Preserve callers holding the original model instance.
            task.refresh_from_db()
            return result
    return change


def task_command(operation):
    """Replay a command only after checking current actor access to the task."""
    @wraps(operation)
    def execute(view, request, *args, **kwargs):
        task = view.get_unassigned_action_object() if operation.__name__ in {"assign", "assign_to_me"} else view.get_object()
        assert_can(request.user, task.business, Resources.TASKS, Actions.UPDATE, obj=task)

        def perform():
            with transaction.atomic():
                locked = Task.objects.select_for_update().get(pk=task.pk)
                assert_can(request.user, locked.business, Resources.TASKS, Actions.UPDATE, obj=locked)
                check_task_version(locked, request)
                if locked.is_archived:
                    raise InvalidTransition(errors={"task": "Restore the task before changing it."})
                response = operation(view, request, *args, **kwargs)
                return CRMCommandResult(data=response.data, status_code=response.status_code, resource=locked)

        result = run_idempotent_crm_command(
            business=task.business, actor=request.user,
            action=f"tasks.{task.pk}.{operation.__name__}",
            idempotency_key=request.headers.get("Idempotency-Key", ""),
            payload={"data": request.data, "version": request.headers.get("X-Task-Version", "")},
            operation=perform,
        )
        if result.replayed and operation.__name__ != "add_comment":
            # Recheck related-record masking against today's permissions on replay.
            return Response(view.get_serializer(Task.objects.get(pk=task.pk)).data, status=result.status_code)
        return Response(result.data, status=result.status_code)
    return execute
