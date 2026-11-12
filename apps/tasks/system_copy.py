from apps.activities.models import ActivityEvent
from apps.activities.taxonomy import ActivityEvents


def follow_up_events(tasks):
    tasks = list(tasks)
    if not tasks:
        return {}
    events = ActivityEvent.objects.filter(
        business_id__in={task.business_id for task in tasks},
        entity_type="Task", event_type=ActivityEvents.TASK_CREATED,
        entity_id__in=[str(task.pk) for task in tasks],
    ).values("business_id", "entity_id", "metadata")
    return {(event["business_id"], event["entity_id"]): event["metadata"] for event in events}


def follow_up_copy(task, events):
    metadata = events.get((task.business_id, str(task.pk)), {})
    status = metadata.get("appointment_status")
    if not task.appointment_id or metadata.get("appointment_id") != task.appointment_id:
        return None
    from apps.scheduling.services import _appointment_follow_up_task_spec
    from types import SimpleNamespace

    reason = metadata.get("reason") or ""
    spec = _appointment_follow_up_task_spec(
        SimpleNamespace(id=task.appointment_id, status=status), reason=reason,
    )
    if not spec:
        return None
    title = task.title == spec["title"]
    description = task.description == spec["description"]
    if not title and not description:
        return None
    return {"kind": "appointment_follow_up", "status": status,
            "title": title, "description": description, "reason": reason if description else ""}
