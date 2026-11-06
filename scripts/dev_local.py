"""Start the existing Windows development stack without installing or migrating."""
import argparse
import contextlib
import json
import os
from pathlib import Path
import shutil
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
STATE = ROOT / 'output/local-dev'
PYTHON = ROOT / '.venv/Scripts/python.exe'
PS = shutil.which('pwsh') or shutil.which('powershell')


def powershell(script):
    result = subprocess.run([PS, '-NoProfile', '-Command', script], capture_output=True,
                            text=True, encoding='utf-8', errors='replace', timeout=25,
                            creationflags=subprocess.CREATE_NO_WINDOW)
    if result.returncode:
        raise RuntimeError('Cannot inspect Windows processes/listening ports.')
    return json.loads(result.stdout.strip() or 'null')


def inventory():
    return powershell("[Console]::OutputEncoding=[Text.UTF8Encoding]::new(); "
        "$p=@(Get-CimInstance Win32_Process | Select-Object ProcessId,ParentProcessId,CreationDate,CommandLine); "
        "$t=@(Get-NetTCPConnection -State Listen -ErrorAction SilentlyContinue | Select-Object LocalPort,OwningProcess); "
        "@{processes=$p;ports=$t}|ConvertTo-Json -Depth 4 -Compress")


def normalized(value):
    return str(value or '').replace('\\', '/').lower()


def belongs(process, spec, receipt):
    command = normalized(process.get('CommandLine'))
    if spec['marker'] not in command:
        return False
    known = receipt.get(spec['name'], {})
    same_instance = (known.get('pid') == process['ProcessId']
                     and known.get('created') == process['CreationDate'])
    return (normalized(ROOT) + '/' in command or same_instance)


def existing(spec, snapshot, receipt):
    processes = {p['ProcessId']: p for p in snapshot['processes']}
    if spec.get('port'):
        owners = {p['OwningProcess'] for p in snapshot['ports'] if p['LocalPort'] == spec['port']}
        if not owners:
            return None
        for owner in owners:
            process = processes.get(owner)
            verified = False
            for _ in range(16):
                if not process:
                    break
                if belongs(process, spec, receipt):
                    verified = True
                    break
                process = processes.get(process.get('ParentProcessId'))
            if not verified:
                raise RuntimeError(f"Port {spec['port']} is occupied by an unverified process. Nothing was stopped.")
        return processes[next(iter(owners))]
    return next((p for p in snapshot['processes'] if belongs(p, spec, receipt)), None)


def probe(mode):
    sys.path.insert(0, str(ROOT))
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
    import django
    django.setup()
    from django.conf import settings
    if mode == 'config':
        from urllib.parse import urlsplit
        from django.db import connections
        from django.db.migrations.executor import MigrationExecutor
        if settings.ENVIRONMENT not in {'local', 'development'}:
            raise RuntimeError('Development launch is disabled outside a local/development environment.')
        database = settings.DATABASES['default']
        if database['ENGINE'].endswith('sqlite3') and not Path(database['NAME']).is_file():
            raise RuntimeError('Working SQLite database is missing. No database was created.')
        broker = urlsplit(settings.CELERY_BROKER_URL)
        if (broker.scheme != 'redis' or broker.hostname not in {'localhost', '127.0.0.1', '::1'}
                or (broker.port or 6379) != 6379 or broker.username or broker.password
                or settings.CLAMD_HOST not in {'localhost', '127.0.0.1'} or settings.CLAMD_PORT != 3310
                or settings.CELERY_TASK_ALWAYS_EAGER):
            raise RuntimeError('This launcher requires local Redis6379, ClamAV3310 and non-eager Celery. Configuration was not changed.')
        executor = MigrationExecutor(connections['default'])
        pending = [f'{m.app_label}.{m.name}' for m, _ in executor.migration_plan(executor.loader.graph.leaf_nodes())]
        print(json.dumps({'pending_migrations': pending}))
    else:
        import redis
        from config.celery import app
        from apps.core.antivirus import scanner_health
        assert redis.Redis.from_url(settings.CELERY_BROKER_URL, socket_timeout=3).ping()
        scanner = scanner_health()
        workers = app.control.inspect(timeout=3).active_queues() or {}
        assert any(name.startswith('import-local@') and any(q['name'] == 'reports_exports' for q in queues)
                   for name, queues in workers.items()), 'Import worker is not responding on reports_exports'
        print(json.dumps({'scanner': scanner, 'redis': True, 'worker': True}))


def run_probe(mode):
    result = subprocess.run([str(PYTHON), str(Path(__file__).resolve()), '--probe', mode],
                            cwd=ROOT, capture_output=True, timeout=40)
    if result.returncode:
        (STATE / f'{mode}-probe.log').write_bytes(result.stderr)
        raise RuntimeError(f'{mode} check failed. See {STATE / (mode + "-probe.log")}')
    return json.loads(result.stdout.decode('utf-8').strip().splitlines()[-1])


def specs():
    redis = ROOT / 'output/crm-s04-20261014/deps/redis/Redis-7.4.9-Windows-x64-msys2/redis-server.exe'
    av = ROOT / 'output/local-file-antivirus'
    node = shutil.which('node')
    required = [PYTHON, redis, av / 'engine/clamd.exe', av / 'engine/freshclam.exe',
                av / 'clamd.conf', av / 'freshclam.conf', ROOT / 'frontend/node_modules/vite/bin/vite.js']
    missing = [str(p) for p in required if not p.is_file()]
    if missing or not node:
        raise RuntimeError('Missing local dependencies: ' + ', '.join(missing or ['node']) + '. No installation was attempted.')
    return [
        dict(name='redis', port=6379, marker='redis-server', cwd=ROOT / 'output/local-import-runtime',
             args=[str(redis), '--bind', '127.0.0.1', '::1', '--port', '6379', '--appendonly', 'yes']),
        dict(name='scanner', port=3310, marker='clamd.exe', cwd=ROOT,
             args=[str(av / 'engine/clamd.exe'), f'--config-file={av / "clamd.conf"}']),
        dict(name='updater', marker='freshclam.exe', cwd=ROOT,
             args=[str(av / 'engine/freshclam.exe'), f'--config-file={av / "freshclam.conf"}', '--daemon']),
        dict(name='worker', marker='--hostname=import-local@', cwd=ROOT,
             args=[str(PYTHON), '-m', 'celery', '-A', 'config', 'worker', '--pool=solo', '--concurrency=1',
                   '--queues=reports_exports', '--hostname=import-local@%h', '--without-gossip', '--without-mingle', '--loglevel=INFO']),
        dict(name='backend', port=8000, marker='runserver', cwd=ROOT,
             args=[str(PYTHON), str(ROOT / 'manage.py'), 'runserver', '127.0.0.1:8000']),
        dict(name='frontend', port=5173, marker='vite/bin/vite.js', cwd=ROOT / 'frontend',
             args=[node, str(ROOT / 'frontend/node_modules/vite/bin/vite.js'), '--host', '127.0.0.1', '--port', '5173', '--strictPort']),
    ]


def wait_until(check, seconds, message, alive=lambda: True):
    deadline = time.monotonic() + seconds
    while True:
        if not alive():
            raise RuntimeError(message + ' Process exited; inspect its log.')
        try:
            if check():
                return
        except (OSError, RuntimeError):
            pass
        if time.monotonic() >= deadline:
            raise RuntimeError(message)
        time.sleep(1)


def http_status(url):
    try:
        with urllib.request.urlopen(url, timeout=4) as response:
            return response.status
    except urllib.error.HTTPError as error:
        return error.code


@contextlib.contextmanager
def launch_lock():
    import msvcrt
    STATE.mkdir(parents=True, exist_ok=True)
    with (STATE / 'launch.lock').open('a+b') as stream:
        stream.seek(0); stream.write(b'0'); stream.flush(); stream.seek(0)
        try:
            msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
        except OSError:
            raise RuntimeError('Another dev launch is in progress. Wait for it to finish.') from None
        try:
            yield
        finally:
            stream.seek(0); msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)


def start():
    with launch_lock():
        plan = specs()
        config = run_probe('config')
        receipt_path = STATE / 'processes.json'
        receipt = json.loads(receipt_path.read_text()) if receipt_path.exists() else {}
        snapshot = inventory()
        for spec in plan:
            existing(spec, snapshot, receipt)
        for spec in plan:
            process = existing(spec, snapshot, receipt)
            if process:
                print(f"{spec['name']}: already running", flush=True)
                continue
            spec['cwd'].mkdir(parents=True, exist_ok=True)
            with (STATE / f"{spec['name']}.log").open('ab') as log:
                child = subprocess.Popen(spec['args'], cwd=spec['cwd'], stdout=log, stderr=subprocess.STDOUT,
                                         creationflags=subprocess.CREATE_NO_WINDOW)
            wait_until(lambda: existing(spec, inventory(), receipt), 90,
                       f"{spec['name']} did not start. Logs: {STATE}", lambda: child.poll() is None)
            process = existing(spec, inventory(), receipt)
            receipt[spec['name']] = {'pid': process['ProcessId'], 'created': process['CreationDate']}
            receipt_path.write_text(json.dumps(receipt, indent=2))
            snapshot = inventory()
            print(f"{spec['name']}: started", flush=True)
        wait_until(lambda: http_status('http://127.0.0.1:8000/health/') == 200
                   and http_status('http://127.0.0.1:5173/') == 200
                   and http_status('http://127.0.0.1:5173/api/auth/me/') == 401,
                   60, 'Frontend/backend/API proxy is not ready.')
        wait_until(lambda: bool(run_probe('health')), 90, f'Scanner/Redis/worker not ready. Logs: {STATE}')
        snapshot = inventory()
        for spec in plan:
            if not existing(spec, snapshot, receipt):
                raise RuntimeError(f"{spec['name']} exited during startup. Logs: {STATE}")
        print('Dev: http://127.0.0.1:5173/\nLogs: ' + str(STATE))
        if config['pending_migrations']:
            print('WARNING: unapplied migrations: ' + ', '.join(config['pending_migrations']))
            print('Services are running, but DB-dependent features may fail. No migration was applied.')
            return 2
        return 0


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--probe', choices=['config', 'health'], help=argparse.SUPPRESS)
    args = parser.parse_args()
    try:
        if args.probe:
            probe(args.probe)
        elif os.name != 'nt':
            raise RuntimeError('Use dev.ps1 on Windows.')
        else:
            raise SystemExit(start())
    except (OSError, RuntimeError, subprocess.TimeoutExpired, ValueError) as error:
        print('Dev startup failed: ' + str(error), file=sys.stderr)
        raise SystemExit(1)
