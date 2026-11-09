import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest

import redis

from scripts.codex_verify import find_available_port, safe_environment


ROOT = Path(__file__).resolve().parents[2]
PROBE = """
import os
os.environ['DJANGO_SETTINGS_MODULE'] = 'config.settings'
from types import SimpleNamespace
from rest_framework.throttling import ScopedRateThrottle
request = SimpleNamespace(user=SimpleNamespace(is_authenticated=False), META={'REMOTE_ADDR':'192.0.2.1'}, headers={})
view = SimpleNamespace(throttle_scope='auth_login')
print(ScopedRateThrottle().allow_request(request, view))
"""


class SharedAuthCacheTests(unittest.TestCase):
    @unittest.skipUnless(os.environ.get("TEST_REDIS_SERVER"), "Set TEST_REDIS_SERVER to run disposable Redis integration")
    def test_distinct_processes_share_quota_and_cache_outage_denies(self):
        port = find_available_port((6379,))
        with tempfile.TemporaryDirectory(prefix="platforma-auth-cache-") as directory:
            environment = safe_environment(database_path=Path(directory) / "db.sqlite3", python=sys.executable,
                                           django_port=8001, frontend_port=5174)
            environment.update(DJANGO_CACHE_URL=f"redis://127.0.0.1:{port}/0", AUTH_LOGIN_RATE="2/min")
            flags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
            process = subprocess.Popen([os.environ["TEST_REDIS_SERVER"], "--bind", "127.0.0.1", "--port", str(port),
                                        "--save", "", "--appendonly", "no", "--dir", directory],
                                       stdout=subprocess.PIPE, stderr=subprocess.STDOUT, creationflags=flags)
            connection = redis.Redis(host="127.0.0.1", port=port, socket_connect_timeout=1)
            try:
                for _ in range(15):
                    if process.poll() is not None:
                        self.fail(process.stdout.read().decode(errors="replace"))
                    try:
                        if connection.ping():
                            break
                    except (redis.ConnectionError, redis.TimeoutError):
                        time.sleep(0.1)
                else:
                    self.fail("Disposable Redis did not start")

                def probe():
                    return subprocess.run([sys.executable, "-c", PROBE], cwd=ROOT, env=environment,
                                          capture_output=True, text=True, timeout=30)

                for expected in ("True", "True", "False", "False"):
                    result = probe()
                    self.assertEqual(result.returncode, 0, result.stderr)
                    self.assertEqual(result.stdout.strip(), expected)
                keys = connection.keys("platforma:*throttle_auth_login*")
                self.assertEqual(len(keys), 1)
                connection.expire(keys[0], 1)
                time.sleep(1.1)
                self.assertEqual(probe().stdout.strip(), "True")
                process.terminate()
                process.wait(timeout=10)
                result = probe()
                self.assertNotEqual(result.returncode, 0)
                self.assertNotEqual(result.stdout.strip(), "True")
            finally:
                if process.poll() is None:
                    process.terminate()
                    process.wait(timeout=10)
                process.stdout.close()

    def test_production_rejects_process_local_cache(self):
        with tempfile.TemporaryDirectory() as directory:
            environment = safe_environment(database_path=Path(directory) / "db.sqlite3", python=sys.executable,
                                           django_port=8001, frontend_port=5174)
            environment.update(ENVIRONMENT="production", DJANGO_SETTINGS_MODULE="config.settings")
            result = subprocess.run([sys.executable, "-c", "from django.conf import settings; print(settings.CACHES)"],
                                    cwd=ROOT, env=environment, capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("require a shared Redis", result.stderr)

    def test_default_cache_uses_existing_redis_broker(self):
        with tempfile.TemporaryDirectory() as directory:
            environment = safe_environment(database_path=Path(directory) / "db.sqlite3", python=sys.executable,
                                           django_port=8001, frontend_port=5174)
            environment.pop("DJANGO_CACHE_URL")
            environment.update(REDIS_URL="redis://127.0.0.1:1234/0", DJANGO_SETTINGS_MODULE="config.settings")
            result = subprocess.run([sys.executable, "-c", "from django.conf import settings; print(settings.CACHES['default']['BACKEND']); print(settings.CACHES['default']['LOCATION'])"],
                                    cwd=ROOT, env=environment, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(result.stdout.splitlines(), ["django.core.cache.backends.redis.RedisCache", "redis://127.0.0.1:1234/0"])


if __name__ == "__main__":
    unittest.main()
