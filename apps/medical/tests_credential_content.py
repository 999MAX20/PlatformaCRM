import json
from unittest.mock import patch

from django.core.exceptions import ValidationError as ModelValidationError
from django.db import IntegrityError, connection, transaction
from django.db.models.deletion import ProtectedError
from django.test import TestCase, override_settings
from django.test.utils import CaptureQueriesContext
from rest_framework.exceptions import ValidationError

from apps.businesses.models import Business, BusinessMember
from apps.core.domain_errors import InvalidTransition
from . import tests_patient_services as crypto_fixtures
from . import tests_role_access as fixtures
from .credential_content import append_credential_revision, read_credential_revision
from .identity_crypto import MedicalDataUnavailable, MedicalKeyUnavailable, decrypt_medical_value, encrypt_medical_value
from .models import MedicalCredentialProfile, MedicalCredentialRevision


@override_settings(MEDICAL_DATA_KEYS={"test": crypto_fixtures.key(7)}, MEDICAL_DATA_ACTIVE_KEY_ID="test")
class CredentialContentTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        fixtures.MedicalRoleAccessTests.setUpTestData.__func__(cls)
        cls.profile = MedicalCredentialProfile.objects.create(business=cls.business, member=cls.member)
        cls.clinic = MedicalCredentialProfile.objects.create(business=cls.business)

    def append(self, **overrides):
        return append_credential_revision(**(dict(profile=self.profile, author=self.doctor,
            content={"specialty": "Учебная специальность", "position": "Оқу лауазымы", "qualification": "Synthetic qualification"},
            reason="Private synthetic reason") | overrides))

    def test_encrypted_literal_content_for_clinic_and_clinician(self):
        with CaptureQueriesContext(connection) as queries:
            version = self.append()
            clinic = self.append(profile=self.clinic, content={"license": "Synthetic license <script>{{literal}}"})
        writes = "\n".join(row["sql"] for row in queries)
        for private in ("Учебная специальность", "Оқу лауазымы", "Synthetic qualification", "Private synthetic reason", "Synthetic license"):
            self.assertNotIn(private, writes)
            self.assertNotIn(private, version.content_encrypted)
        self.assertEqual(read_credential_revision(version)["content"]["position"], "Оқу лауазымы")
        self.assertEqual(read_credential_revision(clinic)["content"]["license"], "Synthetic license <script>{{literal}}")

    def test_old_history_survives_new_revision_and_member_deactivation(self):
        first = self.append()
        before = read_credential_revision(first)
        self.profile.refresh_from_db()
        second = self.append(content={"specialty": "New", "position": "", "qualification": ""})
        BusinessMember.objects.filter(pk=self.member.pk).update(is_active=False)
        self.assertEqual(read_credential_revision(first), before)
        self.assertEqual(read_credential_revision(second)["content"]["specialty"], "New")
        self.assertEqual(second.revision, 2)

    def test_foreign_member_link_rejected(self):
        other = Business.objects.create(owner=self.owner, name="Other", slug="credential-other")
        member = BusinessMember.objects.create(business=other, user=self.owner)
        wrong = MedicalCredentialProfile.objects.create(business=self.business, member=member)
        with self.assertRaises(ModelValidationError):
            self.append(profile=wrong)
        self.assertFalse(MedicalCredentialRevision.objects.exists())

    def test_nonmember_and_inactive_authors_rejected(self):
        with self.assertRaises(ValidationError):
            self.append(author=self.owner)
        BusinessMember.objects.filter(pk=self.member.pk).update(is_active=False)
        with self.assertRaises(ValidationError):
            self.append()
        BusinessMember.objects.filter(pk=self.member.pk).update(is_active=True)
        type(self.doctor).objects.filter(pk=self.doctor.pk).update(is_active=False)
        with self.assertRaises(ValidationError):
            self.append()
        self.assertFalse(MedicalCredentialRevision.objects.exists())

    def test_stale_write_does_not_allocate_version(self):
        self.append()
        with self.assertRaises(InvalidTransition):
            self.append()
        self.assertEqual(MedicalCredentialRevision.objects.count(), 1)

    def test_scope_shape_types_and_limits_rejected_without_private_echo(self):
        for content in (None, [], {"license": "Private"}, {"specialty": "x", "position": ""},
                        {"specialty": "x" * 256, "position": "", "qualification": ""},
                        {"specialty": "", "position": True, "qualification": ""},
                        {"specialty": "", "position": "", "qualification": "x" * 4001}):
            with self.subTest(content=type(content)), self.assertRaises(ValidationError) as error:
                self.append(content=content)
            self.assertNotIn("Private", str(error.exception))
        for reason in (None, "x" * 2001):
            with self.assertRaises(ValidationError):
                self.append(reason=reason)
        self.assertFalse(MedicalCredentialRevision.objects.exists())

    def test_database_scope_and_version_constraints(self):
        for member in (None, self.member):
            with self.assertRaises(IntegrityError), transaction.atomic():
                MedicalCredentialProfile.objects.create(business=self.business, member=member)
        version = self.append()
        for revision, content in ((1, "cipher"), (0, "cipher"), (2, "")):
            with self.assertRaises(IntegrityError), transaction.atomic():
                MedicalCredentialRevision.objects.create(profile=self.profile, revision=revision,
                    author=self.doctor, content_encrypted=content)
        with self.assertRaises(ProtectedError):
            self.profile.delete()
        self.assertTrue(MedicalCredentialRevision.objects.filter(pk=version.pk).exists())

    def test_ciphertext_scope_version_and_metadata_binding(self):
        first = self.append()
        self.profile.refresh_from_db()
        second = self.append()
        MedicalCredentialRevision.objects.filter(pk=second.pk).update(content_encrypted=first.content_encrypted)
        with self.assertRaises(MedicalDataUnavailable):
            read_credential_revision(second)
        MedicalCredentialRevision.objects.filter(pk=first.pk).update(author=self.owner)
        with self.assertRaises(MedicalDataUnavailable):
            read_credential_revision(first)
        MedicalCredentialRevision.objects.filter(pk=first.pk).update(author=self.doctor)
        member = BusinessMember.objects.create(business=self.business, user=self.owner)
        MedicalCredentialProfile.objects.filter(pk=self.profile.pk).update(member=member)
        with self.assertRaises(MedicalDataUnavailable):
            read_credential_revision(first)
        other = Business.objects.create(owner=self.owner, name="Other", slug="credential-swap")
        MedicalCredentialProfile.objects.filter(pk=self.profile.pk).update(business=other, member=None)
        with self.assertRaises(MedicalDataUnavailable):
            read_credential_revision(first)

    def test_invalid_authenticated_payload_fails_closed(self):
        version = self.append()
        payload = json.loads(decrypt_medical_value(version.content_encrypted, business_id=self.business.pk,
            subject_id=version.pk, purpose="medical_credentials"))
        for key, value in (("schema", True), ("revision", True), ("member_id", None),
                           ("content", {"license": "wrong scope"}), ("reason", [])):
            corrupted = dict(payload) | {key: value}
            encrypted = encrypt_medical_value(json.dumps(corrupted), business_id=self.business.pk,
                subject_id=version.pk, purpose="medical_credentials")
            MedicalCredentialRevision.objects.filter(pk=version.pk).update(content_encrypted=encrypted)
            with self.subTest(key=key), self.assertRaises(MedicalDataUnavailable):
                read_credential_revision(version)

    def test_final_encryption_failure_rolls_back_counter_and_version(self):
        real = encrypt_medical_value
        def fail(value, **kwargs):
            if kwargs["purpose"] == "medical_credentials":
                raise MedicalKeyUnavailable()
            return real(value, **kwargs)
        with patch("apps.medical.credential_content.encrypt_medical_value", side_effect=fail):
            with self.assertRaises(MedicalKeyUnavailable):
                self.append()
        self.profile.refresh_from_db()
        self.assertEqual(self.profile.revision, 0)
        self.assertFalse(MedicalCredentialRevision.objects.exists())
