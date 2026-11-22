from unittest.mock import patch

from django.core.exceptions import ValidationError as ModelValidationError
from django.db import IntegrityError, connection, transaction
from django.test import TestCase, override_settings
from django.test.utils import CaptureQueriesContext
from rest_framework.exceptions import ValidationError

from apps.businesses.models import Business, BusinessMember
from apps.core.domain_errors import InvalidTransition
from . import tests_patient_services as crypto_fixtures
from . import tests_role_access as fixtures
from .document_templates import append_template_revision, read_template_revision
from .identity_crypto import MedicalDataUnavailable, MedicalKeyUnavailable, encrypt_medical_value
from .models import MedicalDocumentTemplate, MedicalDocumentTemplateRevision


@override_settings(MEDICAL_DATA_KEYS={"test": crypto_fixtures.key(7)}, MEDICAL_DATA_ACTIVE_KEY_ID="test")
class DocumentTemplateStorageTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        fixtures.MedicalRoleAccessTests.setUpTestData.__func__(cls)
        cls.template = MedicalDocumentTemplate.objects.create(business=cls.business, code="synthetic")

    def append(self, **overrides):
        return append_template_revision(**(dict(template=self.template, author=self.doctor,
            title="Учебный шаблон", text="Оқу үлгісі\nLiteral {{ value }}", reason="Synthetic private reason") | overrides))

    def test_template_content_is_encrypted_and_preserves_unicode_as_literal_data(self):
        with CaptureQueriesContext(connection) as queries:
            version = self.append()
        sql = "\n".join(row["sql"] for row in queries)
        for value in ("Учебный шаблон", "Оқу үлгісі", "Synthetic private reason"):
            self.assertNotIn(value, sql)
            self.assertNotIn(value, version.snapshot_encrypted)
        self.assertEqual(read_template_revision(version), {"template": {"code": "synthetic", "version": 1,
            "title": "Учебный шаблон", "text": "Оқу үлгісі\nLiteral {{ value }}"}, "reason": "Synthetic private reason"})

    def test_personal_template_links_only_a_member_of_its_business(self):
        self.template.owner_member = self.member
        self.template.save(update_fields=["owner_member"])
        self.assertEqual(read_template_revision(self.append())["template"]["version"], 1)
        other = Business.objects.create(owner=self.owner, name="Other", slug="template-other")
        foreign_member = BusinessMember.objects.create(business=other, user=self.owner)
        wrong = MedicalDocumentTemplate.objects.create(business=self.business, code="wrong", owner_member=foreign_member)
        with self.assertRaises(ModelValidationError):
            self.append(template=wrong)
        self.assertEqual(MedicalDocumentTemplateRevision.objects.count(), 1)

    def test_new_revision_preserves_old_text_author_and_reason(self):
        first = self.append()
        before = read_template_revision(first)
        self.template.refresh_from_db()
        BusinessMember.objects.create(business=self.business, user=self.owner)
        second = self.append(author=self.owner, title="Changed", text="New text", reason="New reason")
        self.assertEqual(second.revision, 2)
        self.assertEqual(read_template_revision(first), before)
        self.assertEqual(read_template_revision(second)["template"]["text"], "New text")
        self.assertEqual(first.author_id, self.doctor.pk)
        self.assertEqual(second.author_id, self.owner.pk)

    def test_stale_template_object_does_not_append(self):
        self.append()
        with self.assertRaises(InvalidTransition):
            self.append()
        self.assertEqual(MedicalDocumentTemplateRevision.objects.count(), 1)

    def test_inactive_or_nonmember_author_does_not_write(self):
        with self.assertRaises(ValidationError):
            self.append(author=self.owner)
        BusinessMember.objects.filter(pk=self.member.pk).update(is_active=False)
        with self.assertRaises(ValidationError):
            self.append()
        self.assertFalse(MedicalDocumentTemplateRevision.objects.exists())

    def test_scope_author_and_code_tampering_are_detected(self):
        first = self.append()
        for field, value, original in (("owner_member_id", self.member.pk, None), ("code", "changed", "synthetic")):
            MedicalDocumentTemplate.objects.filter(pk=self.template.pk).update(**{field: value})
            with self.subTest(field=field), self.assertRaises(MedicalDataUnavailable):
                read_template_revision(first)
            MedicalDocumentTemplate.objects.filter(pk=self.template.pk).update(**{field: original})
        MedicalDocumentTemplateRevision.objects.filter(pk=first.pk).update(author=self.owner)
        with self.assertRaises(MedicalDataUnavailable):
            read_template_revision(first)

    def test_ciphertext_cannot_be_swapped_between_versions_or_businesses(self):
        first = self.append()
        self.template.refresh_from_db()
        second = self.append(text="Different")
        MedicalDocumentTemplateRevision.objects.filter(pk=second.pk).update(snapshot_encrypted=first.snapshot_encrypted)
        with self.assertRaises(MedicalDataUnavailable):
            read_template_revision(second)
        other = Business.objects.create(owner=self.owner, name="Other", slug="template-swap")
        MedicalDocumentTemplate.objects.filter(pk=self.template.pk).update(business=other)
        with self.assertRaises(MedicalDataUnavailable):
            read_template_revision(first)

    def test_failure_after_allocation_rolls_back_version_and_parent_counter(self):
        calls = 0
        def encrypt(value, **kwargs):
            nonlocal calls
            calls += 1
            if calls == 2:
                raise MedicalKeyUnavailable()
            return encrypt_medical_value(value, **kwargs)
        with patch("apps.medical.document_templates.encrypt_medical_value", side_effect=encrypt):
            with self.assertRaises(MedicalKeyUnavailable):
                self.append()
        self.template.refresh_from_db()
        self.assertEqual(self.template.revision, 0)
        self.assertFalse(MedicalDocumentTemplateRevision.objects.exists())

    def test_outer_audit_failure_rolls_back_append(self):
        with self.assertRaises(RuntimeError), transaction.atomic():
            self.append()
            raise RuntimeError("Synthetic outer audit failure")
        self.template.refresh_from_db()
        self.assertEqual(self.template.revision, 0)
        self.assertFalse(MedicalDocumentTemplateRevision.objects.exists())

    def test_database_rejects_duplicate_code_version_and_empty_snapshot(self):
        first = self.append()
        with self.assertRaises(IntegrityError), transaction.atomic():
            MedicalDocumentTemplate.objects.create(business=self.business, code="synthetic")
        for revision, content in ((1, first.snapshot_encrypted), (0, first.snapshot_encrypted), (2, "")):
            with self.subTest(revision=revision), self.assertRaises(IntegrityError), transaction.atomic():
                MedicalDocumentTemplateRevision.objects.create(template=self.template, revision=revision,
                    author=self.doctor, snapshot_encrypted=content)

    def test_missing_keys_do_not_write_and_invalid_content_does_not_echo_input(self):
        with override_settings(MEDICAL_DATA_KEYS={}):
            with self.assertRaises(MedicalKeyUnavailable):
                self.append()
        for changes in ({"title": ""}, {"title": " \n\t"}, {"text": 123}, {"reason": "private" * 1000}):
            with self.subTest(changes=tuple(changes)), self.assertRaises(ValidationError) as error:
                self.append(**changes)
            self.assertNotIn("private", str(error.exception))
        self.assertFalse(MedicalDocumentTemplateRevision.objects.exists())

    def test_parent_revision_rollback_invalidates_newer_template_version(self):
        self.append()
        self.template.refresh_from_db()
        second = self.append()
        MedicalDocumentTemplate.objects.filter(pk=self.template.pk).update(revision=1)
        with self.assertRaises(MedicalDataUnavailable):
            read_template_revision(second)
