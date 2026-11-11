import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from scripts.browser_test_runtime import browser_environment, ROOT
from scripts.codex_verify import safe_environment


class BrowserRuntimeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="zani-quality-gate-")
        self.addCleanup(self.temp.cleanup)
        self.directory = Path(self.temp.name)
        self.env = safe_environment(database_path=self.directory / "gate.sqlite3", python=sys.executable,
                                    django_port=18741, frontend_port=18742)

    def test_invalid_profile_has_no_side_effects(self):
        for patch in ({"DATABASE_URL": "sqlite:///db.sqlite3"}, {"ZANI_QUALITY_GATE": "0"},
                      {"E2E_DJANGO_PORT": "8000"}, {"E2E_BASE_URL": "https://example.invalid"}):
            with self.subTest(patch=patch), self.assertRaises(RuntimeError):
                browser_environment({**self.env, **patch})
        self.assertEqual(list(self.directory.iterdir()), [])

    def test_safe_provider_settings_and_stable_disposable_key(self):
        env = browser_environment({**self.env, "OPENAI_API_KEY": "must-drop", "EMAIL_HOST": "remote.invalid",
                                   "DJANGO_SETTINGS_MODULE": "unsafe.settings"})
        self.assertNotEqual(env.get("OPENAI_API_KEY"), "must-drop")
        self.assertEqual(env["EMAIL_HOST"], "")
        self.assertEqual(env["DJANGO_SETTINGS_MODULE"], "config.settings")
        self.assertEqual(Path(env["MEDIA_ROOT"]), self.directory / "media")
        self.assertEqual(env["CONNECTOR_CREDENTIAL_KEYS"], browser_environment(self.env)["CONNECTOR_CREDENTIAL_KEYS"])
        for name in ("AUTH_REFRESH_COOKIE_NAME", "CSRF_COOKIE_NAME", "SESSION_COOKIE_NAME"):
            self.assertEqual(env[name], self.env[name])
            self.assertEqual(browser_environment({**self.env, name: "working-cookie"})[name], env[name])

    def test_dotenv_and_external_network_disabled_before_django(self):
        code = '''
import environ, socket, json
from scripts.browser_test_runtime import configure_browser_runtime
def forbidden(*args, **kwargs):
    raise AssertionError("working dotenv was read")
environ.Env.read_env = forbidden
configure_browser_runtime()
import django
django.setup()
from django.conf import settings
for method in ("connect", "connect_ex"):
    with socket.socket() as connection:
        try:
            getattr(connection, method)(("192.0.2.1", 443))
        except RuntimeError:
            pass
        else:
            raise AssertionError("external network allowed")
print(json.dumps({"database": settings.DATABASES["default"]["NAME"],
    "cookies": {key: getattr(settings, key) for key in (
        "AUTH_REFRESH_COOKIE_NAME", "CSRF_COOKIE_NAME", "SESSION_COOKIE_NAME")},
    "access_seconds": settings.SIMPLE_JWT["ACCESS_TOKEN_LIFETIME"].total_seconds(),
    "refresh_seconds": settings.SIMPLE_JWT["REFRESH_TOKEN_LIFETIME"].total_seconds()}))
'''
        result = subprocess.run([sys.executable, "-c", code], cwd=ROOT, env=self.env, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(Path(json.loads(result.stdout.strip().splitlines()[-1])["database"]), self.directory / "gate.sqlite3")
        data = json.loads(result.stdout.strip().splitlines()[-1])
        self.assertEqual(data["cookies"], {key: self.env[key] for key in data["cookies"]})
        self.assertEqual(data["access_seconds"], 15 * 60)
        self.assertEqual(data["refresh_seconds"], 7 * 24 * 60 * 60)

    def test_direct_python_entrypoints_refuse_ordinary_database(self):
        for entry in ("scripts/browser_test_runtime.py", "frontend/e2e/serve-isolated.py"):
            result = subprocess.run([sys.executable, entry, "prepare"], cwd=ROOT,
                                    env={**self.env, "DATABASE_URL": "sqlite:///db.sqlite3"}, capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("no setup performed", result.stderr)
            self.assertNotIn("Applying ", result.stdout)


if __name__ == "__main__":
    unittest.main()
