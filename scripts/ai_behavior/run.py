"""Run only on disposable synthetic data. --live is an explicitly authorized operation."""
import argparse
import json
import logging
import os
from pathlib import Path
import subprocess
import sys
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--suite", choices=["smoke", "profiles", "temperature", "scope", "dialogue", "analytics", "commands", "pipeline", "final_responses", "final_crm", "continuity"], default="smoke")
    parser.add_argument("--max-calls", type=int, choices=range(1, 751), default=500, metavar="1..750")
    parser.add_argument("--live", action="store_true")
    parser.add_argument("--child", action="store_true")
    parser.add_argument("--case-filter", default="")
    parser.add_argument("--output", default="output/ai-agents-behavior-20261006")
    args = parser.parse_args()
    directory = (ROOT / args.output).resolve()
    if ROOT not in directory.parents or directory == ROOT:
        raise RuntimeError("Evaluation output must stay inside canonical workspace")
    directory.mkdir(parents=True, exist_ok=True)
    if not args.child:
        import django
        django.setup()
        from django.conf import settings
        from scripts.codex_verify import isolated_runtime
        key = settings.OPENROUTER_API_KEY if args.live else "dry-no-provider"
        if args.live and (settings.AI_PROVIDER != "openrouter" or not key):
            raise RuntimeError("Expected configured OpenRouter; no provider fallback")
        with isolated_runtime(python=sys.executable) as runtime:
            env = dict(runtime.environment)
            subprocess.run([sys.executable, "manage.py", "migrate", "--noinput"], cwd=ROOT, env=env, check=True, stdout=subprocess.DEVNULL)
            env.update(AI_PROVIDER="openrouter", OPENROUTER_API_KEY=key, OPENROUTER_BASE_URL="https://openrouter.ai/api/v1", AI_ENABLED="True", AI_QUEUE_LIVE_REQUESTS="False", AI_HTTP_TIMEOUT_SECONDS="45", AI_MAX_OUTPUT_TOKENS="600",
                       **{name: str(getattr(settings, name)) for name in ("AI_MODEL", "AI_FAST_MODEL", "AI_SMART_MODEL", "AI_CHEAP_MODEL", "AI_PROMPT_MODEL_TIERS")})
            command = [sys.executable, __file__, "--child", "--suite", args.suite, "--output", args.output]
            command.extend(["--max-calls", str(args.max_calls)])
            if args.case_filter:
                command.extend(["--case-filter", args.case_filter])
            if args.live:
                command.append("--live")
            subprocess.run(command, cwd=ROOT, env=env, check=True)
        return
    if os.environ.get("ZANI_QUALITY_GATE") != "1" or "zani-quality-gate-" not in os.environ.get("DATABASE_URL", ""):
        raise RuntimeError("Disposable environment required before Django setup")
    import django
    django.setup()
    logging.disable(logging.CRITICAL)
    from scripts.ai_behavior.fixtures import Laboratory, NOW
    from scripts.ai_behavior.transport import Transport
    from scripts.ai_behavior.suites import Evaluation
    transport = Transport(directory, live=args.live, max_calls=args.max_calls)
    transport.load_prices()
    import hashlib
    import time
    transport.run_id = args.suite + "-" + str(time.time_ns())
    manifest = {"run_id": transport.run_id, "suite": args.suite, "filter": args.case_filter, "source_sha256": {
        str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest()
        for folder in (ROOT / "apps/ai_core", ROOT / "apps/bots", ROOT / "apps/conversations", ROOT / "scripts/ai_behavior")
        for path in folder.rglob("*.py")}}
    with (directory / "run-manifests.jsonl").open("a", encoding="utf8") as stream:
        stream.write(json.dumps(manifest)+"\n")
    with patch("django.utils.timezone.now", return_value=NOW), patch("urllib.request.urlopen", side_effect=transport):
        lab = Laboratory()
        evaluation = Evaluation(lab, transport, directory, args.live)
        evaluation.case_filter = args.case_filter
        getattr(evaluation, args.suite)()
    print(json.dumps({"suite": args.suite, "live": args.live, "cases": evaluation.completed, "failed": evaluation.failures, "provider_calls": len(transport.calls), "results": str(evaluation.results_path)}, ensure_ascii=False), flush=True)
    if args.live and evaluation.failures:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
