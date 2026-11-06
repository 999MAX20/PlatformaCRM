import importlib.util
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

SPEC = importlib.util.spec_from_file_location('dev_local', Path(__file__).resolve().parents[1] / 'dev_local.py')
dev = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(dev)


class DevLaunchTests(unittest.TestCase):
    def setUp(self):
        self.service = dict(name='frontend', port=5173, marker='vite/bin/vite.js')

    def test_foreign_listener_is_rejected_before_starting_anything(self):
        snapshot = {'ports': [{'LocalPort': 5173, 'OwningProcess': 7}],
                    'processes': [{'ProcessId': 7, 'CreationDate': 'now', 'CommandLine': 'node elsewhere/vite/bin/vite.js'}]}
        with self.assertRaisesRegex(RuntimeError, 'unverified process'):
            dev.existing(self.service, snapshot, {})

    def test_pid_reuse_does_not_authorize_a_foreign_listener(self):
        process = {'ProcessId': 7, 'CreationDate': 'new', 'CommandLine': 'node vite/bin/vite.js'}
        self.assertFalse(dev.belongs(process, self.service, {'frontend': {'pid': 7, 'created': 'old'}}))
        self.assertTrue(dev.belongs(process, self.service, {'frontend': {'pid': 7, 'created': 'new'}}))

    def test_sibling_checkout_with_same_prefix_is_not_owned(self):
        process = {'ProcessId': 7, 'CreationDate': 'now', 'CommandLine': f'node {dev.ROOT}-other/frontend/node_modules/vite/bin/vite.js'}
        self.assertFalse(dev.belongs(process, self.service, {}))

    def test_python_reloader_must_have_a_canonical_ancestor(self):
        service = dict(name='backend', port=8000, marker='runserver')
        child = {'ProcessId': 8, 'ParentProcessId': 7, 'CreationDate': 'now', 'CommandLine': 'python manage.py runserver'}
        parent = {'ProcessId': 7, 'ParentProcessId': 0, 'CreationDate': 'before', 'CommandLine': f'{dev.ROOT}/.venv/Scripts/python.exe manage.py runserver'}
        snapshot = {'ports': [{'LocalPort': 8000, 'OwningProcess': 8}], 'processes': [parent, child]}
        self.assertEqual(dev.existing(service, snapshot, {})['ProcessId'], 8)

    def test_all_port_owners_must_match(self):
        process = {'ProcessId': 7, 'CreationDate': 'now', 'CommandLine': f'node {dev.ROOT}/frontend/node_modules/vite/bin/vite.js'}
        snapshot = {'ports': [{'LocalPort': 5173, 'OwningProcess': n} for n in [7, 99]], 'processes': [process]}
        with self.assertRaises(RuntimeError):
            dev.existing(self.service, snapshot, {})

    def test_readiness_failure_is_bounded(self):
        with patch.object(dev.time, 'sleep'), patch.object(dev.time, 'monotonic', side_effect=[0, 0, 2]):
            with self.assertRaisesRegex(RuntimeError, 'not ready'):
                dev.wait_until(lambda: False, 1, 'not ready')

    def test_exited_child_is_not_reported_as_started(self):
        with self.assertRaisesRegex(RuntimeError, 'Process exited'):
            dev.wait_until(lambda: True, 1, 'failed', alive=lambda: False)

    def test_launch_lock_rejects_concurrent_start_and_releases(self):
        with tempfile.TemporaryDirectory() as folder, patch.object(dev, 'STATE', Path(folder)):
            with dev.launch_lock():
                with self.assertRaisesRegex(RuntimeError, 'Another dev launch'):
                    with dev.launch_lock():
                        pass
            with dev.launch_lock():
                pass

    def test_diagnostic_output_never_leaks_probe_stderr_to_console(self):
        with tempfile.TemporaryDirectory() as folder, patch.object(dev, 'STATE', Path(folder)):
            result = subprocess.CompletedProcess([], 1, b'', b'private diagnostic')
            with patch.object(dev.subprocess, 'run', return_value=result):
                with self.assertRaises(RuntimeError) as caught:
                    dev.run_probe('health')
            self.assertNotIn('private diagnostic', str(caught.exception))

    def test_pending_schema_reports_partial_readiness_without_duplicate_start(self):
        process = {'ProcessId': 7, 'CreationDate': 'now', 'CommandLine': f'node {dev.ROOT}/frontend/node_modules/vite/bin/vite.js'}
        snapshot = {'ports': [{'LocalPort': 5173, 'OwningProcess': 7}], 'processes': [process]}
        with tempfile.TemporaryDirectory() as folder, patch.object(dev, 'STATE', Path(folder)), \
                patch.object(dev, 'specs', return_value=[self.service]), \
                patch.object(dev, 'inventory', return_value=snapshot), \
                patch.object(dev, 'run_probe', side_effect=[{'pending_migrations': ['branches.pending']}, {'worker': True}]), \
                patch.object(dev, 'http_status', side_effect=lambda url: 401 if '/api/' in url else 200), \
                patch.object(dev.subprocess, 'Popen') as launch, patch('builtins.print'):
            self.assertEqual(dev.start(), 2)
            launch.assert_not_called()


if __name__ == '__main__':
    unittest.main()
