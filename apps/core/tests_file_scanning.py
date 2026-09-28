from datetime import timedelta
import hashlib
from io import BytesIO
import tempfile
from unittest.mock import patch
from uuid import uuid4

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, SimpleTestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.businesses.models import Business, BusinessMember
from apps.clients.models import Client
from apps.core.antivirus import ScanResult, ScanUnavailable, scan_stream
from apps.core.file_scanning import scan_attachment, scan_due_attachments
from apps.core.models import AuditLog, FileAttachment


def clean_result(stream):
    data = stream.read()
    return ScanResult(True, hashlib.sha256(data).hexdigest(), len(data), "ClamAV test/1")


class FileQuarantineTests(TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.settings_override = override_settings(MEDIA_ROOT=self.temp.name, PRIVATE_MEDIA_ROOT=self.temp.name + "/private", USE_S3=False)
        self.settings_override.enable()
        self.addCleanup(self.settings_override.disable)
        self.api = APIClient()
        self.owner = User.objects.create_user(username="scan-owner", email="scan@example.test")
        self.business = Business.objects.create(owner=self.owner, name="Scan", slug="scan")
        BusinessMember.objects.create(business=self.business, user=self.owner, role="owner")
        self.client = Client.objects.create(business=self.business, full_name="Synthetic file client")
        self.api.force_authenticate(self.owner)

    def upload(self, body=b"safe synthetic text"):
        response = self.api.post("/api/file-attachments/", {
            "business": self.business.id, "entity_type": "client", "entity_id": self.client.id,
            "file": SimpleUploadedFile("note.txt", body, content_type="text/plain"),
            "scan_status": "clean", "scan_sha256": hashlib.sha256(body).hexdigest(),
        }, format="multipart")
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(response.data["scan_status"], "pending")
        self.assertEqual(response.data["download_url"], "")
        return FileAttachment.objects.get(pk=response.data["id"])

    def download(self, attachment):
        return self.api.get(f"/api/file-attachments/{attachment.id}/download/")

    def test_pending_blocks_api_and_legacy_even_if_client_forges_verdict(self):
        attachment = self.upload()
        self.assertEqual(self.download(attachment).status_code, 423)
        path = attachment.file.name.removeprefix("private/")
        self.assertEqual(self.api.get(f"/api/files/private/{path}/").status_code, 423)
        self.assertFalse(AuditLog.objects.filter(action=AuditLog.Actions.DOWNLOAD).exists())
        other = User.objects.create_user(username="scan-other", email="other@example.test")
        self.api.force_authenticate(other)
        self.assertEqual(self.download(attachment).status_code, 404)
        self.api.force_authenticate(None)
        self.assertEqual(self.download(attachment).status_code, 401)

    def test_admin_does_not_render_storage_urls_or_allow_manual_clean_verdict(self):
        from django.contrib.admin import site
        from django.test import RequestFactory, Client as DjangoClient
        from apps.core.models import ImportJob

        attachment = self.upload()
        self.owner.is_staff = True
        self.owner.is_superuser = True
        self.owner.save(update_fields=["is_staff", "is_superuser"])
        admin_client = DjangoClient()
        admin_client.force_login(self.owner)
        with patch.object(attachment.file.storage, "url", side_effect=AssertionError("Storage URL bypass")):
            response = admin_client.get(f"/admin/core/fileattachment/{attachment.pk}/change/")
        self.assertEqual(response.status_code, 200)
        request = RequestFactory().get("/admin/")
        request.user = self.owner
        file_admin = site._registry[FileAttachment]
        self.assertNotIn("file", file_admin.get_fields(request, attachment))
        self.assertFalse(file_admin.has_add_permission(request))
        self.assertFalse(file_admin.has_change_permission(request, attachment))
        self.assertNotIn("source_file", site._registry[ImportJob].get_fields(request))

    @patch("apps.core.file_scanning.scan_stream", side_effect=clean_result)
    def test_clean_and_duplicate_worker_deliver_verified_snapshot(self, scanner):
        attachment = self.upload()
        self.assertEqual(scan_attachment(attachment.id, self.business.id), "clean")
        self.assertIsNone(scan_attachment(attachment.id, self.business.id))
        self.assertEqual(scanner.call_count, 1)
        response = self.download(attachment)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(b"".join(response.streaming_content), b"safe synthetic text")
        self.assertEqual(response["Content-Type"], "text/plain")
        detail = self.api.get(f"/api/file-attachments/{attachment.id}/").data
        self.assertTrue(detail["download_url"])
        self.assertNotIn("scan_token", detail)
        self.assertEqual(AuditLog.objects.filter(metadata__kind="file_security_scan").count(), 1)

    def test_infected_is_not_retried_or_released_by_rename(self):
        attachment = self.upload()
        verdict = ScanResult(False, "a" * 64, attachment.size, "ClamAV test/1")
        with patch("apps.core.file_scanning.scan_stream", return_value=verdict):
            self.assertEqual(scan_attachment(attachment.id, self.business.id), "infected")
        self.api.post(f"/api/file-attachments/{attachment.id}/rename/", {"original_name": "safe.pdf"})
        self.assertEqual(self.download(attachment).status_code, 423)
        self.assertEqual(scan_due_attachments(), 0)
        attachment.refresh_from_db()
        self.assertEqual(attachment.scan_status, "infected")

    def test_failure_backoff_and_recovery_without_raw_error_leak(self):
        attachment = self.upload()
        with patch("apps.core.file_scanning.scan_stream", side_effect=OSError("secret signed URL token=do-not-log")):
            self.assertEqual(scan_attachment(attachment.id, self.business.id), "error")
        self.assertEqual(scan_due_attachments(), 0)
        self.assertEqual(self.download(attachment).status_code, 423)
        attachment.refresh_from_db()
        self.assertEqual(attachment.scan_error_code, "storage_unavailable")
        self.assertNotIn("do-not-log", str(list(AuditLog.objects.values("metadata"))))
        FileAttachment.objects.filter(pk=attachment.pk).update(scan_next_attempt_at=timezone.now() - timedelta(seconds=1))
        with patch("apps.core.file_scanning.scan_stream", side_effect=clean_result):
            self.assertEqual(scan_due_attachments(), 1)
        self.assertEqual(self.download(attachment).status_code, 200)

    def test_crashed_worker_reclaimed_and_stale_result_cannot_release_file(self):
        attachment = self.upload()
        def stale_scan(stream):
            self.assertIsNone(scan_attachment(attachment.id, self.business.id))
            FileAttachment.objects.filter(pk=attachment.pk).update(scan_token=uuid4())
            return clean_result(stream)
        with patch("apps.core.file_scanning.scan_stream", side_effect=stale_scan):
            self.assertIsNone(scan_attachment(attachment.id, self.business.id))
        self.assertEqual(self.download(attachment).status_code, 423)
        self.assertEqual(AuditLog.objects.filter(metadata__kind="file_security_scan").count(), 0)
        FileAttachment.objects.filter(pk=attachment.pk).update(scan_started_at=timezone.now() - timedelta(hours=1))
        with patch("apps.core.file_scanning.scan_stream", side_effect=clean_result):
            self.assertEqual(scan_due_attachments(), 1)
        self.assertEqual(self.download(attachment).status_code, 200)

    @patch("apps.core.file_scanning.scan_stream", side_effect=clean_result)
    def test_storage_replacement_returns_no_bytes_and_requarantines(self, scanner):
        attachment = self.upload()
        scan_attachment(attachment.id, self.business.id)
        with attachment.file.open("wb") as target:
            target.write(b"changed content")
        self.assertEqual(self.download(attachment).status_code, 423)
        attachment.refresh_from_db()
        self.assertEqual(attachment.scan_status, "error")
        self.assertEqual(attachment.scan_sha256, "")
        self.assertEqual(self.download(attachment).status_code, 423)
        self.assertEqual(AuditLog.objects.filter(metadata__kind="file_security_quarantine").count(), 1)

    @override_settings(USE_S3=True, STORAGES={"default": {"BACKEND": "django.core.files.storage.InMemoryStorage"}})
    @patch("apps.core.file_scanning.scan_stream", side_effect=clean_result)
    def test_storage_without_local_path_and_wrong_business_worker(self, scanner):
        attachment = self.upload()
        self.assertIsNone(scan_attachment(attachment.id, self.business.id + 123))
        self.assertEqual(scan_attachment(attachment.id, self.business.id), "clean")
        self.assertEqual(self.download(attachment).status_code, 200)


class ClamProtocolTests(SimpleTestCase):
    def connection(self, response):
        from unittest.mock import MagicMock
        sock = MagicMock()
        sock.__enter__.return_value = sock
        sock.recv.return_value = response
        return sock

    @patch("apps.core.antivirus.scanner_health", return_value="ClamAV test/1")
    def test_only_exact_clean_verdict_releases_stream(self, health):
        for reply, expected in [(b"stream: OK\0", True), (b"stream: Eicar FOUND\0", False)]:
            sock = self.connection(reply)
            with patch("apps.core.antivirus._connect", return_value=sock):
                result = scan_stream(BytesIO(b"hello"))
            self.assertEqual(result.clean, expected)
            self.assertEqual(result.sha256, hashlib.sha256(b"hello").hexdigest())
            self.assertEqual(sock.sendall.call_args_list[0].args[0], b"zINSTREAM\0")
            self.assertEqual(sock.sendall.call_args_list[-1].args[0], b"\0\0\0\0")

    @patch("apps.core.antivirus.scanner_health", return_value="ClamAV test/1")
    def test_error_truncation_oversized_reply_and_unknown_verdict_fail_closed(self, health):
        for reply in [b"stream: limit exceeded ERROR\0", b"", b"OK\0", b"stream: OK\0garbage", b"x" * 5000]:
            with self.subTest(reply=reply[:25]), patch("apps.core.antivirus._connect", return_value=self.connection(reply)):
                with self.assertRaises(ScanUnavailable):
                    scan_stream(BytesIO(b"hello"))

    def test_stale_database_prevents_file_transmission(self):
        sock = self.connection(b"ClamAV 1.5.4/123/Mon Jan  1 00:00:00 2001\0")
        with patch("apps.core.antivirus._connect", return_value=sock):
            with self.assertRaises(ScanUnavailable) as error:
                scan_stream(BytesIO(b"never transmit"))
        self.assertEqual(error.exception.code, "scanner_signatures_stale")
        self.assertEqual(sock.sendall.call_count, 1)

    @override_settings(MAX_UPLOAD_SIZE_MB=0)
    @patch("apps.core.antivirus.scanner_health", return_value="ClamAV test/1")
    def test_oversized_upload_is_not_reported_clean(self, health):
        with patch("apps.core.antivirus._connect", return_value=self.connection(b"stream: OK\0")):
            with self.assertRaises(ScanUnavailable) as error:
                scan_stream(BytesIO(b"x"))
        self.assertEqual(error.exception.code, "scan_size_limit")

    @patch("apps.core.antivirus.scanner_health", return_value="ClamAV test/1")
    def test_socket_timeout_never_returns_clean(self, health):
        sock = self.connection(b"stream: OK\0")
        sock.sendall.side_effect = TimeoutError()
        with patch("apps.core.antivirus._connect", return_value=sock), self.assertRaises(ScanUnavailable):
            scan_stream(BytesIO(b"hello"))


class ImportAntivirusTests(SimpleTestCase):
    def test_import_is_blocked_before_parser_on_infection_or_unavailability(self):
        from apps.core.import_export import read_tabular_file
        from rest_framework.exceptions import APIException, ValidationError
        from pathlib import Path
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "sample.csv"
            path.write_bytes(b"full_name\nSynthetic\n")
            with patch("apps.core.antivirus.scan_stream", return_value=ScanResult(False, "", 20, "test")):
                with self.assertRaises(ValidationError):
                    read_tabular_file(path)
            with patch("apps.core.antivirus.scan_stream", side_effect=ScanUnavailable("scanner_signatures_stale")):
                with self.assertRaises(APIException) as error:
                    read_tabular_file(path)
                self.assertEqual(error.exception.status_code, 503)
            with patch("apps.core.antivirus.scan_stream", side_effect=clean_result):
                self.assertEqual(read_tabular_file(path), [{"full_name": "Synthetic"}])
