"""Local synthetic worker restart and SQLite restore drill; never uses a working DB.

Run with the project Python. Uses Celery's filesystem transport, not Redis/Postgres;
production transport, storage, RPO/RTO and deployment acceptance remain separate.
"""

import json
import os
from pathlib import Path
import sqlite3
import site
import shutil
from io import StringIO
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def configure_worker(directory):
    from config.celery import app
    from celery.signals import task_postrun

    app.conf.broker_url  # Resolve lazy Django configuration before scoped overrides.
    queue = directory / "queue"
    queue.mkdir(exist_ok=True)
    control = directory / "control"
    control.mkdir(exist_ok=True)
    app.conf.update(
        CELERY_BROKER_URL="filesystem://",
        CELERY_BROKER_TRANSPORT_OPTIONS={"data_folder_in": str(queue), "data_folder_out": str(queue), "control_folder": str(control)},
        CELERY_RESULT_BACKEND="cache+memory://",
        CELERY_TASK_ALWAYS_EAGER=False,
        CELERY_TASK_IGNORE_RESULT=True,
        CELERY_WORKER_HIJACK_ROOT_LOGGER=False,
    )
    if app.conf.broker_url != "filesystem://" or app.conf.result_backend != "cache+memory://" or app.conf.task_always_eager:
        raise RuntimeError("Drill Celery isolation settings were not applied")
    @task_postrun.connect(weak=False)
    def completed(task_id=None, **kwargs):
        (directory / f"done-{task_id}").touch()

    return app


def wait_for_run(run, status, worker):
    deadline = time.monotonic() + 45
    while time.monotonic() < deadline:
        if worker.poll() is not None:
            raise RuntimeError(f"Drill worker exited: {worker.returncode}")
        run.refresh_from_db()
        if run.status == status:
            return
        if run.status in {"failed", "skipped", "cancelled"}:
            raise RuntimeError(f"Synthetic automation ended as {run.status}; inspect worker log")
        time.sleep(0.25)
    raise RuntimeError(f"Timed out waiting for {status}; current={run.status}")


def stop_worker(worker):
    if worker.poll() is None:
        worker.terminate()
        try:
            worker.wait(timeout=10)
        except subprocess.TimeoutExpired:
            worker.kill()
            worker.wait(timeout=10)


def wait_for_dispatch(directory, dispatch, worker):
    deadline = time.monotonic() + 45
    while not (directory / f"done-{dispatch.id}").exists():
        if worker.poll() is not None or time.monotonic() >= deadline:
            raise RuntimeError("Queued drill dispatch did not complete")
        time.sleep(0.25)


def run_drill(directory):
    import django
    django.setup()
    from django.db import connection
    from django.core.management import call_command
    from django.utils import timezone
    from apps.accounts.models import User
    from apps.automations.models import AutomationAction, AutomationRule, AutomationRun
    from apps.businesses.models import Business, BusinessMember
    from apps.tasks.models import Task, TaskReminderDelivery
    from apps.notifications.models import Notification
    from apps.core.models import FileAttachment
    from apps.ai_core.models import AIJob

    app = configure_worker(directory)
    owner = User.objects.create_user(username="drill", email="drill@example.invalid")
    business = Business.objects.create(owner=owner, name="Synthetic recovery", slug="synthetic-recovery")
    BusinessMember.objects.create(business=business, user=owner, role="owner")
    rule = AutomationRule.objects.create(business=business, name="Restart drill", trigger_type="lead_created", is_active=True)
    for index, (kind, config, delay) in enumerate([
        ("create_task", {"title": "Before restart"}, 0),
        ("wait", {}, 3600),
        ("create_task", {"title": "After restart"}, 0),
    ]):
        AutomationAction.objects.create(rule=rule, order=index, action_type=kind, config=config, delay_seconds=delay)
    run = AutomationRun.objects.create(
        business=business, rule=rule, trigger_type="lead_created",
        idempotency_key="synthetic-restart", run_after=timezone.now(),
    )
    worker_command = [sys.executable, str(Path(__file__).resolve()), "--worker"]
    with (directory / "worker.log").open("w", encoding="utf-8") as log:
        worker = subprocess.Popen(worker_command, cwd=ROOT, stdout=log, stderr=subprocess.STDOUT)
        try:
            app.send_task("automations.process_automation_run", args=[run.id], queue="automations")
            wait_for_run(run, "waiting", worker)
            assert run.current_action_index == 2
            assert Task.objects.filter(business=business, title="Before restart").count() == 1
            Task.objects.filter(business=business, title="Before restart").update(
                assignee=owner, reminder_at=timezone.now() - timezone.timedelta(minutes=1),
            )
            stop_worker(worker)
            run.run_after = timezone.now() - timezone.timedelta(seconds=1)
            run.save(update_fields=["run_after"])
            worker = subprocess.Popen(worker_command, cwd=ROOT, stdout=log, stderr=subprocess.STDOUT)
            app.send_task("automations.process_due_automation_runs", queue="automations")
            wait_for_run(run, "success", worker)
            # A duplicate persisted dispatch is harmless after completion.
            duplicate = app.send_task("automations.process_automation_run", args=[run.id], queue="automations")
            wait_for_dispatch(directory, duplicate, worker)
            for _ in range(2):
                reminder_tick = app.send_task("notifications.process_due_notifications", queue="notifications")
                wait_for_dispatch(directory, reminder_tick, worker)
            reminders = Notification.objects.filter(business=business, text="Напоминание: Before restart")
            assert reminders.count() == 1 and reminders.get().status == "sent"
            assert TaskReminderDelivery.objects.filter(task__business=business).count() == 1

            ai_job = AIJob.objects.create(
                business=business, user=owner, source="crm", prompt_type="crm_assistant",
                idempotency_key="synthetic-interrupted-ai", input_json={"user_input": "Synthetic interrupted AI drill"},
            )
            app.send_task("ai.process_job", args=[ai_job.id], queue="ai")
            entered = directory / "ai-provider-entered"
            deadline = time.monotonic() + 45
            while not entered.exists():
                if worker.poll() is not None or time.monotonic() >= deadline:
                    raise RuntimeError("Synthetic AI job never reached the controlled provider boundary")
                time.sleep(0.25)
            ai_job.refresh_from_db()
            assert ai_job.status == "running" and ai_job.attempts == 1
            stop_worker(worker)
            AIJob.objects.filter(pk=ai_job.pk).update(locked_at=timezone.now() - timezone.timedelta(hours=1))
            worker = subprocess.Popen(worker_command, cwd=ROOT, stdout=log, stderr=subprocess.STDOUT)
            recovery = app.send_task("ai.process_due_jobs", queue="ai")
            wait_for_dispatch(directory, recovery, worker)
            ai_job.refresh_from_db()
            assert ai_job.status == "failed" and ai_job.attempts == 1 and ai_job.completed_at is not None
            assert ai_job.result_json == {} and entered.read_text() == "1"
        except Exception:
            log.flush()
            print((directory / "worker.log").read_text(encoding="utf-8", errors="replace")[-4000:])
            raise
        finally:
            stop_worker(worker)
    run.refresh_from_db()
    assert run.current_action_index == 3 and run.attempts == 2
    assert Task.objects.filter(business=business).count() == 2
    for title in ("Before restart", "After restart"):
        assert Task.objects.filter(business=business, title=title).count() == 1

    call_command("storage_runtime_smoke", business_id=business.id, stdout=StringIO())
    attachment = FileAttachment.objects.get(business=business, entity_type="storage_smoke")
    source = Path(attachment.file.path).resolve()
    relative_file = source.relative_to(directory)
    restored_file = directory / "restored-files" / relative_file
    restored_file.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, restored_file)
    assert restored_file.read_bytes() == source.read_bytes()

    # Restore to another disposable DB and read it independently of Django's cache.
    connection.close()
    database = directory / "gate.sqlite3"
    with sqlite3.connect(database) as original, sqlite3.connect(directory / "restored.sqlite3") as restored:
        original.backup(restored)
        assert restored.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
        assert restored.execute("SELECT COUNT(*) FROM tasks_task").fetchone()[0] == 2
        assert restored.execute("SELECT COUNT(*) FROM tasks_taskreminderdelivery").fetchone()[0] == 1
        assert restored.execute("SELECT status, current_action_index FROM automations_automationrun WHERE id=?", (run.id,)).fetchone() == ("success", 3)
        assert restored.execute("SELECT file FROM core_fileattachment WHERE id=?", (attachment.id,)).fetchone()[0] == attachment.file.name
    print(json.dumps({"worker_restart": "pass", "persisted_wait_resume": "pass", "duplicate_dispatch": "pass", "task_reminder_replay": "pass", "ai_interrupted_job_recovery": "pass", "sqlite_restore": "pass", "private_file_restore": "pass", "tasks": 2, "transport": "filesystem", "production_acceptance": False}))


def hold_synthetic_ai_request(directory, **kwargs):
    if kwargs.get("user_input") != "Synthetic interrupted AI drill":
        raise RuntimeError("Unexpected AI request in the isolated recovery drill")
    entered = directory / "ai-provider-entered"
    entered.write_text(str(int(entered.read_text()) + 1) if entered.exists() else "1")
    # The parent terminates this owned worker after observing the persisted claim.
    # No provider connection or billable call is made by the drill.
    time.sleep(60)
    raise RuntimeError("Parent did not stop the synthetic AI worker")


def main():
    if len(sys.argv) == 1 or (len(sys.argv) == 3 and sys.argv[1] == "--dependencies"):
        from scripts.codex_verify import isolated_runtime

        with isolated_runtime(python=sys.executable) as runtime:
            environment = {**runtime.environment, "PILOT_DRILL_DIR": str(runtime.database_path.parent), "DJANGO_SETTINGS_MODULE": "config.settings"}
            if len(sys.argv) == 3:
                environment["PILOT_DRILL_DEPS"] = str(Path(sys.argv[2]).resolve(strict=True))
            subprocess.run([sys.executable, "manage.py", "migrate", "--noinput", "--verbosity", "0"], cwd=ROOT, env=environment, check=True)
            subprocess.run([sys.executable, str(Path(__file__).resolve()), "--drill"], cwd=ROOT, env=environment, check=True)
        return
    directory = Path(os.environ["PILOT_DRILL_DIR"]).resolve()
    expected = f"sqlite:///{(directory / 'gate.sqlite3').as_posix()}"
    if os.environ.get("ZANI_QUALITY_GATE") != "1" or os.environ.get("DATABASE_URL") != expected:
        raise RuntimeError("Refusing drill outside its isolated database")
    if os.environ.get("PILOT_DRILL_DEPS"):
        site.addsitedir(os.environ["PILOT_DRILL_DEPS"])
    if sys.argv[1:] == ["--worker"]:
        import django
        from functools import partial
        from unittest.mock import patch
        django.setup()
        with patch("apps.ai_core.services.run_ai_request", side_effect=partial(hold_synthetic_ai_request, directory)):
            configure_worker(directory).worker_main(["worker", "--pool=solo", "--concurrency=1", "-Q", "automations,notifications,ai", "--without-gossip", "--without-mingle", "--without-heartbeat", "--loglevel=WARNING"])
    elif sys.argv[1:] == ["--drill"]:
        run_drill(directory)
    else:
        raise RuntimeError("Unknown drill mode")


if __name__ == "__main__":
    main()
