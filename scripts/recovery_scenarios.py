"""Synthetic scenarios against the real S04 PostgreSQL/Redis worker."""
import json


def report(**results):
    print(json.dumps(results), flush=True)


def automation_recovery(app, directory, worker, business, owner, dispatch, wait_until):
    from django.utils import timezone
    from rest_framework.test import APIClient
    from apps.accounts.models import User
    from apps.automations.models import AutomationRule, AutomationAction, AutomationRun
    from apps.businesses.models import Business, BusinessMember
    from apps.tasks.models import Task

    def create_run(name, actions, entity=None):
        rule = AutomationRule.objects.create(business=business, name=name, trigger_type="lead_created", is_active=True)
        for index, config in enumerate(actions):
            AutomationAction.objects.create(rule=rule, order=index, **config)
        return AutomationRun.objects.create(business=business, rule=rule, trigger_type="lead_created",
            idempotency_key=name, run_after=timezone.now(),
            entity_type="Task" if entity else "", entity_id=str(entity.pk) if entity else "")

    crashed = create_run("crash", [
        {"action_type": "create_task", "config": {"title": "Committed before crash"}},
        {"action_type": "create_task", "config": {"title": "Rolled back crash window", "_s04_hold": True}},
    ])
    app.send_task("automations.process_automation_run", args=[crashed.pk], queue="automations")
    wait_until(lambda: (directory / "held").exists(), "worker enters transaction crash window")
    crashed.refresh_from_db()
    assert crashed.status == "running" and crashed.current_action_index == 1
    assert Task.objects.filter(business=business, title="Committed before crash").count() == 1
    assert not Task.objects.filter(business=business, title="Rolled back crash window").exists()
    worker.stop()
    (directory / "release").touch()
    AutomationRun.objects.filter(pk=crashed.pk).update(locked_at=timezone.now() - timezone.timedelta(hours=1))
    worker.start()
    dispatch(app, "automations.process_due_automation_runs", queue="automations")
    dispatch(app, "automations.process_automation_run", args=[crashed.pk], queue="automations")
    crashed.refresh_from_db()
    assert crashed.status == "success" and crashed.attempts == 2
    assert Task.objects.filter(business=business, title="Committed before crash").count() == 1
    assert Task.objects.filter(business=business, title="Rolled back crash window").count() == 1
    report(worker_killed_mid_transaction="pass", stale_claim_recovery="pass", effects_exactly_once="pass")

    api = APIClient()
    api.force_authenticate(owner)
    cancelled = create_run("cancel", [
        {"action_type": "wait", "delay_seconds": 3600},
        {"action_type": "create_task", "config": {"title": "Only after explicit retry"}},
    ])
    dispatch(app, "automations.process_automation_run", args=[cancelled.pk], queue="automations")
    url = f"/api/automation-runs/{cancelled.pk}"
    outsider = User.objects.create_user(username="s04-other", email="s04-other@example.invalid")
    Business.objects.create(owner=outsider, name="Other S04", slug="s04-other")
    operator = User.objects.create_user(username="s04-operator", email="s04-operator@example.invalid")
    BusinessMember.objects.create(business=business, user=operator, role="operator")
    # The tenant/scoped queryset hides inaccessible runs before action lookup.
    for actor, expected in ((outsider, 404), (operator, 404)):
        api.force_authenticate(actor)
        for action in ("cancel", "retry"):
            response = api.post(f"{url}/{action}/")
            assert response.status_code == expected, (action, response.status_code)
    api.force_authenticate(owner)
    assert api.post(f"{url}/cancel/").status_code == 200
    dispatch(app, "automations.process_automation_run", args=[cancelled.pk], queue="automations")
    cancelled.refresh_from_db()
    assert cancelled.status == "cancelled"
    assert not Task.objects.filter(business=business, title="Only after explicit retry").exists()
    assert api.post(f"{url}/retry/").status_code == 200
    dispatch(app, "automations.process_automation_run", args=[cancelled.pk], queue="automations")
    cancelled.refresh_from_db()
    assert cancelled.status == "success"
    assert Task.objects.filter(business=business, title="Only after explicit retry").count() == 1

    task = Task.objects.get(business=business, title="S04 before restart")
    retried = create_run("retry", [
        {"action_type": "create_task", "config": {"title": "Before failed action"}},
        {"action_type": "assign_user", "config": {"user_id": 999999}},
    ], entity=task)
    dispatch(app, "automations.process_automation_run", args=[retried.pk], queue="automations")
    retried.refresh_from_db()
    assert retried.status == "retry_scheduled" and retried.current_action_index == 1
    AutomationAction.objects.filter(rule=retried.rule, action_type="assign_user").update(config={"user_id": owner.pk})
    assert api.post(f"/api/automation-runs/{retried.pk}/retry/").status_code == 200
    dispatch(app, "automations.process_automation_run", args=[retried.pk], queue="automations")
    retried.refresh_from_db()
    task.refresh_from_db()
    assert retried.status == "success" and task.assignee_id == owner.pk
    assert Task.objects.filter(business=business, title="Before failed action").count() == 1
    report(api_retry_cancel="pass", permission_and_tenant_denial="pass", failed_action_resume="pass")


def reminder_replay(app, business, owner, dispatch):
    from django.utils import timezone
    from apps.tasks.models import Task, TaskReminderDelivery
    from apps.notifications.models import Notification
    task = Task.objects.get(business=business, title="S04 before restart")
    Task.objects.filter(pk=task.pk).update(assignee=owner, reminder_at=timezone.now() - timezone.timedelta(minutes=1))
    for _ in range(2):
        dispatch(app, "notifications.process_due_notifications", queue="notifications")
    assert TaskReminderDelivery.objects.filter(task=task).count() == 1
    assert Notification.objects.filter(business=business, text="Напоминание: S04 before restart", status="sent").count() == 1
    report(real_notification_queue="pass", reminder_replay="pass")
