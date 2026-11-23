from io import BytesIO
import socket
from unittest.mock import Mock, patch

from django.test import SimpleTestCase
from PIL import Image, PngImagePlugin

from .document_logo import capture_document_logo, normalize_document_logo, DocumentLogoUnavailable, MAX_LOGO_BYTES


class DocumentLogoTests(SimpleTestCase):
    def logo(self):
        output = BytesIO()
        metadata = PngImagePlugin.PngInfo()
        metadata.add_text("Private", "Synthetic metadata to strip")
        Image.new("RGBA", (80, 40), (0, 100, 80, 255)).save(output, format="PNG", pnginfo=metadata)
        return output.getvalue()

    def fetch(self, *, body=None, status=200, headers=None, addresses=None):
        body = self.logo() if body is None else body
        fields = {"Content-Type": "image/png", "Content-Length": str(len(body))} | (headers or {})
        response = Mock(status=status)
        response.getheader.side_effect = lambda key, default=None: fields.get(key, default)
        response.read1 = Mock(side_effect=BytesIO(body).read1)
        connection = Mock()
        connection.getresponse.return_value = response
        answers = [(socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_TCP, "", (value, 443))
                   for value in (addresses or ["93.184.216.34"])]
        with patch("apps.integrations.webhooks.socket.getaddrinfo", return_value=answers), \
             patch("apps.integrations.webhooks._PinnedHTTPSConnection", return_value=connection) as factory:
            result = capture_document_logo("https://clinic.example.test/logo.png?version=7")
        return result, factory, connection, response

    def test_public_https_pins_address_and_strips_metadata_without_patient_headers(self):
        result, factory, connection, _ = self.fetch()
        args, kwargs = factory.call_args
        self.assertEqual(args, ("clinic.example.test", 443, "93.184.216.34"))
        self.assertGreater(kwargs["timeout"], 0)
        self.assertLessEqual(kwargs["timeout"], 8)
        connection.request.assert_called_once_with("GET", "/logo.png?version=7",
            headers={"Accept": "image/png, image/jpeg", "Accept-Encoding": "identity"})
        connection.close.assert_called_once()
        with Image.open(BytesIO(result)) as image:
            self.assertEqual(image.size, (80, 40))
            self.assertNotIn("Private", image.info)
            self.assertEqual(image.getpixel((0, 0)), (0, 100, 80))

    def test_unsafe_urls_fail_before_connection_even_in_debug(self):
        for url in ("http://example.test/logo", "https://127.0.0.1/logo", "https://169.254.169.254/logo",
                    "https://localhost/logo", "https://user:password@example.test/logo", "https://example.test:8443/logo",
                    "https://example.test/logo#fragment", "https://example.test/logo\n", "file:///logo", None):
            with self.subTest(url=url), patch("apps.integrations.webhooks._PinnedHTTPSConnection") as connection:
                with self.assertRaises(DocumentLogoUnavailable) as error:
                    capture_document_logo(url)
                self.assertEqual(str(error.exception), "")
                connection.assert_not_called()

    def test_private_mixed_and_shared_network_dns_is_rejected(self):
        for addresses in (["10.0.0.1"], ["93.184.216.34", "192.168.1.1"], ["100.64.0.1"]):
            with self.subTest(addresses=addresses), self.assertRaises(DocumentLogoUnavailable):
                self.fetch(addresses=addresses)

    def test_redirects_nonimage_and_compressed_responses_are_not_used(self):
        for changes in ({"status": 302, "headers": {"Location": "http://127.0.0.1/private"}},
                        {"headers": {"Content-Type": "image/svg+xml"}}, {"headers": {"Content-Encoding": "gzip"}},
                        {"headers": {"Content-Length": "bad"}}, {"body": b"not an image"}):
            with self.subTest(changes=changes), self.assertRaises(DocumentLogoUnavailable):
                self.fetch(**changes)

    def test_size_limit_is_enforced_with_and_without_declared_length(self):
        for headers in ({}, {"Content-Length": None}, {"Content-Length": "10"}):
            with self.subTest(headers=headers), self.assertRaises(DocumentLogoUnavailable):
                self.fetch(body=b"x" * (MAX_LOGO_BYTES + 1), headers=headers)

    def test_missing_logo_never_fetches_and_invalid_images_fail(self):
        self.assertIsNone(capture_document_logo(""))
        for value in (b"", b"<svg/>", b"x" * (MAX_LOGO_BYTES + 1)):
            with self.assertRaises(DocumentLogoUnavailable):
                normalize_document_logo(value)

    def test_elapsed_resolution_budget_prevents_connection(self):
        with patch("apps.medical.document_logo.time.monotonic", side_effect=[0, 9]):
            with self.assertRaises(DocumentLogoUnavailable):
                self.fetch()
