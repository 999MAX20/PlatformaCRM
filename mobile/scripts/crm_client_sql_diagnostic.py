#!/usr/bin/env python3
"""One bounded, read-only, disposable CRM SQL diagnostic; never a runtime fix."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import threading
import time


def inside():
    from django.contrib.auth import get_user_model
    from django.db import connection, transaction
    from django.db.backends.postgresql.base import DatabaseWrapper
    from rest_framework.test import APIRequestFactory, force_authenticate
    from apps.clients.views import ClientViewSet
    from apps.clients.selectors import build_client_summary
    from apps.core.viewsets import TenantModelViewSet

    started = time.monotonic()
    deadline = started + 36
    report = {'status': 'BLOCKED', 'probes': [], 'observationErrors': [], 'readOnly': True,
              'explainAnalyze': False, 'statementLimitMs': 5000, 'lockLimitMs': 1000}
    stop = threading.Event()
    state_lock = threading.Lock()
    state = {'name': None, 'started': 0., 'active': False}
    samples = []
    observer = None

    def millis(limit):
        remaining = int((deadline-time.monotonic())*1000)-100
        if remaining <= 0:
            raise TimeoutError('Shared SQL helper deadline exhausted')
        return min(limit, remaining)

    def readonly(cursor, statement_ms):
        cursor.execute('SET TRANSACTION READ ONLY')
        cursor.execute("SELECT set_config('statement_timeout', %s, true), set_config('lock_timeout', %s, true)",
                       [str(millis(statement_ms)), str(millis(1000))])

    class Captured(Exception):
        def __init__(self, sql, params):
            self.sql, self.params = sql, params

    def capture(execute, sql, params, many, context):
        if many or not sql.lstrip().upper().startswith('SELECT '):
            raise RuntimeError('Only one SELECT may be captured')
        raise Captured(sql, params)

    def watch(pid, settings):
        db = DatabaseWrapper(settings, alias='bounded-sql-observer')
        seen = set()
        try:
            with db.cursor() as cursor:
                cursor.execute('SET default_transaction_read_only = on')
                cursor.execute("SET statement_timeout = '500ms'")
                cursor.execute("SET lock_timeout = '500ms'")
                while not stop.is_set() and time.monotonic() < deadline:
                    with state_lock:
                        name, start, active = state['name'], state['started'], state['active']
                    age = time.monotonic()-start
                    slots = [slot for slot in (0, 1, 3) if active and age >= slot and (name, slot) not in seen]
                    if not slots:
                        stop.wait(.05)
                        continue
                    slot = slots[-1]
                    seen.update((name, x) for x in slots)
                    cursor.execute("SELECT state,wait_event_type,wait_event,pg_blocking_pids(pid),EXTRACT(EPOCH FROM clock_timestamp()-query_start) FROM pg_stat_activity WHERE pid=%s", [pid])
                    activity = cursor.fetchone()
                    cursor.execute('SELECT locktype,mode,granted,COUNT(*) FROM pg_locks WHERE pid=%s GROUP BY locktype,mode,granted', [pid])
                    locks = cursor.fetchall()
                    samples.append({'probe': name, 'scheduledAtSeconds': slot, 'elapsedSeconds': round(time.monotonic()-started, 3),
                                    'activity': None if activity is None else {'state': activity[0], 'waitType': activity[1], 'waitEvent': activity[2],
                                        'blockingPids': activity[3], 'queryAgeSeconds': None if activity[4] is None else float(activity[4])},
                                    'locks': [{'type': x[0], 'mode': x[1], 'granted': x[2], 'count': x[3]} for x in locks]})
        except Exception as error:
            report['observationErrors'].append({'kind': type(error).__name__, 'sqlstate': getattr(error, 'sqlstate', None)})
        finally:
            db.close()

    try:
        connection.settings_dict['OPTIONS'] = {**connection.settings_dict.get('OPTIONS', {}), 'connect_timeout': 2}
        with transaction.atomic():
            with connection.cursor() as cursor:
                readonly(cursor, 2000)
                cursor.execute("SELECT pg_backend_pid(),current_setting('jit'),current_setting('jit_above_cost'),current_setting('jit_inline_above_cost'),current_setting('jit_optimize_above_cost')")
                pid, jit, above, inline, optimize = cursor.fetchone()
                report['postgres'] = {'pid': pid, 'jit': jit, 'jitAboveCost': above, 'jitInlineAboveCost': inline, 'jitOptimizeAboveCost': optimize}
            owner = get_user_model().objects.get(email='business_owner@example.com')
            raw = APIRequestFactory().get('/api/clients/')
            force_authenticate(raw, user=owner)
            view = ClientViewSet()
            view.args, view.kwargs, view.action_map = (), {}, {'get': 'list'}
            view.request = view.initialize_request(raw)
            view.format_kwarg = None
            view.check_permissions(view.request)
            plain = view.filter_queryset(TenantModelViewSet.get_queryset(view))
            annotated = view.filter_queryset(view.get_queryset(apply_quick_filter=False))
            # Both querysets come from the actual tenant/permission path. No direct all-tenant replacement.
            report['scope'] = {'view': 'ClientViewSet.list', 'actor': 'synthetic-owner', 'queryParameters': [],
                               'permissionCheck': 'passed', 'querysetPath': 'TenantModelViewSet -> ClientViewSet'}
        observer = threading.Thread(target=watch, args=(pid, connection.settings_dict.copy()), daemon=True)
        observer.start()
        probes = [
            ('plain-count', lambda: plain.all().count()),
            ('summary', lambda: build_client_summary(annotated.all())),
            ('annotated-distinct-count', lambda: annotated.all().count()),
            ('vip-count', lambda: annotated.filter(is_vip=True).count()),
        ]
        for name, operation in probes:
            row = {'name': name, 'status': 'BLOCKED', 'executionCount': 0, 'captureOnlyCalls': 1}
            report['probes'].append(row)
            probe_started = time.monotonic()
            try:
                millis(5000)
                try:
                    with connection.execute_wrapper(capture):
                        operation()
                except Captured as captured:
                    sql, params = captured.sql, captured.params
                else:
                    raise RuntimeError('Expected exactly one uncached SELECT, no capture obtained')
                row.update(sqlSha256=hashlib.sha256(sql.encode()).hexdigest(), sqlBytes=len(sql.encode()),
                           parameterTypes=[type(value).__name__ for value in (params or ())])
                with transaction.atomic():
                    with connection.cursor() as cursor:
                        readonly(cursor, 2000)
                        explain_started = time.monotonic()
                        cursor.execute('EXPLAIN (FORMAT JSON) '+sql, params)
                        plan = cursor.fetchone()[0]
                        if len(json.dumps(plan).encode()) > 2*1024*1024:
                            raise RuntimeError('Query plan evidence oversized')
                        row.update(plan=plan, explainSeconds=round(time.monotonic()-explain_started, 6))
                        cursor.execute("SELECT set_config('statement_timeout', %s, true),set_config('lock_timeout', %s, true)",
                                       [str(millis(5000)), str(millis(1000))])
                        with state_lock:
                            state.update(name=name, started=time.monotonic(), active=True)
                        execute_started = time.monotonic()
                        row['executionCount'] = 1
                        try:
                            cursor.execute(sql, params)
                            values = cursor.fetchall()
                            if len(values) != 1:
                                raise RuntimeError('Expected one count/aggregate result row')
                            row.update(status='PASS', result=[None if v is None else int(v) for v in values[0]])
                        finally:
                            row['executionSeconds'] = round(time.monotonic()-execute_started, 6)
                            with state_lock:
                                state['active'] = False
            except Exception as error:
                row.update(status='FAIL', error={'kind': type(error).__name__, 'sqlstate': getattr(error, 'sqlstate', None) or getattr(error.__cause__, 'sqlstate', None)},
                           transactionRollback='atomic exit; no retry of this query')
            finally:
                row['elapsedSeconds'] = round(time.monotonic()-probe_started, 6)
            # Each independent probe runs at most once; all failures remain red.
        complete = len(report['probes']) == 4 and all(p['status'] == 'PASS' and p['executionCount'] == 1 for p in report['probes'])
        report['status'] = 'PASS' if complete and not report['observationErrors'] else 'FAIL'
    except Exception as error:
        report.update(status='BLOCKED', error={'kind': type(error).__name__, 'sqlstate': getattr(error, 'sqlstate', None)})
    finally:
        stop.set()
        if observer:
            observer.join(timeout=max(0., min(1., deadline-time.monotonic())))
            if observer.is_alive():
                report.update(status='BLOCKED', observerStop='UNKNOWN')
        for name in ('plain-count','summary','annotated-distinct-count','vip-count'):
            if name not in {p['name'] for p in report['probes']}:
                report['probes'].append({'name':name,'status':'NOT_RUN','executionCount':0,'reason':'Required setup/shared budget did not pass'})
        if report['observationErrors'] and report['status']=='PASS':
            report['status']='BLOCKED'
        report.update(activitySamples=samples, elapsedSeconds=round(time.monotonic()-started, 3))
        if time.monotonic() > deadline:
            report.update(status='BLOCKED', deadlineExceeded=True)
        print('SQL_RESULT '+json.dumps(report, default=str), flush=True)
    return report


def host(project, output):
    if os.environ.get('GITHUB_ACTIONS') != 'true' or os.environ.get('GITHUB_REF') != 'refs/heads/codex/mobile-max':
        raise RuntimeError('Only disposable authorized mobile-branch Linux CI')
    expected = 'crm-test-'+os.environ.get('GITHUB_RUN_ID', '')+'-queue-web'
    if project != expected or not os.environ.get('GITHUB_RUN_ID', '').isdigit():
        raise RuntimeError('Per-run container ownership mismatch')
    started = time.monotonic()
    deadline = started+55
    compose = ['docker', 'compose', '--project-name', project, '-f', 'docker-compose.yml', '-f', 'mobile/ci/crm-test-stack.compose.yml', '--env-file', str(Path.cwd()/'.env')]
    report = {'status': 'BLOCKED', 'limits': {'phaseSeconds': 60, 'internalSeconds': 55, 'insideSeconds': 36}, 'cgroup': {}, 'sql': None}
    script = 'for name in memory.current memory.peak memory.max memory.events cpu.stat; do if test -r "/sys/fs/cgroup/$name"; then printf "__CGROUP__%s\\n" "$name"; cat "/sys/fs/cgroup/$name"; else printf "__MISSING__%s\\n" "$name"; fi; done'
    def run(args, seconds):
        remaining = deadline-time.monotonic()
        if remaining <= 0:
            raise TimeoutError('Shared SQL bundle deadline')
        return subprocess.run(args, capture_output=True, text=True, timeout=min(seconds, remaining))
    def memory(label):
        snapshots = {}
        for service in ('web', 'db'):
            result = run(compose+['exec', '-T', service, 'sh', '-c', script], 2)
            values = {}; field = None
            for line in result.stdout.splitlines():
                if line.startswith('__CGROUP__'):
                    field = line[len('__CGROUP__'):]; values[field] = []
                elif line.startswith('__MISSING__'):
                    field = None
                elif field:
                    if not all(part.isdigit() or part == 'max' or part.replace('_', '').isalnum() for part in line.split()):
                        raise RuntimeError('Unexpected cgroup counter format')
                    values[field].append(line)
            complete = result.returncode == 0 and set(values) == {'memory.current','memory.peak','memory.max','memory.events','cpu.stat'}
            snapshots[service] = {'status': 'PASS' if complete else 'UNKNOWN', 'values': values}
        report['cgroup'][label] = snapshots
    try:
        memory('before')
        code = "import runpy; runpy.run_path('mobile/scripts/crm_client_sql_diagnostic.py')['inside']()"
        result = run(compose+['exec', '-T', 'web', 'python', 'manage.py', 'shell', '-c', code], 40)
        rows = [line[len('SQL_RESULT '):] for line in result.stdout.splitlines() if line.startswith('SQL_RESULT ')]
        if result.returncode or len(rows) != 1:
            import re
            frames=re.findall(r'File "([^"\n]+)", line (\d+)',result.stderr)
            report['error'] = {'kind': 'InnerDiagnosticFailed', 'exitCode': result.returncode, 'resultCount': len(rows),
                               'frames':[{'file':Path(path).name,'line':int(line)} for path,line in frames[-12:]]}
        else:
            report['sql'] = json.loads(rows[0])
        memory('after')
        observed = all(v['status'] == 'PASS' for snap in report['cgroup'].values() for v in snap.values())
        report['status'] = 'PASS' if report['sql'] and report['sql']['status'] == 'PASS' and observed else 'FAIL'
    except Exception as error:
        report.update(status='BLOCKED', error={'kind': type(error).__name__})
    finally:
        report['elapsedSeconds'] = round(time.monotonic()-started, 3)
        if time.monotonic() > deadline:
            report.update(status='BLOCKED', deadlineExceeded=True)
        output.write_text(json.dumps(report, indent=2, default=str)+'\n')
        print(json.dumps(report, default=str), flush=True)
    return 0 if report['status'] == 'PASS' else 1


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--project', required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    raise SystemExit(host(args.project, args.output))
