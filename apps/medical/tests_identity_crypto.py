import base64
import json

from django.test import SimpleTestCase, override_settings
from rest_framework.exceptions import ValidationError

from .identity_crypto import (
    MedicalDataUnavailable, MedicalKeyUnavailable, decrypt_medical_value,
    encrypt_medical_value, iin_digest, normalize_iin,
)


def encoded(byte):
    return base64.urlsafe_b64encode(bytes([byte]) * 32).decode("ascii")


@override_settings(MEDICAL_DATA_KEYS={"first": encoded(1)}, MEDICAL_DATA_ACTIVE_KEY_ID="first",
                   MEDICAL_IDENTITY_INDEX_KEY=encoded(3))
class MedicalIdentityCryptoTests(SimpleTestCase):
    context = {"business_id": 5, "subject_id": 8, "purpose": "iin"}
    synthetic_iin = "000000000001"

    def encrypt(self, value=None):
        return encrypt_medical_value(value or self.synthetic_iin, **self.context)

    def test_randomized_roundtrip_preserves_leading_zeroes_and_unicode(self):
        first, second = self.encrypt(), self.encrypt()
        self.assertNotEqual(first, second)
        self.assertNotIn(self.synthetic_iin, first)
        self.assertEqual(decrypt_medical_value(first, **self.context), self.synthetic_iin)
        value = "Тест / Сынақ"
        self.assertEqual(decrypt_medical_value(self.encrypt(value), **self.context), value)

    def test_authenticated_context_prevents_transplant(self):
        encrypted = self.encrypt()
        for override in ({"business_id": 6}, {"subject_id": 9}, {"purpose": "identity_evidence"}):
            with self.subTest(override=override), self.assertRaises(MedicalDataUnavailable):
                decrypt_medical_value(encrypted, **{**self.context, **override})

    def test_ciphertext_tampering_fails_without_disclosing_value(self):
        envelope = json.loads(self.encrypt())
        data = bytearray(base64.urlsafe_b64decode(envelope["ciphertext"]))
        data[0] ^= 1
        envelope["ciphertext"] = base64.urlsafe_b64encode(data).decode("ascii")
        with self.assertRaises(MedicalDataUnavailable) as raised:
            decrypt_medical_value(json.dumps(envelope), **self.context)
        self.assertNotIn(self.synthetic_iin, str(raised.exception))
        self.assertNotIn(envelope["ciphertext"], str(raised.exception))

    def test_envelope_metadata_tampering_is_rejected(self):
        original = json.loads(self.encrypt())
        for override in ({"v": True}, {"v": 2}, {"kid": []}, {"kid": "unknown"},
                         {"nonce": ""}, {"nonce": 123}, {"ciphertext": "!"}, {"extra": True}):
            with self.subTest(override=override), self.assertRaises(MedicalDataUnavailable):
                decrypt_medical_value(json.dumps({**original, **override}), **self.context)

    def test_plaintext_and_malformed_envelopes_are_never_accepted(self):
        for value in (self.synthetic_iin, "[]", "null", "{}", "not-json", None):
            with self.subTest(value=value), self.assertRaises(MedicalDataUnavailable):
                decrypt_medical_value(value, **self.context)

    def test_encryption_rotation_keeps_old_key_readable_and_index_stable(self):
        encrypted = self.encrypt()
        digest = iin_digest(self.synthetic_iin, business_id=5)
        with override_settings(MEDICAL_DATA_KEYS=json.dumps({"first": encoded(1), "second": encoded(2)}),
                               MEDICAL_DATA_ACTIVE_KEY_ID="second"):
            self.assertEqual(decrypt_medical_value(encrypted, **self.context), self.synthetic_iin)
            self.assertEqual(json.loads(self.encrypt())["kid"], "second")
            self.assertEqual(iin_digest(self.synthetic_iin, business_id=5), digest)
        with override_settings(MEDICAL_DATA_KEYS={"second": encoded(2)}, MEDICAL_DATA_ACTIVE_KEY_ID="second"):
            with self.assertRaises(MedicalDataUnavailable):
                decrypt_medical_value(encrypted, **self.context)

    def test_relabelling_key_id_cannot_bypass_authentication(self):
        envelope = json.loads(self.encrypt())
        envelope["kid"] = "alias"
        with override_settings(MEDICAL_DATA_KEYS={"first": encoded(1), "alias": encoded(1)}):
            with self.assertRaises(MedicalDataUnavailable):
                decrypt_medical_value(json.dumps(envelope), **self.context)

    def test_missing_invalid_keys_fail_closed_even_with_django_secret(self):
        for keys in ("", "[]", "{}", {"first": "invalid"}, {"first": encoded(1)[:-4]}, {"": encoded(1)}):
            with self.subTest(keys=keys), override_settings(MEDICAL_DATA_KEYS=keys):
                with self.assertRaises(MedicalKeyUnavailable):
                    self.encrypt()
        with override_settings(MEDICAL_DATA_ACTIVE_KEY_ID="absent"):
            with self.assertRaises(MedicalKeyUnavailable):
                self.encrypt()
        with override_settings(MEDICAL_IDENTITY_INDEX_KEY=""):
            with self.assertRaises(MedicalKeyUnavailable):
                iin_digest(self.synthetic_iin, business_id=5)

    def test_digest_is_tenant_scoped_deterministic_and_not_plaintext(self):
        first = iin_digest(self.synthetic_iin, business_id=5)
        self.assertEqual(first, iin_digest(self.synthetic_iin, business_id=5))
        self.assertNotEqual(first, iin_digest(self.synthetic_iin, business_id=6))
        self.assertNotEqual(first, iin_digest("000000000002", business_id=5))
        self.assertRegex(first, r"^[a-f0-9]{64}$")
        self.assertNotIn(self.synthetic_iin, first)

    def test_iin_syntax_is_not_a_claim_of_verified_identity(self):
        self.assertEqual(normalize_iin(self.synthetic_iin), self.synthetic_iin)
        for value in (None, 1, "", "123", "１２３４５６７８９０１２", " 000000000001", "000000000001\n"):
            with self.subTest(value=value), self.assertRaises(ValidationError):
                normalize_iin(value)

    def test_invalid_context_is_rejected_before_crypto(self):
        for override in ({"business_id": True}, {"subject_id": 0}, {"purpose": ""}, {"purpose": "iin\n"}):
            with self.subTest(override=override), self.assertRaises(ValueError):
                encrypt_medical_value(self.synthetic_iin, **{**self.context, **override})
