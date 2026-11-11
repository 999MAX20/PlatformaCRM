from email.message import Message
from http.cookiejar import CookieJar
from pathlib import Path
import sys
import tempfile
import unittest
from urllib.request import Request

from scripts.codex_verify import safe_environment


class CookieNamespaceTests(unittest.TestCase):
    def setUp(self):
        self.jar = CookieJar()

    def receive(self, port, name, value, *, delete=False):
        headers = Message()
        headers.add_header("Set-Cookie", f"{name}={value}; Path=/api/auth/; HttpOnly; SameSite=Lax" + ("; Max-Age=0" if delete else ""))

        class Response:
            def info(self):
                return headers

        self.jar.extract_cookies(Response(), Request(f"http://127.0.0.1:{port}/api/auth/token/"))

    def sent(self, port):
        request = Request(f"http://127.0.0.1:{port}/api/auth/token/refresh/")
        self.jar.add_cookie_header(request)
        return request.get_header("Cookie", "")

    def test_different_ports_do_not_isolate_the_legacy_cookie(self):
        self.receive(18001, "zani_refresh", "first")
        self.assertIn("zani_refresh=first", self.sent(18002))
        self.receive(18002, "zani_refresh", "second")
        self.assertIn("zani_refresh=second", self.sent(18001))
        self.assertNotIn("zani_refresh=first", self.sent(18001))

    def test_namespaced_rotation_and_deletion_preserve_default_and_other_runs(self):
        path = Path(tempfile.gettempdir())
        environments = [safe_environment(database_path=path / name / "gate.sqlite3", python=sys.executable,
                                         django_port=18001 + i, frontend_port=19001 + i, base={})
                        for i, name in enumerate(("run-a", "run-b"))]
        for key, default in (("AUTH_REFRESH_COOKIE_NAME", "zani_refresh"),
                             ("CSRF_COOKIE_NAME", "csrftoken"), ("SESSION_COOKIE_NAME", "sessionid")):
            with self.subTest(cookie=key):
                first, second = [env[key] for env in environments]
                self.receive(18000, default, "working")
                self.receive(18001, first, "first")
                self.receive(18002, second, "second")
                self.receive(18001, first, "rotated")
                self.assertIn(f"{default}=working", self.sent(18000))
                self.assertIn(f"{second}=second", self.sent(18002))
                self.assertIn(f"{first}=rotated", self.sent(18001))
                self.receive(18001, first, "", delete=True)
                self.assertNotIn(f"{first}=", self.sent(18001))
                self.assertIn(f"{default}=working", self.sent(18000))
                self.assertIn(f"{second}=second", self.sent(18002))


if __name__ == "__main__":
    unittest.main()
