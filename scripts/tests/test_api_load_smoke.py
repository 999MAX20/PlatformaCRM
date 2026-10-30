import io
import unittest
from unittest.mock import Mock, patch

from scripts import api_load_smoke


class AuthenticatedSmokeTests(unittest.TestCase):
    def test_cookie_opener_and_csrf_headers_are_used_for_login(self):
        response = Mock()
        response.__enter__ = Mock(return_value=response)
        response.__exit__ = Mock(return_value=False)
        response.read.return_value = b'{"access":"synthetic"}'
        opener = Mock()
        opener.open.return_value = response
        _, data = api_load_smoke.request_json("POST", "https://crm.example.invalid/api/auth/token/",
                                              payload={"email": "synthetic@example.invalid"},
                                              opener=opener, csrf_token="masked-token")
        request = opener.open.call_args.args[0]
        self.assertEqual(request.get_header("Origin"), "https://crm.example.invalid")
        self.assertEqual(request.get_header("X-csrftoken"), "masked-token")
        self.assertEqual(data["access"], "synthetic")

    def test_missing_bootstrap_token_stops_before_sending_credentials(self):
        argv = ["smoke", "--api-base-url", "https://crm.example.invalid", "--email", "synthetic@example.invalid", "--password", "synthetic"]
        with patch("sys.argv", argv), patch.object(api_load_smoke, "request_json", return_value=(1, {})) as request:
            with self.assertRaisesRegex(SystemExit, "CSRF token"):
                api_load_smoke.main()
        self.assertEqual(request.call_count, 1)
        self.assertEqual(request.call_args.args, ("GET", "https://crm.example.invalid/api/auth/csrf/"))

    def test_login_reuses_bootstrap_cookie_opener(self):
        argv = ["smoke", "--api-base-url", "https://crm.example.invalid", "--email", "synthetic@example.invalid", "--password", "synthetic", "--iterations", "0"]
        with patch("sys.argv", argv), patch("sys.stdout", new_callable=io.StringIO), patch.object(api_load_smoke, "request_json", side_effect=[(1, {"csrf_token": "masked"}), (1, {"access": "synthetic"})]) as request:
            api_load_smoke.main()
        bootstrap, login = request.call_args_list
        self.assertIs(bootstrap.kwargs["opener"], login.kwargs["opener"])
        self.assertEqual(login.kwargs["csrf_token"], "masked")
