from unittest.mock import patch

from django.test import TestCase, override_settings
from rest_framework.exceptions import PermissionDenied
from rest_framework.test import APIClient

from apps.businesses.models import Business, RolePermission
from apps.core.domain_errors import InvalidTransition
from apps.core.models import FileAttachment
from . import tests_signing_sessions as fixtures
from .audit import MedicalAuditUnavailable
from .document_finalization_services import finalize_document
from .models import MedicalDocumentFinalization
from .tests_document_rules import default_rule
from .tests_patient_services import key


@override_settings(MEDICAL_DATA_KEYS={"test": key(7)}, MEDICAL_DATA_ACTIVE_KEY_ID="test",
    MEDICAL_IDENTITY_INDEX_KEY=key(8), USE_S3=False, MEDICAL_SYNTHETIC_SIGNING_ENABLED=True, ENVIRONMENT="test")
class DocumentFinalizationTests(TestCase):
    setUpTestData = classmethod(fixtures.SigningSessionTests.setUpTestData.__func__)
    setUp = fixtures.SigningSessionTests.setUp
    rules = fixtures.SigningSessionTests.rules
    save = fixtures.SigningSessionTests.save
    prepare = fixtures.SigningSessionTests.prepare
    change = fixtures.SigningSessionTests.change
    confirm = fixtures.SigningSessionTests.confirm
    render = fixtures.SigningSessionTests.render
    start = fixtures.SigningSessionTests.start
    advance = fixtures.SigningSessionTests.advance

    def finalize(self, **changes):
        return finalize_document(**(dict(actor=self.doctor, business_id=self.business.pk, patient_id=self.patient.pk,
            version_id=self.version.pk, artifact_id=self.artifact.pk, expected_state_revision=3,
            appointment_id=self.appointment.pk, idempotency_key="finalize") | changes))

    def sign_all(self):
        session, _ = self.start()
        session, _ = self.advance(session)
        session, _ = self.advance(session, actor=self.head, appointment_id=None, head_branch_id=self.first.pk)
        return self.advance(session)[0]

    def no_signers(self):
        self.rules(kind_id=self.rule_version.kind_id, expected_revision=1, idempotency_key="no-signatures", content={"name": "Synthetic unsigned final document", "services": [],
            "default": default_rule(reviewers=["primary_clinician", "medical_head"])})
        self.version = self.save(idempotency_key="no-signature-document")
        self.change(idempotency_key="no-signature-submit")
        self.confirm(idempotency_key="no-signature-head")
        self.change(target="reviewed", expected_state_revision=2, idempotency_key="no-signature-primary")
        self.artifact, _ = self.render()
        FileAttachment.objects.filter(pk=self.artifact.attachment_id).update(scan_status="clean", scan_sha256=self.artifact.sha256)

    def test_missing_signature_blocks_without_losing_document(self):
        with self.assertRaises(InvalidTransition):
            self.finalize()
        self.assertFalse(MedicalDocumentFinalization.objects.exists())
        self.version.document.refresh_from_db()
        self.assertEqual(self.version.document.state, "reviewed")

    def test_all_signatures_exact_pdf_replay_and_return_denied(self):
        session = self.sign_all()
        item, replayed = self.finalize()
        self.assertFalse(replayed)
        self.assertEqual(item.signing_session_id, session.pk)
        self.assertEqual(item.artifact_id, session.artifact_id)
        self.assertEqual(self.finalize()[0].pk, item.pk)
        self.assertTrue(self.finalize()[1])
        self.version.document.refresh_from_db()
        self.assertEqual(self.version.document.state, "finalized")
        with self.assertRaises(InvalidTransition):
            self.change(target="draft", expected_state_revision=4, reason="Must use correction", idempotency_key="return-final")

    def test_document_without_required_signatures_finalizes_without_session(self):
        self.no_signers()
        item, _ = self.finalize()
        self.assertIsNone(item.signing_session_id)
        self.assertEqual(item.version_id, self.version.pk)

    def test_wrong_actor_stale_revision_and_revoked_permission(self):
        self.sign_all()
        with self.assertRaises(PermissionDenied):
            self.finalize(actor=self.head, appointment_id=None, head_branch_id=self.first.pk)
        with self.assertRaises(InvalidTransition):
            self.finalize(expected_state_revision=2)
        RolePermission.objects.filter(business_role=self.role, resource="medical_documents", action="sign").update(is_allowed=False)
        with self.assertRaises(PermissionDenied):
            self.finalize()
        self.assertFalse(MedicalDocumentFinalization.objects.exists())

    def test_audit_failure_rolls_back_finalization_and_state(self):
        self.no_signers()
        with patch("apps.medical.document_finalization_services.write_patient_audit", side_effect=MedicalAuditUnavailable):
            with self.assertRaises(MedicalAuditUnavailable):
                self.finalize()
        self.assertFalse(MedicalDocumentFinalization.objects.exists())
        self.version.document.refresh_from_db()
        self.assertEqual(self.version.document.state, "reviewed")

    def test_tenant_branch_and_revoked_replay(self):
        self.no_signers()
        foreign = Business.objects.create(owner=self.owner, name="Finalization foreign", slug="finalization-foreign")
        for changes in ({"business_id": foreign.pk}, {"actor": self.head, "appointment_id": None, "head_branch_id": self.second.pk}):
            with self.assertRaises(PermissionDenied):
                self.finalize(**changes)
        self.finalize()
        RolePermission.objects.filter(business_role=self.role, resource="medical_documents", action="update").update(is_allowed=False)
        with self.assertRaises(PermissionDenied):
            self.finalize()

    def test_finalization_evidence_is_bound_to_actor(self):
        from .document_finalization_services import finalization_evidence
        from .identity_crypto import MedicalDataUnavailable
        self.no_signers()
        item, _ = self.finalize()
        self.assertTrue(finalization_evidence(item)["synthetic"])
        item.actor = self.head
        with self.assertRaises(MedicalDataUnavailable):
            finalization_evidence(item)

    def test_http_final_state_preserves_head_review_and_view_only_pdf(self):
        self.no_signers()
        api = APIClient(); api.force_authenticate(self.doctor)
        root = f"/api/medical/documents/versions/{self.version.pk}/"
        scope = dict(business_id=self.business.pk, patient_id=self.patient.pk, appointment_id=self.appointment.pk)
        response = api.post(root + "finalize/", scope | {"artifact_id": self.artifact.pk, "expected_state_revision": 3},
            format="json", HTTP_IDEMPOTENCY_KEY="http-finalize")
        self.assertEqual(response.status_code, 200, response.data)
        self.assertTrue(response.data["synthetic"])
        review = api.get(root + "review/", scope)
        self.assertEqual(review.data["document_state"], "finalized")
        self.assertFalse(review.data["can_transition"])
        self.assertIsNotNone(api.get(root + "head-review/", scope).data["confirmation"])
        state = api.get(root + "signing/", scope | {"language": "kk"})
        self.assertEqual(state.status_code, 200, state.data)
        self.assertFalse(state.data["can_finalize"])
        self.assertEqual(state.data["finalization"]["artifact_id"], self.artifact.pk)
        RolePermission.objects.filter(business_role=self.role, resource="medical_documents", action="sign").update(is_allowed=False)
        self.assertEqual(api.get(root + "signing-pdf/", scope | {"artifact_id": self.artifact.pk}).status_code, 200)
        RolePermission.objects.filter(business_role=self.role, resource="medical_documents", action="view").update(is_allowed=False)
        self.assertEqual(api.get(root + "signing-pdf/", scope | {"artifact_id": self.artifact.pk}).status_code, 403)
