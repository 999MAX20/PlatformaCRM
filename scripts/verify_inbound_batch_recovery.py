"""Real Celery restart drill on owned PostgreSQL/Redis with synthetic providers."""
import argparse
from contextlib import ExitStack
import json
import os
from pathlib import Path
import shutil
import socket
import subprocess
import sys
import time
from types import SimpleNamespace
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.recovery_runtime import HIDDEN, recovery_runtime, stop_process
from scripts.verify_recovery_s04 import configured_app, dispatch, wait_until


def restrict_network():
    original = socket.socket.connect

    def connect(sock, address):
        if isinstance(address, tuple) and address[0] not in ("127.0.0.1", "::1", "localhost"):
            raise AssertionError("Recovery drill forbids non-loopback network access")
        return original(sock, address)

    socket.socket.connect = connect


def worker(app, directory, token):
    from celery.signals import worker_ready
    from apps.conversations.ai_qualification import ConversationQualification

    def record(kind):
        with (directory / "effects.jsonl").open("a", encoding="utf-8") as output:
            output.write(json.dumps({"kind": kind, "worker": token}) + "\n")

    def classify(**kwargs):
        record("classification")
        if (directory / "hold-model").exists():
            (directory / "model-entered").write_text(token, encoding="utf-8")
            wait_until(lambda: not (directory / "hold-model").exists(), "release mock model", timeout=120)
        return ConversationQualification(intent="price_question", confidence=.99, summary="Price"), None

    def reply(**kwargs):
        record("reply")
        return SimpleNamespace(output_text="5000 KZT"), None, [], []

    def send(*args, **kwargs):
        record("transport")
        return {"ok": True, "provider_message_id": "synthetic-recovery"}

    def ready(**kwargs):
        (directory / f"ready-{token}").write_text("ready", encoding="utf-8")

    worker_ready.connect(ready, weak=False)
    with ExitStack() as stack:
        stack.enter_context(patch("apps.conversations.auto_pipeline.qualify_conversation", side_effect=classify))
        stack.enter_context(patch("apps.conversations.auto_pipeline.suggest_bot_reply", side_effect=reply))
        stack.enter_context(patch("apps.bots.outbound_delivery.send_message", side_effect=send))
        app.worker_main(["worker", "--pool=solo", "--concurrency=1", "-Q", "integrations",
                         "--hostname", f"batch-{token}@%h", "--without-gossip", "--without-mingle", "--loglevel=INFO"])


def drill(app, directory):
    from datetime import timedelta
    from django.utils import timezone
    from apps.ai_core.models import AgentTurn
    from apps.bots import tests_inbound_batching as fixtures
    from apps.bots.models import InboundMessageBatch, BotMessage
    from apps.conversations.auto_pipeline import maybe_run_auto_pipeline

    fixture = SimpleNamespace()
    fixtures.InboundBatchTests.setUp(fixture)
    fixture.conversation.external_user_id = "isolated-recovery-recipient"
    fixture.conversation.save(update_fields=["external_user_id"])
    processes, streams = [], []
    report = {"head": os.environ["BATCH_RECOVERY_HEAD"], "backend": "PostgreSQL/Redis", "worker_pool": "solo"}

    def start(mode, token):
        stream = (directory / f"{mode}-{token}.log").open("w", encoding="utf-8")
        streams.append(stream)
        process = subprocess.Popen([sys.executable, str(Path(__file__).resolve()), f"--{mode}", token],
                                   cwd=ROOT, stdout=stream, stderr=subprocess.STDOUT, creationflags=HIDDEN)
        processes.append(process)
        if mode == "worker":
            wait_until(lambda: (directory / f"ready-{token}").exists() or process.poll() is not None,
                       "Celery worker readiness", timeout=60)
            assert process.poll() is None, "Worker exited before readiness"
        return process

    def enqueue(text, due):
        message = BotMessage.objects.create(conversation=fixture.conversation, direction="inbound", text=text)
        decision = maybe_run_auto_pipeline(conversation=fixture.conversation, message=message, channel=fixture.channel)
        assert decision.status == "queued_batch", decision.status
        InboundMessageBatch.objects.filter(conversation=fixture.conversation).update(due_at=due)
        return message

    def effects():
        path = directory / "effects.jsonl"
        return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()] if path.exists() else []

    try:
        first = start("worker", "before")
        message = enqueue("How much?", timezone.now() + timedelta(hours=1))
        assert not AgentTurn.objects.exists()
        stop_process(first)
        assert first.poll() is not None
        assert InboundMessageBatch.objects.get().pending
        InboundMessageBatch.objects.update(due_at=timezone.now() - timedelta(seconds=1))
        assert not effects()
        second = start("worker", "recovered")
        start("beat", "scheduler")
        wait_until(lambda: fixture.conversation.messages.filter(direction="outbound", status="sent").count() == 1,
                   "pending group recovered by real beat/worker", timeout=60)
        wait_until(lambda: AgentTurn.objects.filter(status="completed").count() == 1, "turn completed")
        assert not InboundMessageBatch.objects.get().pending
        for _ in range(2):
            dispatch(app, "bots.process_due_inbound_batches", queue="integrations")
        assert [item["kind"] for item in effects()] == ["classification", "reply", "transport"]
        assert AgentTurn.objects.get().idempotency_key == f"message:{message.pk}"
        report["pending_worker_restart"] = "PASS"
        report["duplicate_due_dispatch"] = "PASS"

        (directory / "hold-model").write_text("hold", encoding="utf-8")
        uncertain = enqueue("A different question", timezone.now() - timedelta(seconds=1))
        wait_until(lambda: (directory / "model-entered").exists(), "mock model entered after admission")
        assert AgentTurn.objects.filter(idempotency_key=f"message:{uncertain.pk}", status="preparing").exists()
        assert not InboundMessageBatch.objects.get().pending
        stop_process(second)
        assert second.poll() is not None
        (directory / "hold-model").unlink()
        start("worker", "after-crash")
        for _ in range(2):
            dispatch(app, "bots.process_due_inbound_batches", queue="integrations")
        replay = maybe_run_auto_pipeline(conversation=fixture.conversation, message=uncertain, channel=fixture.channel)
        assert replay.status == "skipped_preparing", replay.status
        assert [item["kind"] for item in effects()] == ["classification", "reply", "transport", "classification"]
        assert AgentTurn.objects.count() == 2
        assert fixture.conversation.messages.filter(direction="outbound").count() == 1
        report["uncertain_admitted_crash_no_replay"] = "PASS"
        report["uncertain_turn_state"] = "preparing; manual continuation required"
        report["effects"] = effects()
        beat_log = (directory / "beat-scheduler.log").read_text(encoding="utf-8")
        scheduled = [line.split("Sending due task ", 1)[1].split(" (", 1)[0]
                     for line in beat_log.splitlines() if "Sending due task " in line]
        assert scheduled and set(scheduled) == {"batch-recovery"}, scheduled
        report["beat_schedule_only_batching"] = "PASS"
        report["runtime_ports"] = json.loads((directory / "s04-runtime.json").read_text(encoding="utf-8"))
        Path(os.environ["BATCH_RECOVERY_REPORT"]).write_text(json.dumps(report, indent=2), encoding="utf-8")
        print(json.dumps(report), flush=True)
    finally:
        for process in reversed(processes):
            stop_process(process)
        for stream in streams:
            stream.close()
        destination = Path(os.environ["BATCH_RECOVERY_REPORT"]).with_suffix("")
        destination.mkdir(exist_ok=True)
        for path in directory.glob("*.log"):
            shutil.copyfile(path, destination / path.name)
        if (directory / "effects.jsonl").exists():
            shutil.copyfile(directory / "effects.jsonl", destination / "effects.jsonl")


def main():
    if len(sys.argv) >= 2 and sys.argv[1] in ("--worker", "--beat", "--drill"):
        app, directory = configured_app()
        restrict_network()
        if sys.argv[1] == "--worker":
            worker(app, directory, sys.argv[2])
        elif sys.argv[1] == "--beat":
            from django.test import override_settings
            schedule = {"batch-recovery": {"task": "bots.process_due_inbound_batches", "schedule": 1,
                                            "options": {"queue": "integrations"}}}
            with override_settings(CELERY_BEAT_SCHEDULE=schedule):
                app.conf.beat_schedule = schedule
                app.Beat(loglevel="INFO", schedule=str(directory / "beat-schedule"), max_interval=1).run()
        else:
            drill(app, directory)
        return
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pg-bin", required=True, type=Path)
    parser.add_argument("--redis-server", required=True, type=Path)
    args = parser.parse_args()
    output = ROOT / "output" / "ai-agents-message-batch-20261119"
    output.mkdir(exist_ok=True)
    report = output / f"celery-recovery-{time.time_ns()}.json"
    log = report.with_suffix(".log")
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    print(f"Evidence: {report}", flush=True)
    with log.open("w", encoding="utf-8") as stream:
        with recovery_runtime(pg_bin=args.pg_bin.resolve(), redis_server=args.redis_server.resolve(), logs=stream) as runtime:
            runtime.env.update(AI_ENABLED="True", AI_PROVIDER="mock", OUTBOUND_MESSAGES_RUN_INLINE="True",
                               BATCH_RECOVERY_REPORT=str(report), BATCH_RECOVERY_HEAD=head)
            runtime.run([sys.executable, str(Path(__file__).resolve()), "--drill"], timeout=300)
    data = json.loads(report.read_text(encoding="utf-8"))
    data["owned_runtime_cleanup"] = "PASS"
    report.write_text(json.dumps(data, indent=2), encoding="utf-8")
    print(json.dumps(data), flush=True)


if __name__ == "__main__":
    main()
