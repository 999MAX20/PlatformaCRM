import base64
import json
import hashlib
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import Mock, patch

import boto3
from botocore.stub import Stubber
from django.core.management import call_command, CommandError
from django.db import transaction
from django.test import TestCase, override_settings
from django.utils import timezone

from . import tests_patient_services as crypto
from . import tests_file_upload as fixtures
from .audit import MedicalAuditUnavailable, write_patient_audit
from .audit_reserve import ReserveReceipt, ReserveUnavailable, write_reserved_read
from .audit_reserve_recovery import recover_reserved_read
from .identity_crypto import decrypt_medical_value, encrypt_medical_value
from .models import MedicalAuditEvent


RESERVE = {"bucket": "synthetic-audit", "endpoint": "https://storage.yandexcloud.kz",
           "region": "kz", "access_key": "synthetic-key", "secret_key": "synthetic-secret",
           "kms_key_id": "synthetic-kms", "retention_days": 3}


@override_settings(MEDICAL_DATA_KEYS={"test": crypto.key(7)}, MEDICAL_DATA_ACTIVE_KEY_ID="test",
                   MEDICAL_IDENTITY_INDEX_KEY=crypto.key(8), MEDICAL_READ_AUDIT_RESERVE=RESERVE)
class MedicalAuditReserveTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        fixtures.MedicalFileUploadTests.setUpTestData.__func__(cls)

    def audit(self, **extra):
        return write_patient_audit(actor=self.doctor, business=self.business, patient=self.patient,
                                   action="read", **extra)

    def storage(self):
        client = Mock()
        def put(**options):
            self.saved = options
            return {"VersionId": "immutable-version", "ResponseMetadata": {"HTTPStatusCode": 200}}
        client.put_object.side_effect = put
        client.get_object_retention.side_effect = lambda **kwargs: {"Retention": {
            "Mode": "COMPLIANCE", "RetainUntilDate": self.saved["ObjectLockRetainUntilDate"]}}
        client.head_object.side_effect = lambda **kwargs: {"ServerSideEncryption": "aws:kms",
            "SSEKMSKeyId": "synthetic-kms", "ContentLength": len(self.saved["Body"]),
            "Metadata": self.saved["Metadata"]}
        return client

    def test_primary_success_never_contacts_reserve(self):
        with patch("apps.medical.audit_reserve.boto3.client") as factory:
            event = self.audit(record=self.record)
        self.assertIsInstance(event, MedicalAuditEvent)
        factory.assert_not_called()

    def reserved_object(self):
        with patch("apps.medical.audit.MedicalAuditEvent.objects.create", return_value=None), \
                patch("apps.medical.audit_reserve.boto3.client", return_value=self.storage()):
            receipt = self.audit(record=self.record)
        return receipt, self.saved["Body"]

    def test_offline_recovery_and_rotation_preserve_exact_event_without_database_changes(self):
        receipt, body = self.reserved_object()
        with override_settings(MEDICAL_DATA_KEYS={"test": crypto.key(7), "next": crypto.key(9)},
                               MEDICAL_DATA_ACTIVE_KEY_ID="next"), self.assertNumQueries(0):
            payload = recover_reserved_read(body, expected_event_id=receipt.event_id)
        self.assertEqual(payload["event_id"], receipt.event_id)
        self.assertEqual(payload["references"]["record_id"], self.record.pk)
        self.assertEqual(payload["result"], "authorized")
        with TemporaryDirectory() as directory:
            source = Path(directory) / "reserved.json"
            source.write_bytes(body)
            output = StringIO()
            with self.assertNumQueries(0):
                call_command("inspect_medical_read_audit", str(source), event_id=receipt.event_id, stdout=output)
            self.assertEqual(json.loads(output.getvalue()), payload)

    def test_recovery_rejects_tampering_wrong_context_wrong_key_and_unbounded_input(self):
        receipt, body = self.reserved_object()
        envelope = json.loads(body)
        for bad in (b"not json", b"x" * 16385,
                    json.dumps(envelope | {"business_id": self.business.pk + 1}).encode(),
                    json.dumps(envelope | {"patient_id": self.patient.pk + 1}).encode(),
                    json.dumps(envelope | {"encrypted_event": "invalid"}).encode(),
                    json.dumps(envelope | {"schema": True}).encode()):
            with self.subTest(length=len(bad)), self.assertRaises(ReserveUnavailable):
                recover_reserved_read(bad, expected_event_id=receipt.event_id)
        with self.assertRaises(ReserveUnavailable):
            recover_reserved_read(body, expected_event_id="00000000-0000-0000-0000-000000000000")
        with override_settings(MEDICAL_DATA_KEYS={"test": crypto.key(10)}), self.assertRaises(ReserveUnavailable):
            recover_reserved_read(body, expected_event_id=receipt.event_id)
        with TemporaryDirectory() as directory:
            source = Path(directory) / "invalid.json"
            source.write_bytes(b"invalid")
            output = StringIO()
            with self.assertRaises(CommandError):
                call_command("inspect_medical_read_audit", str(source), event_id=receipt.event_id, stdout=output)
            self.assertEqual(output.getvalue(), "")

    def test_storage_requests_match_real_sdk_contract_without_network(self):
        client = boto3.client("s3", endpoint_url=RESERVE["endpoint"], region_name="kz",
                              aws_access_key_id="synthetic", aws_secret_access_key="synthetic")
        event_id = "11111111-1111-4111-8111-111111111111"
        now = timezone.now()
        from datetime import timedelta
        until = now + timedelta(days=3)
        key = f"medical-read-audit/{now:%Y/%m/%d}/{event_id}.json"
        body = json.dumps({"schema": 1, "business_id": self.business.pk, "patient_id": self.patient.pk,
            "encrypted_event": "synthetic-encrypted"}, sort_keys=True, separators=(",", ":")).encode()
        metadata = {"sha256": hashlib.sha256(body).hexdigest()}
        target = {"Bucket": RESERVE["bucket"], "Key": key, "VersionId": "version1"}
        with Stubber(client) as stub:
            stub.add_response("put_object", {"VersionId": "version1", "ResponseMetadata": {"HTTPStatusCode": 200}},
                {"Bucket": RESERVE["bucket"], "Key": key, "Body": body, "ContentType": "application/json",
                 "ContentMD5": base64.b64encode(hashlib.md5(body).digest()).decode(),
                 "ServerSideEncryption": "aws:kms", "SSEKMSKeyId": RESERVE["kms_key_id"],
                 "ObjectLockMode": "COMPLIANCE", "ObjectLockRetainUntilDate": until, "Metadata": metadata})
            stub.add_response("get_object_retention", {"Retention": {"Mode": "COMPLIANCE", "RetainUntilDate": until}}, target)
            stub.add_response("head_object", {"ServerSideEncryption": "aws:kms", "SSEKMSKeyId": RESERVE["kms_key_id"],
                "ContentLength": len(body), "Metadata": metadata}, target)
            with patch("apps.medical.audit_reserve.boto3.client", return_value=client), \
                    patch("apps.medical.audit_reserve.uuid.uuid4", return_value=event_id), \
                    patch("apps.medical.audit_reserve.timezone.now", return_value=now), \
                    patch("apps.medical.audit_reserve.encrypt_medical_value", return_value="synthetic-encrypted"), \
                    patch("apps.medical.audit.MedicalAuditEvent.objects.create", return_value=None):
                receipt = self.audit(record=self.record)
            self.assertEqual(receipt, ReserveReceipt(event_id, "version1"))
            stub.assert_no_pending_responses()
        client.close()

    def test_recovery_rejects_authenticated_but_invalid_event_schema(self):
        receipt, body = self.reserved_object()
        envelope = json.loads(body)
        payload = recover_reserved_read(body, expected_event_id=receipt.event_id)
        for change in ({"result": "success"}, {"action": "file_downloaded"}, {"schema": True},
                       {"occurred_at": "2026-11-23T12:00:00"},
                       {"references": payload["references"] | {"actor_id": True}},
                       {"references": payload["references"] | {"business_id": self.business.pk + 1}},
                       {"references": payload["references"] | {"clinical_text": "forbidden"}}):
            encrypted = encrypt_medical_value(json.dumps(payload | change), business_id=self.business.pk,
                subject_id=self.patient.pk, purpose="read_audit_reserve")
            changed_body = json.dumps(envelope | {"encrypted_event": encrypted}).encode()
            with self.subTest(change=list(change)), self.assertRaises(ReserveUnavailable):
                recover_reserved_read(changed_body, expected_event_id=receipt.event_id)

    def test_real_database_error_rolls_back_savepoint_and_protects_exact_read_evidence(self):
        original = MedicalAuditEvent.objects.create
        def broken_insert(**fields):
            return original(**(fields | {"action": None}))
        client = self.storage()
        with transaction.atomic(), patch("apps.medical.audit.MedicalAuditEvent.objects.create", side_effect=broken_insert), \
                patch("apps.medical.audit_reserve.boto3.client", return_value=client):
            receipt = self.audit(record=self.record)
            self.assertTrue(type(self.patient).objects.filter(pk=self.patient.pk).exists())
        self.assertIsInstance(receipt, ReserveReceipt)
        self.assertFalse(MedicalAuditEvent.objects.filter(action="read").exists())
        envelope = json.loads(self.saved["Body"])
        self.assertEqual(envelope["business_id"], self.business.pk)
        self.assertEqual(envelope["patient_id"], self.patient.pk)
        payload = json.loads(decrypt_medical_value(envelope["encrypted_event"],
            business_id=self.business.pk, subject_id=self.patient.pk, purpose="read_audit_reserve"))
        self.assertEqual(payload["result"], "authorized")
        self.assertEqual(payload["references"]["record_id"], self.record.pk)
        self.assertEqual(payload["references"]["patient_revision"], self.patient.revision)
        self.assertEqual(payload["references"]["actor_id"], self.doctor.pk)
        self.assertNotIn(b"record_id", self.saved["Body"])
        client.head_object.assert_called_once_with(Bucket="synthetic-audit", Key=self.saved["Key"], VersionId="immutable-version")

    def test_missing_configuration_blocks_read_without_network(self):
        with override_settings(MEDICAL_READ_AUDIT_RESERVE=""), \
                patch("apps.medical.audit.MedicalAuditEvent.objects.create", return_value=None), \
                patch("apps.medical.audit_reserve.boto3.client") as factory:
            with self.assertRaises(MedicalAuditUnavailable):
                self.audit()
        factory.assert_not_called()

    def test_unconfirmed_lock_encryption_or_version_blocks_read(self):
        for defect in ("governance", "short_retention", "encryption", "size", "hash", "version", "provider"):
            with self.subTest(defect=defect):
                client = self.storage()
                if defect == "governance":
                    client.get_object_retention.side_effect = lambda **kwargs: {"Retention": {"Mode": "GOVERNANCE"}}
                elif defect == "short_retention":
                    client.get_object_retention.side_effect = lambda **kwargs: {"Retention": {"Mode": "COMPLIANCE", "RetainUntilDate": self.patient.created_at}}
                elif defect in {"encryption", "size", "hash"}:
                    valid_head = client.head_object.side_effect
                    override = {"encryption": {"SSEKMSKeyId": "wrong-key"}, "size": {"ContentLength": 0},
                                "hash": {"Metadata": {"sha256": "wrong"}}}[defect]
                    client.head_object.side_effect = lambda **kwargs: valid_head(**kwargs) | override
                elif defect == "version":
                    client.put_object.side_effect = None
                    client.put_object.return_value = {"VersionId": "null", "ResponseMetadata": {"HTTPStatusCode": 200}}
                else:
                    client.put_object.side_effect = RuntimeError("synthetic secret provider failure")
                with patch("apps.medical.audit.MedicalAuditEvent.objects.create", return_value=None), \
                        patch("apps.medical.audit_reserve.boto3.client", return_value=client):
                    with self.assertRaises(MedicalAuditUnavailable) as error:
                        self.audit()
                self.assertNotIn("synthetic secret", str(error.exception))

    def test_write_failure_never_uses_reserve(self):
        with patch("apps.medical.audit.MedicalAuditEvent.objects.create", return_value=None), \
                patch("apps.medical.audit_reserve.write_reserved_read") as reserve:
            with self.assertRaises(MedicalAuditUnavailable):
                write_patient_audit(actor=self.doctor, business=self.business, patient=self.patient,
                                    action="record_opened", record=self.record)
        reserve.assert_not_called()

    def test_invalid_entity_reference_never_uses_reserve(self):
        with patch("apps.medical.audit_reserve.write_reserved_read") as reserve:
            with self.assertRaises(ValueError):
                self.audit(record=Mock(pk=9999999))
        reserve.assert_not_called()

    def test_reserve_rejects_non_read_actions(self):
        with patch("apps.medical.audit_reserve.boto3.client") as factory:
            with self.assertRaises(ReserveUnavailable):
                write_reserved_read({"action": "file_downloaded", "result": "success"})
        factory.assert_not_called()

    def test_invalid_reserve_config_or_missing_crypto_key_never_contacts_storage(self):
        for config in (RESERVE | {"retention_days": 0}, RESERVE | {"retention_days": True},
                       RESERVE | {"endpoint": "http://storage.yandexcloud.kz"},
                       RESERVE | {"endpoint": "https://storage.yandexcloud.net"}):
            with self.subTest(config=config["endpoint"]), override_settings(MEDICAL_READ_AUDIT_RESERVE=config), \
                    patch("apps.medical.audit.MedicalAuditEvent.objects.create", return_value=None), \
                    patch("apps.medical.audit_reserve.boto3.client") as factory:
                with self.assertRaises(MedicalAuditUnavailable):
                    self.audit()
                factory.assert_not_called()
        with override_settings(MEDICAL_DATA_KEYS={}), \
                patch("apps.medical.audit.MedicalAuditEvent.objects.create", return_value=None), \
                patch("apps.medical.audit_reserve.boto3.client") as factory:
            with self.assertRaises(MedicalAuditUnavailable):
                self.audit()
            factory.assert_not_called()
