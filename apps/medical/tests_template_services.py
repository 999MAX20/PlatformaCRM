from unittest.mock import patch

from django.db import DatabaseError, IntegrityError, transaction
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied

from apps.businesses.models import BusinessCapability, BusinessMember, RolePermission
from apps.core.domain_errors import InvalidTransition, ModuleDisabled
from apps.core.idempotency import CRMCommandConflict
from apps.core.models import CRMCommandIdempotency
from . import tests_document_templates as fixtures
from . import tests_patient_services as crypto_fixtures
from .audit import MedicalAuditUnavailable
from .identity_crypto import MedicalKeyUnavailable
from .models import MedicalAuditEvent, MedicalDocumentTemplate, MedicalDocumentTemplateRevision
from .template_audit import write_template_audit
from .template_services import list_personal_template_drafts, read_personal_template_version, save_personal_template_draft


@override_settings(MEDICAL_DATA_KEYS={"test": crypto_fixtures.key(7)}, MEDICAL_DATA_ACTIVE_KEY_ID="test",
                   MEDICAL_IDENTITY_INDEX_KEY=crypto_fixtures.key(8))
class PersonalTemplateServiceTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        fixtures.DocumentTemplateStorageTests.setUpTestData.__func__(cls)
        for action in ("create", "update", "view"):
            RolePermission.objects.create(business_role=cls.role, resource="medical_documents",
                action=action, scope="own", is_allowed=True)

    def save(self, **overrides):
        return save_personal_template_draft(**(dict(actor=self.doctor, business_id=self.business.pk,
            title="Личный шаблон", text="Private synthetic text", reason="Private reason",
            idempotency_key="private-key") | overrides))

    def read(self, version, **overrides):
        return read_personal_template_version(**(dict(actor=self.doctor, business_id=self.business.pk,
            version_id=version.pk) | overrides))

    def listing(self, **overrides):
        return list_personal_template_drafts(**(dict(actor=self.doctor, business_id=self.business.pk) | overrides))

    def test_create_read_and_replay_preserve_private_content_and_exact_audit(self):
        version, replayed = self.save()
        self.assertFalse(replayed)
        self.assertEqual(version.template.owner_member_id, self.member.pk)
        self.assertTrue(version.template.code.startswith("personal_"))
        event = MedicalAuditEvent.objects.get()
        self.assertEqual(event.template_version_id, version.pk)
        self.assertIsNone(event.patient_id)
        self.assertEqual(self.read(version)["template"]["text"], "Private synthetic text")
        replay, replayed = self.save()
        self.assertTrue(replayed)
        self.assertEqual(replay.pk, version.pk)
        self.assertEqual(MedicalDocumentTemplateRevision.objects.count(), 1)
        for record in [CRMCommandIdempotency.objects.get(), *MedicalAuditEvent.objects.all()]:
            self.assertNotIn("Private", str(record.__dict__))
            self.assertNotIn("Личный", str(record.__dict__))

    def test_update_preserves_history_and_original_replay(self):
        first, _ = self.save()
        second, _ = self.save(template_id=first.template_id, expected_revision=1, text="Next", idempotency_key="next")
        self.assertEqual(second.revision, 2)
        self.assertEqual(self.read(first)["template"]["text"], "Private synthetic text")
        self.assertEqual(self.read(second)["template"]["text"], "Next")
        self.assertEqual(self.save()[0].pk, first.pk)
        self.assertEqual(MedicalAuditEvent.objects.filter(action="template_draft_saved", template_version=second).count(), 1)

    def test_stale_and_conflicting_requests_do_not_append(self):
        first, _ = self.save()
        with self.assertRaises(CRMCommandConflict):
            self.save(text="Other")
        with self.assertRaises(InvalidTransition):
            self.save(template_id=first.template_id, expected_revision=999, idempotency_key="stale")
        self.assertEqual(MedicalDocumentTemplateRevision.objects.count(), 1)

    def test_owner_and_assistant_cannot_use_clinician_personal_drafts(self):
        with self.assertRaises(PermissionDenied):
            self.save(actor=self.owner)
        self.assignment.kind = "assistant"
        self.assignment.save(update_fields=["kind"])
        with self.assertRaises(PermissionDenied):
            self.save()
        self.assertFalse(MedicalDocumentTemplateRevision.objects.exists())

    def test_revoked_role_denies_read_list_and_replay(self):
        first, _ = self.save()
        self.assignment.revoked_at = timezone.now()
        self.assignment.save(update_fields=["revoked_at"])
        for operation in (self.save, self.listing, lambda: self.read(first)):
            with self.assertRaises(PermissionDenied):
                operation()
        self.assertEqual(MedicalAuditEvent.objects.count(), 1)

    def test_missing_document_permission_or_disabled_module_denies_access(self):
        first, _ = self.save()
        RolePermission.objects.filter(business_role=self.role, resource="medical_documents", action="view").delete()
        with self.assertRaises(PermissionDenied):
            self.read(first)
        BusinessCapability.objects.filter(business=self.business, module_key="medical_records").update(is_enabled=False)
        with self.assertRaises(ModuleDisabled):
            self.save()

    def test_valid_role_cannot_read_or_edit_common_or_another_persons_template(self):
        common = fixtures.DocumentTemplateStorageTests.append(self)
        with self.assertRaises(PermissionDenied):
            self.read(common)
        with self.assertRaises(PermissionDenied):
            self.save(template_id=common.template_id, expected_revision=1)
        other = BusinessMember.objects.create(business=self.business, user=self.owner)
        MedicalDocumentTemplate.objects.filter(pk=common.template_id).update(owner_member=other)
        with self.assertRaises(PermissionDenied):
            self.read(common)
        with self.assertRaises(PermissionDenied):
            self.save(template_id=common.template_id, expected_revision=1)
        self.assertEqual(self.listing()["results"], [])

    def test_listing_has_stable_pagination_and_audits_only_exposed_versions(self):
        first, _ = self.save()
        second, _ = self.save(idempotency_key="second", title="Другой шаблон")
        page = self.listing(limit=1)
        self.assertEqual([row["version_id"] for row in page["results"]], [second.pk])
        self.assertNotIn("text", page["results"][0])
        last = self.listing(before_id=page["next_before_id"], limit=1)
        self.assertEqual([row["version_id"] for row in last["results"]], [first.pk])
        self.assertIsNone(last["next_before_id"])
        self.assertEqual(MedicalAuditEvent.objects.filter(action="read").count(), 2)

    def test_failed_audit_rolls_back_new_template_version_and_receipt(self):
        with patch("apps.medical.template_audit.MedicalAuditEvent.objects.create", side_effect=DatabaseError()):
            with self.assertRaises(MedicalAuditUnavailable):
                self.save()
        self.assertEqual(MedicalDocumentTemplate.objects.count(), 1)
        self.assertFalse(MedicalDocumentTemplateRevision.objects.exists())
        self.assertFalse(CRMCommandIdempotency.objects.exists())

    def test_read_audit_failure_prevents_decryption(self):
        first, _ = self.save()
        with patch("apps.medical.template_audit.MedicalAuditEvent.objects.create", side_effect=DatabaseError()), \
                patch("apps.medical.template_services.read_template_revision") as decrypt:
            with self.assertRaises(MedicalAuditUnavailable):
                self.read(first)
            decrypt.assert_not_called()

    def test_key_failure_does_not_leave_new_template(self):
        with override_settings(MEDICAL_DATA_KEYS={}):
            with self.assertRaises(MedicalKeyUnavailable):
                self.save()
        self.assertEqual(MedicalDocumentTemplate.objects.count(), 1)
        self.assertFalse(CRMCommandIdempotency.objects.exists())

    def test_audit_rejects_stale_write_wrong_actor_and_missing_version(self):
        first, _ = self.save()
        self.save(template_id=first.template_id, expected_revision=1, idempotency_key="next")
        with self.assertRaises(ValueError):
            write_template_audit(actor=self.doctor, business=self.business, version=first, action="template_draft_saved")
        with self.assertRaises(ValueError):
            write_template_audit(actor=self.owner, business=self.business, version=first, action="template_draft_created")
        with self.assertRaises(IntegrityError), transaction.atomic():
            MedicalAuditEvent.objects.create(business=self.business, actor=self.doctor,
                action="template_draft_created", result="success")
