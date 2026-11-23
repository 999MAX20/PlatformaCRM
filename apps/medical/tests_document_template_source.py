import json
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from rest_framework.exceptions import PermissionDenied, ValidationError

from apps.businesses.models import Business, BusinessMember, BusinessRole, RolePermission
from apps.core.idempotency import CRMCommandConflict
from apps.core.domain_errors import InvalidTransition
from . import tests_document_services as fixtures
from . import tests_patient_services as crypto_fixtures
from .audit import MedicalAuditUnavailable
from .common_template_services import save_common_template_draft, submit_common_template
from .document_content import read_document_revision
from .document_services import save_primary_document_draft
from .identity_crypto import MedicalDataUnavailable, decrypt_medical_value, encrypt_medical_value
from .models import MedicalAuditEvent, MedicalDocumentRevision, MedicalDocumentTemplate, MedicalDocumentTemplateRevision, MedicalRoleAssignment, MedicalTemplateReview
from .template_reviews import decide_template_review, submit_personal_template
from .template_services import save_personal_template_draft
from .template_availability import set_template_availability


@override_settings(MEDICAL_DATA_KEYS={"test": crypto_fixtures.key(7)}, MEDICAL_DATA_ACTIVE_KEY_ID="test",
                   MEDICAL_IDENTITY_INDEX_KEY=crypto_fixtures.key(8))
class DocumentTemplateSourceTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        fixtures.DocumentServiceTests.setUpTestData.__func__(cls)
        cls.head = get_user_model().objects.create_user(username="source-head", email="source-head@example.test")
        member = BusinessMember.objects.create(business=cls.business, user=cls.head)
        role = BusinessRole.objects.create(business=cls.business, name="Source reviewer")
        MedicalRoleAssignment.objects.create(member=member, business_role=role, kind="head", granted_by=cls.owner)
        for action in ("view", "create", "update", "approve"):
            RolePermission.objects.create(business_role=role, resource="medical_documents", action=action,
                                          scope="business", is_allowed=True)

    def setUp(self):
        fixtures.DocumentServiceTests.setUp(self)
        self.template, _ = save_common_template_draft(actor=self.head, business_id=self.business.pk,
            title="Synthetic source", text="Original {{patient}} text", idempotency_key="source")

    def approve(self, version=None):
        version = version or self.template
        submit_common_template(actor=self.head, business_id=self.business.pk,
            version_id=version.pk, idempotency_key=f"submit-{version.pk}")
        return decide_template_review(actor=self.head, business_id=self.business.pk,
            version_id=version.pk, decision="approved", reason="", idempotency_key=f"approve-{version.pk}")[0]

    def save(self, **overrides):
        return save_primary_document_draft(**(dict(actor=self.doctor, business_id=self.business.pk,
            patient_id=self.patient.pk, encounter_id=self.encounter_record.pk, expected_encounter_revision=1,
            expected_patient_revision=self.patient.revision, idempotency_key="source-document",
            template_version_id=self.template.pk, document_text="Doctor edited synthetic text") | overrides))

    def test_source_and_edited_text_are_distinct_and_bound_to_approval(self):
        review = self.approve()
        version, replayed = self.save()
        self.assertFalse(replayed)
        snapshot = read_document_revision(version)
        self.assertEqual(snapshot["template"]["text"], "Original {{patient}} text")
        self.assertEqual(snapshot["document_text"], "Doctor edited synthetic text")
        self.assertEqual(snapshot["template_source"], dict(template_id=self.template.template_id,
            version_id=self.template.pk, revision=1, review_id=review.pk,
            approved_by=self.head.pk, approved_at=review.decided_at.isoformat()))
        self.assertNotIn("Doctor edited", version.snapshot_encrypted)
        self.assertTrue(self.save()[1])
        self.assertEqual(MedicalDocumentRevision.objects.count(), 1)

    def test_risk_snapshot_does_not_follow_later_encounter_changes(self):
        from .encounter_services import save_primary_encounter_draft
        self.approve()
        risks = {"allergies": "Synthetic original allergy", "contraindications": "Synthetic restriction",
                 "plan_steps": [{"id": "00000000-0000-4000-8000-000000000001", "description": "Synthetic original step"}],
                 "not_applicable": {"procedures": "Synthetic consultation only"}}
        kwargs = dict(actor=self.doctor, business_id=self.business.pk, patient_id=self.patient.pk,
                      encounter_id=self.encounter_record.pk, content=risks)
        save_primary_encounter_draft(**kwargs, expected_revision=1, idempotency_key="risk-first")
        document, _ = self.save(expected_encounter_revision=2)
        before = document.snapshot_encrypted
        self.assertEqual(read_document_revision(document)["clinical"], risks)
        save_primary_encounter_draft(**(kwargs | {"content": {"allergies": "Later synthetic text"}}),
                                    expected_revision=2, idempotency_key="risk-later")
        document.refresh_from_db()
        self.assertEqual(document.snapshot_encrypted, before)
        self.assertEqual(read_document_revision(document)["clinical"], risks)

    def test_paused_template_blocks_new_use_but_preserves_saved_document(self):
        self.approve()
        document, _ = self.save()
        before = read_document_revision(document)
        set_template_availability(actor=self.head, business_id=self.business.pk,
            template_id=self.template.template_id, is_active=False, expected_revision=0,
            reason="Synthetic pause", idempotency_key="pause")
        for key in ("new-document", "source-document"):
            with self.subTest(key=key), self.assertRaises(InvalidTransition):
                self.save(idempotency_key=key)
        document.refresh_from_db()
        self.assertEqual(read_document_revision(document), before)
        self.assertEqual(MedicalDocumentRevision.objects.count(), 1)
        set_template_availability(actor=self.head, business_id=self.business.pk,
            template_id=self.template.template_id, is_active=True, expected_revision=1,
            reason="Synthetic resume", idempotency_key="resume")
        self.assertFalse(self.save(idempotency_key="after-resume")[1])

    def test_new_template_version_and_receipt_change_do_not_rewrite_document(self):
        self.approve()
        first, _ = self.save()
        before = first.snapshot_encrypted
        newer, _ = save_common_template_draft(actor=self.head, business_id=self.business.pk,
            template_id=self.template.template_id, expected_revision=1, title="New", text="New text", idempotency_key="new")
        self.approve(newer)
        second, _ = self.save(template_version_id=newer.pk, document_id=first.document_id,
            expected_document_revision=1, document_text="New edited text", idempotency_key="update")
        self.assertEqual(read_document_revision(second)["template_source"]["version_id"], newer.pk)
        MedicalTemplateReview.objects.update(decision_encrypted="changed-after-snapshot")
        first.refresh_from_db()
        self.assertEqual(first.snapshot_encrypted, before)
        self.assertEqual(read_document_revision(first)["template"]["text"], "Original {{patient}} text")

    def test_unapproved_and_corrupt_receipt_deny_creation_without_partial_audit(self):
        before = MedicalAuditEvent.objects.count()
        with self.assertRaises(PermissionDenied):
            self.save()
        self.assertEqual(MedicalAuditEvent.objects.count(), before)
        self.approve()
        MedicalTemplateReview.objects.update(decision_encrypted="corrupt")
        before = MedicalAuditEvent.objects.count()
        with self.assertRaises(MedicalDataUnavailable):
            self.save()
        self.assertEqual(MedicalAuditEvent.objects.count(), before)
        self.assertFalse(MedicalDocumentRevision.objects.exists())

    def test_private_template_of_other_author_is_not_a_document_source(self):
        personal, _ = save_personal_template_draft(actor=self.head, business_id=self.business.pk,
            title="Private", text="", idempotency_key="personal")
        submit_personal_template(actor=self.head, business_id=self.business.pk, version_id=personal.pk, idempotency_key="send")
        decide_template_review(actor=self.head, business_id=self.business.pk, version_id=personal.pk,
            decision="approved", reason="", idempotency_key="decide")
        with self.assertRaises(PermissionDenied):
            self.save(template_version_id=personal.pk)
        self.assertFalse(MedicalDocumentRevision.objects.exists())

    def test_own_approved_personal_template_can_be_used(self):
        personal, _ = save_personal_template_draft(actor=self.doctor, business_id=self.business.pk,
            title="Own", text="Own source", idempotency_key="personal")
        submit_personal_template(actor=self.doctor, business_id=self.business.pk, version_id=personal.pk, idempotency_key="send")
        decide_template_review(actor=self.head, business_id=self.business.pk, version_id=personal.pk,
            decision="approved", reason="", idempotency_key="decide")
        version, _ = self.save(template_version_id=personal.pk)
        self.assertEqual(read_document_revision(version)["template_source"]["version_id"], personal.pk)

    def test_foreign_template_is_denied_before_decryption(self):
        other = Business.objects.create(owner=self.owner, name="Foreign", slug="source-foreign")
        template = MedicalDocumentTemplate.objects.create(business=other, code="foreign", revision=1)
        foreign = MedicalDocumentTemplateRevision.objects.create(template=template, revision=1,
            author=self.head, snapshot_encrypted="must-not-decrypt")
        with self.assertRaises(PermissionDenied):
            self.save(template_version_id=foreign.pk)
        self.assertFalse(MedicalDocumentRevision.objects.exists())

    def test_conflicting_retry_and_audit_failure_do_not_change_document(self):
        self.approve()
        with patch("apps.medical.document_services.write_patient_audit", side_effect=MedicalAuditUnavailable):
            with self.assertRaises(MedicalAuditUnavailable):
                self.save()
        self.assertFalse(MedicalDocumentRevision.objects.exists())
        self.save()
        with self.assertRaises(CRMCommandConflict):
            self.save(document_text="Different text")
        self.assertEqual(MedicalDocumentRevision.objects.count(), 1)

    def test_invalid_inputs_and_current_patient_access(self):
        self.approve()
        for changes in ({"template_version_id": True}, {"document_text": None},
                        {"document_text": "x" * 131073}, {"template": {"code": "forged"}},
                        {"template_version_id": None}):
            with self.assertRaises(ValidationError):
                self.save(**changes)
        with self.assertRaises(PermissionDenied):
            self.save(actor=self.owner)
        self.save()
        self.assignment.branches.clear()
        with self.assertRaises(PermissionDenied):
            self.save()

    def test_source_schema_corruption_fails_closed(self):
        self.approve()
        version, _ = self.save()
        original = json.loads(decrypt_medical_value(version.snapshot_encrypted, business_id=self.business.pk,
            subject_id=version.pk, purpose="document_snapshot"))
        for field, value in (("revision", 9), ("version_id", True), ("approved_at", "invalid"), ("approved_by", None)):
            payload = json.loads(json.dumps(original))
            payload["snapshot"]["template_source"][field] = value
            version.snapshot_encrypted = encrypt_medical_value(json.dumps(payload), business_id=self.business.pk,
                subject_id=version.pk, purpose="document_snapshot")
            version.save(update_fields=["snapshot_encrypted"])
            with self.assertRaises(MedicalDataUnavailable):
                read_document_revision(version)
