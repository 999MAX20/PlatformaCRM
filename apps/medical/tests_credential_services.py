from unittest.mock import patch

from django.db import DatabaseError, IntegrityError, transaction
from django.test import TestCase, override_settings
from rest_framework.exceptions import NotFound, PermissionDenied, ValidationError

from apps.businesses.models import Business, RolePermission
from apps.core.domain_errors import InvalidTransition
from apps.core.idempotency import CRMCommandConflict
from apps.core.models import CRMCommandIdempotency
from . import tests_patient_services as crypto_fixtures
from . import tests_template_reviews as fixtures
from .audit import MedicalAuditUnavailable
from .credential_services import confirm_medical_credentials, read_medical_credentials, write_credential_audit
from .models import MedicalAuditEvent, MedicalCredentialProfile, MedicalCredentialRevision


@override_settings(MEDICAL_DATA_KEYS={"test": crypto_fixtures.key(7)}, MEDICAL_DATA_ACTIVE_KEY_ID="test",
                   MEDICAL_IDENTITY_INDEX_KEY=crypto_fixtures.key(8))
class CredentialServiceTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        fixtures.TemplateReviewTests.setUpTestData.__func__(cls)

    def confirm(self, **overrides):
        return confirm_medical_credentials(**(dict(actor=self.head, business_id=self.business.pk,
            member_id=self.member.pk, content={"specialty": "Synthetic specialty", "position": "Synthetic position",
                "qualification": "Synthetic private qualification"}, reason="Synthetic private reason",
            expected_revision=0, idempotency_key="confirm") | overrides))

    def read(self, **overrides):
        return read_medical_credentials(**(dict(actor=self.doctor, business_id=self.business.pk,
            member_id=self.member.pk) | overrides))

    def test_head_confirmation_doctor_own_read_and_exact_version_history(self):
        self.assertIsNone(self.read()["version"])
        first, replayed = self.confirm()
        self.assertFalse(replayed)
        snapshot = self.read()["version"]
        self.assertEqual(snapshot["confirmed_by_id"], self.head.pk)
        self.assertIsNotNone(snapshot["confirmed_at"])
        self.assertEqual(snapshot["content"]["specialty"], "Synthetic specialty")
        second, _ = self.confirm(expected_revision=1, idempotency_key="next",
            content={"specialty": "New", "position": "New", "qualification": ""})
        self.assertEqual(second.revision, 2)
        self.assertEqual(self.read(version_id=first.pk)["version"], snapshot)
        self.assertEqual(self.read()["version"]["id"], second.pk)
        self.assertEqual(MedicalAuditEvent.objects.filter(action="credential_confirmed").count(), 2)
        self.assertEqual(MedicalAuditEvent.objects.filter(action="read", credential_version=first).count(), 2)

    def test_clinic_scope_and_other_clinician_are_head_only(self):
        clinic, _ = self.confirm(member_id=None, content={"license": "Synthetic license"})
        self.assertEqual(self.read(actor=self.head, member_id=None)["version"]["id"], clinic.pk)
        for target in (None, self.head_member.pk):
            with self.assertRaises(PermissionDenied):
                self.read(member_id=target)
        with self.assertRaises(NotFound):
            self.read(actor=self.head, member_id=self.member.pk, version_id=clinic.pk)

    def test_owner_and_doctor_cannot_confirm_even_with_approve_rule(self):
        RolePermission.objects.create(business_role=self.role, resource="medical_documents", action="approve",
                                      scope="business", is_allowed=True)
        for actor in (self.owner, self.doctor):
            with self.assertRaises(PermissionDenied):
                self.confirm(actor=actor)
        self.assertFalse(MedicalCredentialRevision.objects.exists())

    def test_permission_revocation_and_business_scope_apply_before_replay(self):
        self.confirm()
        permission = RolePermission.objects.get(business_role=self.head_role, resource="medical_documents", action="approve")
        for change in ({"is_allowed": False}, {"is_allowed": True, "scope": "own"}):
            RolePermission.objects.filter(pk=permission.pk).update(**change)
            with self.assertRaises(PermissionDenied):
                self.confirm()
        RolePermission.objects.filter(business_role=self.role, resource="medical_documents", action="view").update(is_allowed=False)
        with self.assertRaises(PermissionDenied):
            self.read()

    def test_replay_conflict_stale_and_no_duplicate_audit(self):
        version, _ = self.confirm()
        replay, replayed = self.confirm()
        self.assertTrue(replayed)
        self.assertEqual(replay.pk, version.pk)
        with self.assertRaises(CRMCommandConflict):
            self.confirm(reason="Changed")
        with self.assertRaises(InvalidTransition):
            self.confirm(idempotency_key="new-key")
        self.assertEqual(MedicalCredentialRevision.objects.count(), 1)
        self.assertEqual(MedicalAuditEvent.objects.filter(action="credential_confirmed").count(), 1)

    def test_foreign_business_and_member_do_not_leak(self):
        other = Business.objects.create(owner=self.owner, name="Other", slug="credential-services-other")
        with self.assertRaises(PermissionDenied):
            self.read(business_id=other.pk)
        with self.assertRaises(NotFound):
            self.confirm(member_id=999999)
        with self.assertRaises(NotFound):
            self.read(actor=self.head, member_id=999999)

    def test_required_fields_validation_and_no_private_plaintext_in_receipt(self):
        for content in ({"specialty": "", "position": "P", "qualification": ""},
                        {"specialty": "S", "position": " ", "qualification": ""},
                        {"specialty": "S", "position": "P", "qualification": "", "extra": "invalid"}):
            with self.assertRaises(ValidationError):
                self.confirm(content=content)
        self.assertFalse(MedicalCredentialProfile.objects.exists())
        version, _ = self.confirm()
        receipt = str(list(CRMCommandIdempotency.objects.values()))
        for private in ("Synthetic specialty", "Synthetic private qualification", "Synthetic private reason"):
            self.assertNotIn(private, version.content_encrypted)
            self.assertNotIn(private, receipt)

    def test_failed_write_audit_rolls_back_profile_version_and_receipt(self):
        with patch("apps.medical.credential_services.MedicalAuditEvent.objects.create", side_effect=DatabaseError), self.assertRaises(MedicalAuditUnavailable):
            self.confirm()
        self.assertFalse(MedicalCredentialProfile.objects.exists())
        self.assertFalse(MedicalCredentialRevision.objects.exists())
        self.assertFalse(CRMCommandIdempotency.objects.exists())

    def test_read_audit_failure_does_not_return_content(self):
        self.confirm()
        with patch("apps.medical.credential_services.MedicalAuditEvent.objects.create", return_value=None), self.assertRaises(MedicalAuditUnavailable):
            self.read()

    def test_audit_and_confirmation_constraints(self):
        version, _ = self.confirm()
        with self.assertRaises(ValueError):
            write_credential_audit(actor=self.doctor, business=self.business, version=version, action="credential_confirmed")
        with self.assertRaises(IntegrityError), transaction.atomic():
            MedicalCredentialRevision.objects.filter(pk=version.pk).update(confirmed_at=None)
        with self.assertRaises(IntegrityError), transaction.atomic():
            MedicalAuditEvent.objects.create(business=self.business, actor=self.head,
                                            action="credential_confirmed", result="success")
