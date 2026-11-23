import base64
from dataclasses import dataclass
from datetime import timedelta
import hashlib
import json
import uuid

import boto3
from botocore.config import Config
from django.conf import settings
from django.utils import timezone

from .identity_crypto import encrypt_medical_value


class ReserveUnavailable(Exception):
    pass


@dataclass(frozen=True)
class ReserveReceipt:
    event_id: str
    version_id: str


def reserve_configuration():
    value = getattr(settings, "MEDICAL_READ_AUDIT_RESERVE", "")
    try:
        config = json.loads(value) if isinstance(value, str) else value
        required = {"bucket", "endpoint", "region", "access_key", "secret_key", "kms_key_id", "retention_days"}
        if not isinstance(config, dict) or set(config) != required:
            raise ValueError
        if any(not isinstance(config[key], str) or not config[key].strip() for key in required - {"retention_days"}):
            raise ValueError
        if config["endpoint"] != "https://storage.yandexcloud.kz":
            raise ValueError
        if type(config["retention_days"]) is not int or not 1 <= config["retention_days"] <= 36500:
            raise ValueError
        if config["bucket"] == getattr(settings, "AWS_STORAGE_BUCKET_NAME", None):
            raise ValueError
        if config["access_key"] == getattr(settings, "AWS_ACCESS_KEY_ID", None):
            raise ValueError
        return config
    except (TypeError, ValueError):
        raise ReserveUnavailable() from None


def write_reserved_read(fields):
    """A receipt confirms durable authorization evidence, not delivery to the browser."""
    try:
        config = reserve_configuration()
        if fields["action"] != "read" or fields["result"] != "success":
            raise ReserveUnavailable()
        now = timezone.now()
        event_id = str(uuid.uuid4())
        until = now + timedelta(days=config["retention_days"])
        # Only audit identifiers/revisions enter this envelope, never clinical text.
        references = {}
        for name, value in fields.items():
            if name in {"action", "result"}:
                continue
            references[name if name.endswith("_revision") else name + "_id"] = (
                value if name.endswith("_revision") else value.pk if value is not None else None
            )
        payload = {"schema": 1, "event_id": event_id, "occurred_at": now.isoformat(),
                   "action": "read", "result": "authorized", "references": references}
        encrypted = encrypt_medical_value(json.dumps(payload, sort_keys=True, separators=(",", ":")),
            business_id=fields["business"].pk, subject_id=fields["patient"].pk, purpose="read_audit_reserve")
        body = json.dumps({"schema": 1, "business_id": fields["business"].pk,
            "patient_id": fields["patient"].pk, "encrypted_event": encrypted},
            sort_keys=True, separators=(",", ":")).encode("utf-8")
        client = boto3.client("s3", endpoint_url=config["endpoint"], region_name=config["region"],
            aws_access_key_id=config["access_key"], aws_secret_access_key=config["secret_key"],
            config=Config(connect_timeout=2, read_timeout=3, retries={"total_max_attempts": 1},
                          s3={"addressing_style": "path"}))
        key = f"medical-read-audit/{now:%Y/%m/%d}/{event_id}.json"
        result = client.put_object(Bucket=config["bucket"], Key=key, Body=body,
            ContentType="application/json", ContentMD5=base64.b64encode(hashlib.md5(body).digest()).decode(),
            ServerSideEncryption="aws:kms", SSEKMSKeyId=config["kms_key_id"],
            ObjectLockMode="COMPLIANCE", ObjectLockRetainUntilDate=until,
            Metadata={"sha256": hashlib.sha256(body).hexdigest()})
        version = result.get("VersionId")
        if result.get("ResponseMetadata", {}).get("HTTPStatusCode") != 200 or not isinstance(version, str) or not version or version == "null":
            raise ReserveUnavailable()
        target = {"Bucket": config["bucket"], "Key": key, "VersionId": version}
        retention = client.get_object_retention(**target).get("Retention", {})
        retained_until = retention.get("RetainUntilDate")
        if retention.get("Mode") != "COMPLIANCE" or retained_until is None or retained_until < until.replace(microsecond=0):
            raise ReserveUnavailable()
        head = client.head_object(**target)
        if (head.get("ServerSideEncryption") != "aws:kms" or head.get("SSEKMSKeyId") != config["kms_key_id"]
                or head.get("ContentLength") != len(body) or head.get("Metadata", {}).get("sha256") != hashlib.sha256(body).hexdigest()):
            raise ReserveUnavailable()
        return ReserveReceipt(event_id=event_id, version_id=version)
    except Exception:
        # Provider exceptions may include credentials or request identifiers.
        raise ReserveUnavailable() from None
