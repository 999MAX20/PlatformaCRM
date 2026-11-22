from unittest.mock import patch

from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied, ValidationError

from apps.businesses.models import Business, BusinessCapability, RolePermission
from apps.core.domain_errors import InvalidTransition, ModuleDisabled
from apps.core.idempotency import CRMCommandConflict
from . import tests_patient_services as crypto_fixtures
from . import tests_template_reviews as fixtures
from .audit import MedicalAuditUnavailable
from .common_template_services import (
    save_common_template_draft, submit_common_template, read_common_template_version,
    read_approved_template_version, list_common_template_drafts, list_approved_templates,
)
from .identity_crypto import MedicalDataUnavailable
from .models import MedicalDocumentTemplate, MedicalDocumentTemplateRevision, MedicalTemplateReview, MedicalAuditEvent
from .template_reviews import decide_template_review, submit_personal_template
from .template_services import save_personal_template_draft, read_personal_template_version


@override_settings(MEDICAL_DATA_KEYS={"test": crypto_fixtures.key(7)}, MEDICAL_DATA_ACTIVE_KEY_ID="test",
                   MEDICAL_IDENTITY_INDEX_KEY=crypto_fixtures.key(8))
class CommonTemplateTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        fixtures.TemplateReviewTests.setUpTestData.__func__(cls)
        for action in ("create", "update"):
            RolePermission.objects.create(business_role=cls.head_role, resource="medical_documents",
                action=action, scope="business", is_allowed=True)

    def save(self, **overrides):
        return save_common_template_draft(**(dict(actor=self.head, business_id=self.business.pk,
            title="Synthetic common template", text="Synthetic common text", idempotency_key="common-create") | overrides))

    def submit(self, version, **overrides):
        return submit_common_template(**(dict(actor=self.head, business_id=self.business.pk,
            version_id=version.pk, idempotency_key=f"submit-{version.pk}") | overrides))

    def approve(self, version, **overrides):
        self.submit(version)
        return decide_template_review(**(dict(actor=self.head, business_id=self.business.pk,
            version_id=version.pk, decision="approved", reason="", idempotency_key=f"approve-{version.pk}") | overrides))

    def read(self, version, **overrides):
        return read_approved_template_version(**(dict(actor=self.doctor, business_id=self.business.pk,
            version_id=version.pk) | overrides))

    def listing(self, **overrides):
        return list_approved_templates(**(dict(actor=self.doctor, business_id=self.business.pk) | overrides))

    def test_common_draft_is_private_until_explicit_approval(self):
        version, replayed = self.save()
        self.assertFalse(replayed)
        self.assertIsNone(version.template.owner_member_id)
        self.assertTrue(version.template.code.startswith("common_"))
        self.assertNotIn("Synthetic", version.snapshot_encrypted)
        common = read_common_template_version(actor=self.head, business_id=self.business.pk, version_id=version.pk)
        self.assertEqual(common["template"]["text"], "Synthetic common text")
        self.assertIsNone(common["review"])
        self.assertEqual(self.listing()["results"], [])
        with self.assertRaises(PermissionDenied):
            self.read(version)
        self.submit(version)
        self.assertEqual(self.listing()["results"], [])
        decide_template_review(actor=self.head, business_id=self.business.pk, version_id=version.pk,
            decision="approved", reason="", idempotency_key="decision")
        self.assertEqual(self.read(version)["review"]["state"], "approved")
        self.assertEqual(self.listing()["results"][0]["version_id"], version.pk)

    def test_doctor_and_owner_cannot_manage_common_drafts(self):
        version, _ = self.save()
        for actor in (self.doctor, self.owner):
            for operation in (
                lambda: self.save(actor=actor), lambda: self.submit(version, actor=actor),
                lambda: read_common_template_version(actor=actor, business_id=self.business.pk, version_id=version.pk),
                lambda: list_common_template_drafts(actor=actor, business_id=self.business.pk),
            ):
                with self.assertRaises(PermissionDenied):
                    operation()
        RolePermission.objects.filter(business_role=self.role, resource="medical_documents").update(scope="business")
        with self.assertRaises(PermissionDenied):
            self.save(actor=self.doctor)

    def test_head_requires_business_scope_for_both_write_and_view(self):
        existing = set(MedicalDocumentTemplate.objects.values_list("pk", flat=True))
        for action in ("create", "view"):
            permission = RolePermission.objects.get(business_role=self.head_role, resource="medical_documents", action=action)
            permission.scope = "own"
            permission.save(update_fields=["scope"])
            with self.assertRaises(PermissionDenied):
                self.save()
            permission.scope = "business"
            permission.save(update_fields=["scope"])
        self.assertEqual(set(MedicalDocumentTemplate.objects.values_list("pk", flat=True)), existing)
        self.assertFalse(MedicalDocumentTemplateRevision.objects.exists())

    def test_common_and_personal_scopes_cannot_be_converted(self):
        common, _ = self.save()
        personal, _ = save_personal_template_draft(actor=self.head, business_id=self.business.pk,
            title="Personal", text="", idempotency_key="common-create")
        self.assertNotEqual(personal.template_id, common.template_id)
        with self.assertRaises(PermissionDenied):
            self.save(template_id=personal.template_id, expected_revision=1, idempotency_key="convert")
        with self.assertRaises(PermissionDenied):
            save_personal_template_draft(actor=self.head, business_id=self.business.pk, title="Convert", text="",
                template_id=common.template_id, expected_revision=1, idempotency_key="convert")
        with self.assertRaises(PermissionDenied):
            submit_personal_template(actor=self.head, business_id=self.business.pk,
                version_id=common.pk, idempotency_key="convert")
        with self.assertRaises(PermissionDenied):
            self.submit(personal)
        with self.assertRaises(PermissionDenied):
            read_personal_template_version(actor=self.head, business_id=self.business.pk, version_id=common.pk)

    def test_new_draft_does_not_replace_old_approved_version(self):
        first, _ = self.save()
        self.approve(first)
        second, _ = self.save(template_id=first.template_id, expected_revision=1, title="New draft", idempotency_key="update")
        self.assertEqual(self.listing()["results"][0]["version_id"], first.pk)
        self.assertEqual(self.read(first)["current_revision"], 2)
        with self.assertRaises(PermissionDenied):
            self.read(second)
        self.approve(second)
        self.assertEqual(self.listing()["results"][0]["version_id"], second.pk)
        self.assertEqual(self.read(first)["template"]["title"], "Synthetic common template")

    def test_rejected_version_does_not_enter_approved_selector(self):
        version, _ = self.save()
        self.approve(version, decision="rejected", reason="Synthetic correction")
        self.assertEqual(self.listing()["results"], [])
        with self.assertRaises(PermissionDenied):
            self.read(version)

    def test_personal_approved_version_remains_private_to_its_owner(self):
        version, _ = save_personal_template_draft(actor=self.doctor, business_id=self.business.pk,
            title="Private", text="", idempotency_key="personal")
        submit_personal_template(actor=self.doctor, business_id=self.business.pk, version_id=version.pk, idempotency_key="submit")
        decide_template_review(actor=self.head, business_id=self.business.pk, version_id=version.pk,
            decision="approved", reason="", idempotency_key="approve")
        self.assertEqual(self.listing()["results"][0]["version_id"], version.pk)
        self.assertEqual(self.listing(actor=self.head)["results"], [])
        with self.assertRaises(PermissionDenied):
            self.read(version, actor=self.head)

    def test_replay_conflict_stale_and_role_revocation(self):
        version, _ = self.save()
        self.assertTrue(self.save()[1])
        with self.assertRaises(CRMCommandConflict):
            self.save(title="Different")
        self.submit(version)
        self.assertTrue(self.submit(version)[1])
        self.save(template_id=version.template_id, expected_revision=1, idempotency_key="update")
        with self.assertRaises(InvalidTransition):
            self.save(template_id=version.template_id, expected_revision=1, idempotency_key="stale")
        self.head_assignment.revoked_at = timezone.now()
        self.head_assignment.save(update_fields=["revoked_at"])
        with self.assertRaises(PermissionDenied):
            self.save()
        with self.assertRaises(PermissionDenied):
            self.submit(version)

    def test_tenant_isolation_in_lists_and_exact_reads(self):
        other = Business.objects.create(owner=self.owner, name="Foreign", slug="common-foreign")
        template = MedicalDocumentTemplate.objects.create(business=other, code="foreign", revision=1)
        foreign = MedicalDocumentTemplateRevision.objects.create(template=template, revision=1,
            author=self.head, snapshot_encrypted="must-not-decrypt")
        MedicalTemplateReview.objects.create(version=foreign, submitted_by=self.head, state="approved",
            decided_by=self.head, decided_at=timezone.now() + timezone.timedelta(seconds=1), decision_encrypted="foreign")
        self.assertEqual(self.listing()["results"], [])
        with self.assertRaises(PermissionDenied):
            self.read(foreign)
        with self.assertRaises(PermissionDenied):
            self.save(template_id=template.pk, expected_revision=1)

    def test_audit_and_receipt_fail_closed(self):
        existing = set(MedicalDocumentTemplate.objects.values_list("pk", flat=True))
        with patch("apps.medical.template_services.write_template_audit", side_effect=MedicalAuditUnavailable):
            with self.assertRaises(MedicalAuditUnavailable):
                self.save()
        self.assertEqual(set(MedicalDocumentTemplate.objects.values_list("pk", flat=True)), existing)
        self.assertFalse(MedicalDocumentTemplateRevision.objects.exists())
        version, _ = self.save()
        self.approve(version)
        before = MedicalAuditEvent.objects.count()
        MedicalTemplateReview.objects.update(decision_encrypted="corrupt")
        with self.assertRaises(MedicalDataUnavailable):
            self.listing()
        self.assertEqual(MedicalAuditEvent.objects.count(), before)

    def test_list_pagination_and_current_common_drafts(self):
        first, _ = self.save()
        self.approve(first)
        second, _ = self.save(idempotency_key="second")
        self.approve(second)
        page = self.listing(limit=1)
        self.assertEqual(page["results"][0]["version_id"], second.pk)
        page = self.listing(limit=1, before_id=page["next_before_id"])
        self.assertEqual(page["results"][0]["version_id"], first.pk)
        self.assertIsNone(page["next_before_id"])
        latest, _ = self.save(template_id=first.template_id, expected_revision=1, idempotency_key="update")
        common = list_common_template_drafts(actor=self.head, business_id=self.business.pk)
        self.assertEqual({row["version_id"] for row in common["results"]}, {latest.pk, second.pk})
        for limit in (False, 0, 51):
            with self.assertRaises(ValidationError):
                self.listing(limit=limit)

    def test_module_and_current_doctor_role_gate_approved_reads(self):
        version, _ = self.save()
        self.approve(version)
        self.assignment.revoked_at = timezone.now()
        self.assignment.save(update_fields=["revoked_at"])
        with self.assertRaises(PermissionDenied):
            self.read(version)
        BusinessCapability.objects.filter(business=self.business, module_key="medical_records").update(is_enabled=False)
        with self.assertRaises(ModuleDisabled):
            self.listing(actor=self.head)
