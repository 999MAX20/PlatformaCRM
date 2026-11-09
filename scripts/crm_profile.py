"""Separate Python/SQL/connection costs on a disposable CRM benchmark fixture."""
import cProfile
import io
import json
import os
from pathlib import Path
import pstats
import statistics
import sys
import time
from collections import defaultdict

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def main():
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
    import django
    django.setup()
    from django.conf import settings
    from django.db import connection
    from rest_framework.test import APIClient

    config = json.loads(Path(sys.argv[1]).read_text())
    database = settings.DATABASES["default"]
    if (os.environ.get("CRM_LOAD_DISPOSABLE") != "1" or database["HOST"] != "127.0.0.1"
            or database["NAME"] not in {"crm_bench_small", "crm_bench_large"}
            or config["database"] != database["NAME"]):
        raise RuntimeError("Profiler requires its disposable fixture database")
    out = Path(sys.argv[2])
    subject = config["subjects"][0]
    business = subject["business"]
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION="Bearer " + subject["token"])
    routes = {
        "health": "/health/",
        "auth-me": "/api/auth/me/",
        "clients": f"/api/clients/?business={business}&page=1",
        "clients-search": f"/api/clients/?business={business}&search=Load%20client&page=1",
        "tasks": f"/api/tasks/?business={business}&page=1",
        "appointments": f"/api/appointments/?business={business}&start=2026-10-01&end=2026-12-01&page=1",
        "deals": f"/api/deals/?business={business}&page=1",
        "client-card": f"/api/clients/{subject['client']}/crm-card/",
        "dashboard": f"/api/analytics/owner-dashboard/?business={business}",
    }
    connect = []
    ping = []
    for _ in range(10):
        connection.close()
        start = time.perf_counter()
        connection.ensure_connection()
        connect.append((time.perf_counter() - start) * 1000)
        start = time.perf_counter()
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
        ping.append((time.perf_counter() - start) * 1000)
    report = {"database": database["NAME"], "connect_ms": connect, "select1_ms": ping, "routes": {}}
    for name, route in routes.items():
        samples = []
        queries = []

        def execute(execute, sql, params, many, context):
            start = time.perf_counter()
            try:
                return execute(sql, params, many, context)
            finally:
                queries.append({"sql": sql, "params": params, "ms": (time.perf_counter() - start) * 1000})

        for _ in range(4):
            connection.close()
            queries.clear()
            start = time.perf_counter()
            cpu = time.process_time()
            with connection.execute_wrapper(execute):
                response = client.get(route, HTTP_HOST="127.0.0.1")
            samples.append({"wall_ms": (time.perf_counter() - start) * 1000,
                            "cpu_ms": (time.process_time() - cpu) * 1000,
                            "sql_ms": sum(q["ms"] for q in queries), "queries": len(queries),
                            "status": response.status_code, "bytes": len(response.content)})
            assert response.status_code == 200, (name, response.status_code)
        profiler = cProfile.Profile()
        profiler.enable()
        response = client.get(route, HTTP_HOST="127.0.0.1")
        profiler.disable()
        stream = io.StringIO()
        pstats.Stats(profiler, stream=stream).strip_dirs().sort_stats("cumulative").print_stats(65)
        (out / f"profile-{name}.txt").write_text(stream.getvalue(), encoding="utf-8")
        grouped = defaultdict(lambda: {"count": 0, "ms": 0})
        for query in queries:
            grouped[query["sql"]]["count"] += 1
            grouped[query["sql"]]["ms"] += query["ms"]
        report["routes"][name] = {"samples": samples, "sql": sorted(
            [{"sql": sql, **stats} for sql, stats in grouped.items()], key=lambda v: -v["ms"])}
        if name in {"clients", "clients-search", "tasks", "client-card"}:
            plans = []
            with connection.cursor() as cursor:
                cursor.execute("SHOW jit")
                original_jit = cursor.fetchone()[0]
                try:
                    for query in sorted(queries, key=lambda q: -q["ms"])[:3]:
                        if not query["sql"].startswith("SELECT"):
                            continue
                        variants = {}
                        for jit in (original_jit, "off"):
                            cursor.execute("SELECT set_config('jit', %s, false)", [jit])
                            cursor.execute("EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON) " + query["sql"], query["params"])
                            variants[jit] = cursor.fetchone()[0]
                        plans.append({"sql": query["sql"], "variants": variants})
                finally:
                    cursor.execute("SELECT set_config('jit', %s, false)", [original_jit])
            (out / f"plans-{name}.json").write_text(json.dumps(plans, indent=2), encoding="utf-8")
        print(name, json.dumps(samples[-1]), flush=True)
    (out / "diagnostic.json").write_text(json.dumps(report, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
