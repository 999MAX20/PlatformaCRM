"""Synthetic PostgreSQL/Redis/Celery recovery. Never accepts a working database."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from scripts.recovery_runtime import HIDDEN, free_port, recovery_runtime, stop_process


def configured_app():
    # Guard internal modes before importing Django/settings (and its .env).
    raw_directory = os.environ.get("S04_DIRECTORY", "")
    if not raw_directory:
        raise RuntimeError("An owned disposable runtime is required")
    directory = Path(raw_directory).resolve()
    if not directory.name.startswith("zani-quality-gate-") or not directory.is_dir():
        raise RuntimeError("An owned disposable runtime is required")
    identity = json.loads((directory / "s04-runtime.json").read_text(encoding="utf-8"))
    urls = {f"postgresql://codex_s04@127.0.0.1:{identity['pg_port']}/{name}"
            for name in ("s04_source", "s04_restored")}
    if os.environ.get("DATABASE_URL") not in urls or os.environ.get("REDIS_URL") != f"redis://127.0.0.1:{identity['redis_port']}/0":
        raise RuntimeError("Drill database/broker do not match the owned runtime")
    import django
    django.setup()
    from django.conf import settings
    from config.celery import app
    database = settings.DATABASES["default"]
    if (database["HOST"] != "127.0.0.1" or str(database["PORT"]) != str(identity["pg_port"])
            or database["NAME"] not in {"s04_source", "s04_restored"}
            or database["USER"] != "codex_s04"
            or settings.CELERY_BROKER_URL != f"redis://127.0.0.1:{identity['redis_port']}/0"):
        raise RuntimeError("Drill database/broker do not match the owned runtime")
    assert settings.DATABASES["default"]["NAME"] in {"s04_source", "s04_restored"}
    assert settings.DATABASES["default"]["HOST"] == "127.0.0.1"
    assert settings.CELERY_BROKER_URL.startswith("redis://127.0.0.1:")
    assert not settings.CELERY_TASK_ALWAYS_EAGER and not settings.AUTOMATIONS_RUN_INLINE
    assert Path(settings.MEDIA_ROOT).resolve().is_relative_to(directory)
    assert Path(settings.PRIVATE_MEDIA_ROOT).resolve().is_relative_to(directory)
    return app, directory


class Worker:
    def __init__(self, directory):
        self.directory = directory
        self.process = None
        self.log = (directory / "worker.log").open("a", encoding="utf-8")

    def start(self):
        self.process = subprocess.Popen([sys.executable, str(Path(__file__).resolve()), "--worker"],
                                        cwd=ROOT, stdout=self.log, stderr=subprocess.STDOUT, creationflags=HIDDEN)

    def stop(self):
        stop_process(self.process)

    def close(self):
        self.stop()
        self.log.close()


def wait_until(predicate, label, timeout=45):
    deadline = time.monotonic() + timeout
    while not predicate():
        if time.monotonic() >= deadline:
            raise AssertionError(f"Timed out: {label}")
        time.sleep(.2)


def install_failure_boundary(directory):
    from apps.automations import engine
    original = engine._execute_action
    def action_with_crash_window(action, **kwargs):
        result = original(action, **kwargs)
        if action.config.get("_s04_hold") and not (directory / "release").exists():
            (directory / "held").touch()
            wait_until(lambda: (directory / "release").exists(), "parent stops the owned worker", timeout=60)
        return result
    engine._execute_action = action_with_crash_window


def dispatch(app, name, *, queue, args=None):
    result = app.send_task(name, args=args or [], queue=queue)
    value = result.get(timeout=40)
    result.forget()
    return value


def queue_drill(app, directory):
    from django.utils import timezone
    from apps.accounts.models import User
    from apps.businesses.models import Business, BusinessMember
    from apps.automations.models import AutomationRule, AutomationAction, AutomationRun
    from apps.tasks.models import Task
    owner = User.objects.create_user(username="s04-owner", email="s04-owner@example.invalid")
    business = Business.objects.create(owner=owner, name="Synthetic S04", slug="s04")
    BusinessMember.objects.create(business=business, user=owner, role="owner")
    rule = AutomationRule.objects.create(business=business, name="Recovery", trigger_type="lead_created", is_active=True)
    for index, (kind, config, delay) in enumerate([
        ("create_task", {"title": "S04 before restart"}, 0), ("wait", {}, 3600),
        ("create_task", {"title": "S04 after restart"}, 0),
    ]):
        AutomationAction.objects.create(rule=rule, order=index, action_type=kind, config=config, delay_seconds=delay)
    run = AutomationRun.objects.create(business=business, rule=rule, trigger_type="lead_created",
                                       idempotency_key="s04-restart", run_after=timezone.now())
    worker = Worker(directory)
    try:
        worker.start()
        dispatch(app, "automations.process_automation_run", args=[run.pk], queue="automations")
        run.refresh_from_db()
        assert run.status == "waiting" and run.current_action_index == 2
        worker.stop()
        AutomationRun.objects.filter(pk=run.pk).update(run_after=timezone.now())
        worker.start()
        dispatch(app, "automations.process_due_automation_runs", queue="automations")
        dispatch(app, "automations.process_automation_run", args=[run.pk], queue="automations")
        run.refresh_from_db()
        assert run.status == "success" and run.current_action_index == 3
        assert Task.objects.filter(business=business).count() == 2
        assert Task.objects.filter(business=business, title="S04 before restart").count() == 1
        assert Task.objects.filter(business=business, title="S04 after restart").count() == 1
        print(json.dumps({"postgres_redis_worker_restart": "pass", "wait_resume": "pass", "duplicate_dispatch": "pass"}), flush=True)
        from scripts.recovery_scenarios import automation_recovery, reminder_replay
        automation_recovery(app, directory, worker, business, owner, dispatch, wait_until)
        reminder_replay(app, business, owner, dispatch)
        if os.environ.get("S04_PHASE") == "full":
            from scripts.recovery_files import file_drill, prepare_restore_manifest
            files = file_drill(app, directory, worker, business, owner, dispatch, wait_until)
            prepare_restore_manifest(directory, business, owner, files)
            worker.stop()
            # Publish while no worker can consume it, then parent loses Redis.
            rule = AutomationRule.objects.create(business=business, name="Broker recovery", trigger_type="lead_created", is_active=True)
            AutomationAction.objects.create(rule=rule, action_type="create_task", config={"title": "Recovered after broker loss"})
            run = AutomationRun.objects.create(business=business, rule=rule, trigger_type="lead_created",
                idempotency_key="s04-broker-loss", run_after=timezone.now())
            app.send_task("automations.process_automation_run", args=[run.pk], queue="automations")
    finally:
        worker.close()


def main():
    if sys.argv[1:] == ["--worker"]:
        app, directory = configured_app()
        install_failure_boundary(directory)
        app.worker_main(["worker", "--pool=solo", "--concurrency=1", "--loglevel=WARNING",
                         "--without-gossip", "--without-mingle", "--hostname=s04@%h",
                         "-Q", "default,automations,notifications,reports_exports,file_scans"])
        return
    if sys.argv[1:] == ["--beat"]:
        app, directory = configured_app()
        # Same production tasks, shortened cadence only for the synthetic drill.
        selected = {"automation-runtime", "notification-delivery", "export-runtime", "service-status-observations"}
        app.conf.beat_schedule = {key: {**value, "schedule": 2} for key, value in app.conf.beat_schedule.items() if key in selected}
        app.Beat(schedule=str(directory / "beat"), loglevel="WARNING", max_interval=1).run()
        return
    if sys.argv[1:] == ["--recover-broker"]:
        app, directory = configured_app()
        from apps.tasks.models import Task
        from apps.core.models import ServiceComponentState
        from apps.automations.models import AutomationRun
        worker = Worker(directory)
        beat = None
        try:
            worker.start()
            beat = subprocess.Popen([sys.executable, str(Path(__file__).resolve()), "--beat"], cwd=ROOT,
                                    stdout=worker.log, stderr=subprocess.STDOUT, creationflags=HIDDEN)
            wait_until(lambda: AutomationRun.objects.filter(idempotency_key="s04-broker-loss", status="success").exists(), "beat recovers durable work after broker loss")
            wait_until(lambda: ServiceComponentState.objects.exists(), "beat records service state")
            stop_process(beat)
            dispatch(app, "automations.process_due_automation_runs", queue="automations")
            assert Task.objects.filter(title="Recovered after broker loss").count() == 1
            manifest = json.loads((directory / "manifest.json").read_text(encoding="utf-8"))
            manifest["task_count"] = Task.objects.filter(business_id=manifest["business_id"]).count()
            (directory / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
            print(json.dumps({"redis_queue_loss_recovery": "pass", "real_beat": "pass", "service_sampler": "pass"}), flush=True)
        finally:
            stop_process(beat)
            worker.close()
        return
    if sys.argv[1:] == ["--restored"]:
        app, directory = configured_app()
        from scripts.recovery_files import verify_restored
        verify_restored(directory)
        return
    if sys.argv[1:] == ["--drill"]:
        app, directory = configured_app()
        queue_drill(app, directory)
        return
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pg-bin", required=True, type=Path)
    parser.add_argument("--redis-server", required=True, type=Path)
    parser.add_argument("--phase", choices=["queue", "full"], default="queue")
    parser.add_argument("--clamd", type=Path)
    parser.add_argument("--signatures", type=Path)
    args = parser.parse_args()
    if args.phase == "full" and (not args.clamd or not args.signatures):
        parser.error("Full file/restore verification requires --clamd and --signatures")
    suffix = ".exe" if os.name == "nt" else ""
    required = [args.redis_server, *(args.pg_bin / f"{name}{suffix}" for name in
                                    ("initdb", "pg_ctl", "createdb", "pg_dump", "pg_restore"))]
    if args.phase == "full":
        required.append(args.clamd)
        if not args.signatures.is_dir():
            parser.error("Signature directory does not exist")
    if any(not item.is_file() for item in required):
        parser.error("Required runtime executable does not exist")
    logs = ROOT / "output" / "crm-s04-20261014"
    logs.mkdir(parents=True, exist_ok=True)
    logfile = logs / f"runtime-{time.time_ns()}.log"
    with logfile.open("w", encoding="utf-8") as output:
        try:
            with recovery_runtime(pg_bin=args.pg_bin.resolve(), redis_server=args.redis_server.resolve(), logs=output) as runtime:
                runtime.env["S04_PHASE"] = args.phase
                if args.phase == "full":
                    runtime.env.update({"S04_CLAMD": str(args.clamd.resolve()), "S04_SIGNATURES": str(args.signatures.resolve()),
                                        "CLAMD_PORT": str(free_port())})
                try:
                    runtime.run([sys.executable, str(Path(__file__).resolve()), "--drill"], timeout=300)
                    if args.phase == "full":
                        runtime.lose_broker_queue()
                        runtime.run([sys.executable, str(Path(__file__).resolve()), "--recover-broker"], timeout=120)
                        runtime.restore_backup()
                finally:
                    import shutil
                    for name in ("worker.log", "clamd.log"):
                        if (runtime.directory / name).exists():
                            shutil.copyfile(runtime.directory / name, logfile.with_suffix(f".{name}"))
        except Exception:
            output.flush()
            print(logfile.read_text(encoding="utf-8", errors="replace")[-6000:])
            raise
    print(logfile)
    print(logfile.read_text(encoding="utf-8", errors="replace")[-1300:])


if __name__ == "__main__":
    main()
