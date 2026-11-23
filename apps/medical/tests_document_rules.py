from unittest.mock import patch

from django.db import DatabaseError
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied, ValidationError

from apps.businesses.models import Business, RolePermission
from apps.core.domain_errors import InvalidTransition
from apps.core.idempotency import CRMCommandConflict
from apps.services.models import Service
from . import tests_patient_services as crypto_fixtures
from . import tests_template_reviews as fixtures
from .audit import MedicalAuditUnavailable
from .document_rule_content import read_rule_revision
from .document_rule_services import read_document_rules, save_document_rules
from .identity_crypto import MedicalDataUnavailable
from .models import MedicalAuditEvent, MedicalDocumentKind, MedicalDocumentRuleRevision, MedicalDocumentTemplate


def default_rule(**changes):
    return {"required_at": "optional", "required_fields": [], "reviewers": ["primary_clinician"],
        "signers": [], "issuable": False} | changes


@override_settings(MEDICAL_DATA_KEYS={"test": crypto_fixtures.key(7)}, MEDICAL_DATA_ACTIVE_KEY_ID="test",
                   MEDICAL_IDENTITY_INDEX_KEY=crypto_fixtures.key(8))
class DocumentRuleTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        fixtures.TemplateReviewTests.setUpTestData.__func__(cls)
        from .document_templates import append_template_revision
        append_template_revision(template=cls.template, author=cls.head, title="Synthetic template", text="Synthetic text")

    def save(self, **overrides):
        return save_document_rules(**(dict(actor=self.head, business_id=self.business.pk,
            content={"name": "Synthetic document kind", "default": default_rule(), "services": []},
            template_ids=[self.template.pk], reason="Synthetic configuration", idempotency_key="create-rules") | overrides))

    def read(self, version, **overrides):
        return read_document_rules(**(dict(actor=self.head, business_id=self.business.pk, version_id=version.pk) | overrides))

    def test_create_replay_and_revision_keep_exact_encrypted_history(self):
        first, replayed = self.save()
        self.assertFalse(replayed)
        self.assertFalse(self.read(first)["content"]["docx_allowed"])
        replay, repeated = self.save()
        self.assertTrue(repeated)
        self.assertEqual(replay.pk, first.pk)
        original = self.read(first)
        service = Service.objects.create(business=self.business, name="Synthetic free service")
        content = {"name": "Synthetic revised rules", "docx_allowed": True, "default": default_rule(),
            "services": [{"service_id": service.pk, "rule": default_rule(required_at="before_completion",
                required_fields=["patient.full_name"], signers=["primary_clinician", "patient_or_representative"], issuable=True)}]}
        second, _ = self.save(kind_id=first.kind_id, expected_revision=1, content=content, idempotency_key="change-rules")
        service.name = "Renamed free service"
        service.save(update_fields=["name"])
        self.assertEqual(self.read(first), original)
        self.assertEqual(self.read(second)["content"]["services"][0]["name"], "Synthetic free service")
        self.assertNotIn("Synthetic", second.snapshot_encrypted)
        self.template.refresh_from_db()
        self.assertEqual(self.template.document_kind_id, first.kind_id)
        self.assertEqual(MedicalAuditEvent.objects.filter(action="document_rules_saved").count(), 2)

    def test_owner_doctor_revoked_head_and_narrow_scope_cannot_change_rules(self):
        first, _ = self.save()
        for actor in (self.owner, self.doctor):
            with self.subTest(actor=actor.pk), self.assertRaises(PermissionDenied):
                self.save(actor=actor)
        RolePermission.objects.filter(business_role=self.head_role, action="approve").update(scope="own")
        with self.assertRaises(PermissionDenied):
            self.save()
        RolePermission.objects.filter(business_role=self.head_role, action="approve").update(scope="business")
        self.head_assignment.revoked_at = timezone.now()
        self.head_assignment.save(update_fields=["revoked_at"])
        for operation in (self.save, lambda: self.read(first)):
            with self.assertRaises(PermissionDenied):
                operation()
        self.assertEqual(MedicalDocumentRuleRevision.objects.count(), 1)

    def test_tenant_kind_template_and_service_isolation(self):
        other = Business.objects.create(owner=self.owner, name="Other rules", slug="other-rules")
        foreign_template = MedicalDocumentTemplate.objects.create(business=other, code="foreign")
        foreign_kind = MedicalDocumentKind.objects.create(business=other)
        foreign_service = Service.objects.create(business=other, name="Foreign service")
        for changes in ({"template_ids": [foreign_template.pk]}, {"kind_id": foreign_kind.pk, "expected_revision": 1},
            {"content": {"name": "Synthetic", "default": default_rule(), "services": [
                {"service_id": foreign_service.pk, "rule": default_rule()}]}}):
            with self.subTest(changes=changes), self.assertRaises(PermissionDenied):
                self.save(**changes)
        self.assertFalse(MedicalDocumentKind.objects.filter(business=self.business).exists())
        first, _ = self.save()
        with self.assertRaises(PermissionDenied):
            self.read(first, business_id=other.pk)

    def test_stale_revision_payload_conflict_and_binding_conflict_do_not_mutate(self):
        first, _ = self.save()
        with self.assertRaises(CRMCommandConflict):
            self.save(reason="Different payload")
        with self.assertRaises(InvalidTransition):
            self.save(kind_id=first.kind_id, expected_revision=2, idempotency_key="stale")
        with self.assertRaises(InvalidTransition):
            self.save(idempotency_key="second-kind")
        self.assertEqual(MedicalDocumentKind.objects.count(), 1)
        self.assertEqual(MedicalDocumentRuleRevision.objects.count(), 1)

    def test_invalid_rules_cannot_remove_primary_review_or_invent_fields(self):
        invalid = [default_rule(reviewers=[]), default_rule(required_fields=["patient.secret"]),
            default_rule(signers=["assistant"]), default_rule(signers=["primary_clinician", "primary_clinician"]),
            default_rule(required_at="before_issue"), default_rule(issuable=1)]
        for rule in invalid:
            with self.subTest(rule=rule), self.assertRaises(ValidationError):
                self.save(content={"name": "Synthetic", "default": rule, "services": []})
        self.assertFalse(MedicalDocumentKind.objects.exists())

    def test_audit_failure_rolls_back_version_and_template_binding(self):
        for result in (None, DatabaseError("Synthetic failure")):
            kwargs = {"side_effect": result} if isinstance(result, Exception) else {"return_value": result}
            with patch("apps.medical.document_rule_services.MedicalAuditEvent.objects.create", **kwargs):
                with self.assertRaises(MedicalAuditUnavailable):
                    self.save()
            self.assertFalse(MedicalDocumentKind.objects.exists())
            self.assertFalse(MedicalDocumentRuleRevision.objects.exists())
            self.template.refresh_from_db()
            self.assertIsNone(self.template.document_kind_id)
        first, _ = self.save()
        with patch("apps.medical.document_rule_services.MedicalAuditEvent.objects.create", return_value=None):
            with self.assertRaises(MedicalAuditUnavailable):
                self.read(first)

    def test_private_unapproved_template_is_not_visible_to_configuration(self):
        private = MedicalDocumentTemplate.objects.create(business=self.business, owner_member=self.member, code="private_rules")
        with self.assertRaises(PermissionDenied):
            self.save(template_ids=[private.pk])
        self.assertFalse(MedicalDocumentKind.objects.exists())

    def test_ciphertext_cannot_be_retargeted_to_another_version(self):
        first, _ = self.save()
        second, _ = self.save(kind_id=first.kind_id, expected_revision=1, idempotency_key="new-version")
        MedicalDocumentRuleRevision.objects.filter(pk=second.pk).update(snapshot_encrypted=first.snapshot_encrypted)
        with self.assertRaises(MedicalDataUnavailable):
            read_rule_revision(second)
