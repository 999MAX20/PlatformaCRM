import base64
import binascii
import hashlib
import hmac
import json
import re
import secrets

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from django.conf import settings
from rest_framework.exceptions import ValidationError

from apps.core.domain_errors import DomainAPIException


class MedicalKeyUnavailable(DomainAPIException):
    status_code = 503
    error_code = "medical_key_unavailable"
    default_code = error_code
    default_detail = "Medical data key configuration is unavailable."
    category = "configuration"


class MedicalDataUnavailable(DomainAPIException):
    status_code = 503
    error_code = "medical_data_unavailable"
    default_code = error_code
    default_detail = "Medical data could not be opened."
    category = "configuration"


_KEY_ID = re.compile(r"[A-Za-z0-9._-]{1,64}")
_PURPOSE = re.compile(r"[a-z][a-z0-9_]{0,63}")


def _decode(value):
    return base64.b64decode(value, altchars=b"-_", validate=True)


def _key(value):
    try:
        decoded = _decode(value)
        if len(decoded) != 32:
            raise ValueError
        return decoded
    except (ValueError, TypeError, binascii.Error):
        raise MedicalKeyUnavailable() from None


def _keyring():
    try:
        keys = settings.MEDICAL_DATA_KEYS
        if isinstance(keys, str):
            keys = json.loads(keys)
        if not isinstance(keys, dict) or not keys:
            raise ValueError
        if any(not isinstance(key_id, str) or not _KEY_ID.fullmatch(key_id) for key_id in keys):
            raise ValueError
        return {key_id: _key(value) for key_id, value in keys.items()}
    except (AttributeError, ValueError, TypeError):
        raise MedicalKeyUnavailable() from None


def _context(business_id, subject_id, purpose):
    if any(type(value) is not int or value <= 0 for value in (business_id, subject_id)):
        raise ValueError("Medical data requires persisted business and subject identifiers.")
    if not isinstance(purpose, str) or not _PURPOSE.fullmatch(purpose):
        raise ValueError("Medical data requires an explicit field purpose.")
    return ["platforma-medical", 1, business_id, subject_id, purpose]


def encrypt_medical_value(value, *, business_id, subject_id, purpose):
    context = _context(business_id, subject_id, purpose)
    if not isinstance(value, str):
        raise TypeError("Medical plaintext must be text.")
    keys = _keyring()
    key_id = getattr(settings, "MEDICAL_DATA_ACTIVE_KEY_ID", None)
    if not isinstance(key_id, str) or key_id not in keys:
        raise MedicalKeyUnavailable()
    nonce = secrets.token_bytes(12)
    aad = json.dumps([*context, key_id], separators=(",", ":")).encode()
    ciphertext = AESGCM(keys[key_id]).encrypt(nonce, value.encode("utf-8"), aad)
    return json.dumps({"v": 1, "kid": key_id,
                      "nonce": base64.urlsafe_b64encode(nonce).decode("ascii"),
                      "ciphertext": base64.urlsafe_b64encode(ciphertext).decode("ascii")},
                     separators=(",", ":"), sort_keys=True)


def decrypt_medical_value(encrypted, *, business_id, subject_id, purpose):
    context = _context(business_id, subject_id, purpose)
    keys = _keyring()
    try:
        envelope = json.loads(encrypted)
        if not isinstance(envelope, dict) or set(envelope) != {"v", "kid", "nonce", "ciphertext"}:
            raise ValueError
        if type(envelope["v"]) is not int or envelope["v"] != 1:
            raise ValueError
        key_id = envelope["kid"]
        if not isinstance(key_id, str) or key_id not in keys:
            raise ValueError
        nonce = _decode(envelope["nonce"])
        if len(nonce) != 12:
            raise ValueError
        aad = json.dumps([*context, key_id], separators=(",", ":")).encode()
        return AESGCM(keys[key_id]).decrypt(nonce, _decode(envelope["ciphertext"]), aad).decode("utf-8")
    except (ValueError, TypeError, KeyError, InvalidTag, UnicodeError, binascii.Error):
        raise MedicalDataUnavailable() from None


def normalize_iin(value):
    # Syntax validation is separate from the clinic's identity verification.
    if not isinstance(value, str) or not re.fullmatch(r"[0-9]{12}", value):
        raise ValidationError({"iin": "Enter 12 digits."})
    return value


def iin_digest(value, *, business_id):
    value = normalize_iin(value)
    if type(business_id) is not int or business_id <= 0:
        raise ValueError("An existing business is required.")
    key = _key(getattr(settings, "MEDICAL_IDENTITY_INDEX_KEY", None))
    payload = json.dumps(["platforma-medical-iin", 1, business_id, value], separators=(",", ":")).encode()
    return hmac.new(key, payload, hashlib.sha256).hexdigest()


def medical_request_digest(payload, *, business_id):
    if type(business_id) is not int or business_id <= 0:
        raise ValueError("An existing business is required.")
    key = _key(getattr(settings, "MEDICAL_IDENTITY_INDEX_KEY", None))
    encoded = json.dumps(["platforma-medical-command", 1, business_id, payload],
                         sort_keys=True, ensure_ascii=False, separators=(",", ":"), allow_nan=False).encode("utf-8")
    return hmac.new(key, encoded, hashlib.sha256).hexdigest()
