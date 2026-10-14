"""Real export/ClamAV processing and restored-data assertions for S04."""
import hashlib
import json
from io import BytesIO
import os
from pathlib import Path
import socket
import shutil
import subprocess

from scripts.recovery_runtime import HIDDEN, stop_process
from scripts.recovery_scenarios import report

BLOCKED_FIXTURE = b"S04 harmless custom quarantine fixture"


class Scanner:
    def __init__(self, directory):
        self.directory = directory
        self.process = None
        self.log = (directory / "clamd.log").open("a", encoding="utf-8")
        self.config = directory / "clamd.conf"
        signature_copy = directory / "scan-db"
        shutil.copytree(Path(os.environ["S04_SIGNATURES"]), signature_copy)
        (signature_copy / "s04.ndb").write_text(
            f"S04.Synthetic.Quarantine:0:*:{BLOCKED_FIXTURE.hex()}\n", encoding="ascii")
        self.config.write_text(
            f"DatabaseDirectory {signature_copy}\nTCPAddr 127.0.0.1\n"
            f"TCPSocket {os.environ['CLAMD_PORT']}\nForeground yes\nMaxThreads 2\n"
            f"TemporaryDirectory {directory}\nStreamMaxLength 12M\n", encoding="utf-8")

    def start(self, wait_until):
        self.process = subprocess.Popen([os.environ["S04_CLAMD"], f"--config-file={self.config}"],
                                        stdout=self.log, stderr=subprocess.STDOUT, creationflags=HIDDEN)
        def ready():
            if self.process.poll() is not None:
                raise RuntimeError("Owned ClamD exited")
            try:
                with socket.create_connection(("127.0.0.1", int(os.environ["CLAMD_PORT"])), timeout=1) as sock:
                    sock.sendall(b"zPING\0")
                    return sock.recv(64) == b"PONG\0"
            except OSError:
                return False
        wait_until(ready, "owned ClamD startup", timeout=90)

    def stop(self):
        stop_process(self.process)

    def close(self):
        self.stop()
        self.log.close()


def content(response, status=200):
    assert response.status_code == status, response.status_code
    data = b"".join(response.streaming_content)
    response.close()
    return data


def file_drill(app, directory, worker, business, owner, dispatch, wait_until):
    from django.core.files.uploadedfile import SimpleUploadedFile
    from django.utils import timezone
    from rest_framework.test import APIClient
    from apps.accounts.models import User
    from apps.businesses.models import BusinessMember
    from apps.clients.models import Client
    from apps.core.antivirus import scanner_health, scan_stream
    from apps.core.models import ExportJob, FileAttachment

    api = APIClient()
    api.force_authenticate(owner)
    client = Client.objects.create(business=business, full_name="S04 exported client one")
    Client.objects.create(business=business, full_name="S04 exported client two")
    response = api.get("/api/export/clients/", {"business": business.pk})
    assert response.status_code == 202, response.status_code
    export = ExportJob.objects.get(pk=response.data["id"])
    dispatch(app, "exports.process_job", args=[export.pk], queue="reports_exports")
    export.refresh_from_db()
    assert export.status == "succeeded" and export.row_count == 2
    export_name = export.result_file.name
    export_bytes = content(api.get(f"/api/export-jobs/{export.pk}/download/"))
    assert b"S04 exported client one" in export_bytes and b"S04 exported client two" in export_bytes
    dispatch(app, "exports.process_job", args=[export.pk], queue="reports_exports")
    export.refresh_from_db()
    assert export.result_file.name == export_name

    # Revoke access while queued, then let a real worker recheck current rights.
    worker.stop()
    admin = User.objects.create_user(username="s04-export-admin", email="s04-export-admin@example.invalid")
    member = BusinessMember.objects.create(business=business, user=admin, role="admin")
    api.force_authenticate(admin)
    response = api.get("/api/export/clients/", {"business": business.pk})
    assert response.status_code == 202, response.status_code
    revoked = ExportJob.objects.get(pk=response.data["id"])
    member.is_active = False
    member.save(update_fields=["is_active"])
    worker.start()
    dispatch(app, "exports.process_job", args=[revoked.pk], queue="reports_exports")
    revoked.refresh_from_db()
    assert revoked.status == "failed" and not revoked.result_file
    assert api.get(f"/api/export-jobs/{export.pk}/download/").status_code == 404
    api.force_authenticate(owner)
    report(real_export_queue="pass", export_replay="pass", revoked_export_access="pass")

    scanner = Scanner(directory)
    try:
        def upload(body, name):
            response = api.post("/api/file-attachments/", {"business": business.pk,
                "entity_type": "client", "entity_id": client.pk,
                "file": SimpleUploadedFile(name, body, content_type="text/plain")}, format="multipart")
            assert response.status_code == 201, response.data
            attachment = FileAttachment.objects.get(pk=response.data["id"])
            assert api.get(f"/api/file-attachments/{attachment.pk}/download/").status_code == 423
            return attachment

        attachment = upload(b"S04 private bytes preserved after restore", "synthetic.txt")
        dispatch(app, "files.scan_due_attachments", queue="file_scans")
        attachment.refresh_from_db()
        assert attachment.scan_status == "error" and attachment.scan_next_attempt_at
        assert api.get(f"/api/file-attachments/{attachment.pk}/download/").status_code == 423
        scanner.start(wait_until)
        engine = scanner_health()  # Includes the unchanged 72-hour signature rule.
        FileAttachment.objects.filter(pk=attachment.pk).update(scan_next_attempt_at=timezone.now())
        dispatch(app, "files.scan_due_attachments", queue="file_scans")
        attachment.refresh_from_db()
        assert attachment.scan_status == "clean" and attachment.scan_attempts == 2
        body = content(api.get(f"/api/file-attachments/{attachment.pk}/download/"))
        assert hashlib.sha256(body).hexdigest() == attachment.scan_sha256
        dispatch(app, "files.scan_due_attachments", queue="file_scans")
        attachment.refresh_from_db()
        assert attachment.scan_attempts == 2

        # Standard harmless antivirus test string, never executable malware.
        eicar = b"X5O!P%@AP[4\\PZX54(P^)7CC)7}$EICAR-STANDARD-ANTIVIRUS-TEST-FILE!$H+H*"
        # Keep EICAR in memory so the host antivirus cannot remove our fixture
        # before the application worker reads it. The custom harmless signature
        # separately exercises the real file/queue/download quarantine path.
        assert not scan_stream(BytesIO(eicar)).clean
        blocked = upload(BLOCKED_FIXTURE, "quarantine-test.txt")
        dispatch(app, "files.scan_due_attachments", queue="file_scans")
        blocked.refresh_from_db()
        assert blocked.scan_status == "infected", (blocked.scan_status, blocked.scan_error_code)
        assert api.get(f"/api/file-attachments/{blocked.pk}/download/").status_code == 423
        api.force_authenticate(User.objects.get(username="s04-other"))
        assert api.get(f"/api/file-attachments/{attachment.pk}/download/").status_code == 404
        assert api.get(f"/api/export-jobs/{export.pk}/download/").status_code == 404
        report(real_file_scan_queue="pass", scanner_outage_recovery="pass", quarantine="pass", engine=engine)
        return {"attachment_id": attachment.pk, "export_id": export.pk, "body_sha256": attachment.scan_sha256,
                "export_sha256": hashlib.sha256(export_bytes).hexdigest(), "blocked_id": blocked.pk}
    finally:
        scanner.close()


def prepare_restore_manifest(directory, business, owner, files):
    from apps.integrations.models import BusinessConnector, ConnectorCredential
    from apps.integrations.credential_encryption import encrypt_credential_value
    from apps.tasks.models import Task, TaskReminderDelivery
    connector = BusinessConnector.objects.create(business=business, provider="manual", name="Synthetic key restore")
    credential = ConnectorCredential.objects.create(business=business, connector=connector, key="synthetic",
        encrypted_value=encrypt_credential_value("s04-non-production-credential"), masked_value="synthetic")
    manifest = {**files, "business_id": business.pk, "owner_id": owner.pk, "credential_id": credential.pk,
                "task_count": Task.objects.filter(business=business).count(),
                "reminder_count": TaskReminderDelivery.objects.filter(task__business=business).count()}
    (directory / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")


def verify_restored(directory):
    from django.conf import settings
    from django.db import connection
    from django.test import override_settings
    from rest_framework.test import APIClient
    from apps.accounts.models import User
    from apps.core.models import FileAttachment
    from apps.tasks.models import Task, TaskReminderDelivery
    from apps.integrations.models import ConnectorCredential
    from apps.integrations.credential_encryption import decrypt_connector_credential, CredentialKeyConfigurationError
    assert settings.DATABASES["default"]["NAME"] == "s04_restored"
    manifest = json.loads((directory / "manifest.json").read_text(encoding="utf-8"))
    assert Task.objects.filter(business_id=manifest["business_id"]).count() == manifest["task_count"]
    assert TaskReminderDelivery.objects.filter(task__business_id=manifest["business_id"]).count() == manifest["reminder_count"]
    credential = ConnectorCredential.objects.get(pk=manifest["credential_id"])
    assert credential.business_id == credential.connector.business_id == manifest["business_id"]
    assert decrypt_connector_credential(credential) == "s04-non-production-credential"
    with override_settings(CONNECTOR_CREDENTIAL_KEYS="{}"):
        try:
            decrypt_connector_credential(credential)
        except CredentialKeyConfigurationError:
            pass
        else:
            raise AssertionError("Restore without its encryption key must fail closed")
    api = APIClient()
    api.force_authenticate(User.objects.get(pk=manifest["owner_id"]))
    file_url = f"/api/file-attachments/{manifest['attachment_id']}/download/"
    assert hashlib.sha256(content(api.get(file_url))).hexdigest() == manifest["body_sha256"]
    assert hashlib.sha256(content(api.get(f"/api/export-jobs/{manifest['export_id']}/download/"))).hexdigest() == manifest["export_sha256"]
    assert api.get(f"/api/file-attachments/{manifest['blocked_id']}/download/").status_code == 423
    api.force_authenticate(User.objects.get(username="s04-other"))
    assert api.get(file_url).status_code == 404
    attachment = FileAttachment.objects.get(pk=manifest["attachment_id"])
    # Restored bytes must still pass the same integrity gate.
    Path(attachment.file.path).write_bytes(b"synthetic corruption")
    api.force_authenticate(User.objects.get(pk=manifest["owner_id"]))
    assert api.get(file_url).status_code == 423
    connection.check_constraints()
    report(postgres_restore="pass", private_file_restore="pass", restored_access="pass",
           restored_integrity="pass", encryption_key_restore="pass", tenant_relations="pass")
