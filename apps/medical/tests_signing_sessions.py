from unittest.mock import patch

from django.test import TestCase, override_settings
from rest_framework.exceptions import NotFound, PermissionDenied
from rest_framework.test import APIClient

from apps.businesses.models import Business, RolePermission
from apps.core.domain_errors import InvalidTransition
from apps.core.models import FileAttachment
from apps.core.file_scanning import FileQuarantined
from .audit import MedicalAuditUnavailable
from .models import MedicalSigningSession, MedicalSigningEvent
from .signing_services import start_synthetic_signing, advance_synthetic_signing
from .tests_document_signing_pdf import DocumentSigningPDFTests
from .tests_document_rules import default_rule
from .identity_crypto import MedicalDataUnavailable


from .tests_patient_services import key


@override_settings(MEDICAL_DATA_KEYS={"test": key(7)}, MEDICAL_DATA_ACTIVE_KEY_ID="test",
                   MEDICAL_IDENTITY_INDEX_KEY=key(8), USE_S3=False, MEDICAL_SYNTHETIC_SIGNING_ENABLED=True, ENVIRONMENT="test")
class SigningSessionTests(TestCase):
    setUpTestData = classmethod(DocumentSigningPDFTests.setUpTestData.__func__)
    rules = DocumentSigningPDFTests.rules
    save = DocumentSigningPDFTests.save
    def prepare(self):
        self.rule_version = self.rules(content={"name": "Synthetic ordered signature test", "services": [], "default": default_rule(
            reviewers=["primary_clinician", "medical_head"], signers=["primary_clinician", "medical_head", "patient_or_representative"])})
        self.version = self.save()
        self.change()

    change = DocumentSigningPDFTests.change
    confirm = DocumentSigningPDFTests.confirm
    render = DocumentSigningPDFTests.render
    def setUp(self):
        DocumentSigningPDFTests.setUp(self)
        self.confirm()
        self.change(target="reviewed", expected_state_revision=2, idempotency_key="signing-primary")
        self.artifact, _ = self.render()
        FileAttachment.objects.filter(pk=self.artifact.attachment_id).update(scan_status="clean", scan_sha256=self.artifact.sha256)
        RolePermission.objects.create(business_role=self.head_assignment.business_role, resource="medical_documents",
            action="sign", scope="business", is_allowed=True)

    def start(self, **changes):
        return start_synthetic_signing(**(dict(actor=self.doctor, business_id=self.business.pk,
            patient_id=self.patient.pk, version_id=self.version.pk, artifact_id=self.artifact.pk,
            appointment_id=self.appointment.pk, idempotency_key="start") | changes))

    def advance(self, session, **changes):
        return advance_synthetic_signing(**(dict(actor=self.doctor, business_id=self.business.pk,
            patient_id=self.patient.pk, version_id=self.version.pk, session_id=session.pk,
            appointment_id=self.appointment.pk, expected_revision=session.revision, action="sign",
            idempotency_key=f"sign-{session.revision}") | changes))

    def test_ordered_signing_replay_and_completed_session_rejects_late_change(self):
        session, replayed = self.start()
        self.assertFalse(replayed)
        self.assertEqual(self.start()[0].pk, session.pk)
        session, _ = self.advance(session)
        with self.assertRaises(PermissionDenied):
            self.advance(session)
        session, _ = self.advance(session, actor=self.head, appointment_id=None, head_branch_id=self.first.pk)
        session, _ = self.advance(session)
        self.assertEqual(session.state, "completed")
        self.assertEqual(list(session.events.filter(action="signed").order_by("position").values_list("signer", flat=True)),
            ["primary_clinician", "medical_head", "patient_or_representative"])
        with self.assertRaises(InvalidTransition):
            self.advance(session)

    def test_cancel_and_stale_revision_never_sign(self):
        session, _ = self.start()
        with self.assertRaises(InvalidTransition):
            self.advance(session, expected_revision=2)
        session, _ = self.advance(session, action="cancel", idempotency_key="cancel")
        self.assertEqual(session.state, "cancelled")
        with self.assertRaises(InvalidTransition):
            self.advance(session)
        self.assertFalse(session.events.filter(action="signed").exists())

    def test_revocation_and_tenant_boundary(self):
        session, _ = self.start()
        other = Business.objects.create(name="Independent signing tenant", owner=self.owner)
        with self.assertRaises((PermissionDenied, NotFound)):
            self.advance(session, business_id=other.pk)
        RolePermission.objects.filter(business_role=self.role, resource="medical_documents", action="sign").update(is_allowed=False)
        with self.assertRaises(PermissionDenied):
            self.advance(session)
        self.assertEqual(session.events.count(), 1)

    def test_rollback_and_disabled_production(self):
        with patch("apps.medical.signing_services.write_patient_audit", side_effect=MedicalAuditUnavailable):
            with self.assertRaises(MedicalAuditUnavailable):
                self.start()
        self.assertFalse(MedicalSigningSession.objects.exists())
        self.assertFalse(MedicalSigningEvent.objects.exists())
        with override_settings(ENVIRONMENT="production"):
            with self.assertRaises(PermissionDenied):
                self.start()

    def test_review_return_invalidates_pending_signing(self):
        session, _ = self.start()
        self.change(target="draft", expected_state_revision=3, reason="Correction after signing start", idempotency_key="return-signing")
        with self.assertRaises(InvalidTransition):
            self.advance(session)

    def test_quarantine_and_changed_bytes_cannot_sign(self):
        FileAttachment.objects.filter(pk=self.artifact.attachment_id).update(scan_status="pending")
        with self.assertRaises(FileQuarantined):
            self.start()
        self.assertFalse(MedicalSigningSession.objects.exists())
        FileAttachment.objects.filter(pk=self.artifact.attachment_id).update(scan_status="clean")
        session, _ = self.start()
        with self.artifact.attachment.file.open("wb") as target:
            target.write(b"altered")
        with self.assertRaises(FileQuarantined):
            self.advance(session)
        self.artifact.attachment.refresh_from_db()
        self.assertEqual(self.artifact.attachment.scan_status, "error")
        self.assertEqual(session.events.count(), 1)

    def test_http_private_strict_state_commands_and_revocation(self):
        api = APIClient(); api.force_authenticate(self.doctor)
        root = f"/api/medical/documents/versions/{self.version.pk}/"
        scope = dict(business_id=self.business.pk, patient_id=self.patient.pk, appointment_id=self.appointment.pk)
        response = api.get(root + "signing/", scope | {"language": "ru"})
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response["Cache-Control"], "no-store, private")
        self.assertTrue(response.data["can_start"])
        preview = api.get(root + "signing-pdf/", scope | {"artifact_id": self.artifact.pk})
        self.assertEqual(preview.status_code, 200)
        import hashlib
        self.assertEqual(hashlib.sha256(preview.content).hexdigest(), self.artifact.sha256)
        self.assertEqual(preview["Cache-Control"], "no-store, private")
        payload = scope | {"artifact_id": self.artifact.pk}
        self.assertEqual(api.post(root + "start-signing/", payload | {"signed": True}, format="json").status_code, 400)
        response = api.post(root + "start-signing/", payload, format="json", HTTP_IDEMPOTENCY_KEY="http-start")
        self.assertEqual(response.status_code, 200, response.data)
        session = response.data
        response = api.post(root + "advance-signing/", scope | {"session_id": session["id"], "expected_revision": 1, "action": "sign"},
            format="json", HTTP_IDEMPOTENCY_KEY="http-sign")
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data["revision"], 2)
        self.assertEqual(api.post(root + "advance-signing/", scope | {"session_id": "bad", "expected_revision": 2, "action": "sign"}, format="json").status_code, 400)
        api.force_authenticate(self.owner)
        self.assertEqual(api.get(root + "signing/", scope | {"language": "ru"}).status_code, 403)
        self.assertEqual(api.get(root + "signing-pdf/", scope | {"artifact_id": self.artifact.pk}).status_code, 403)

    def test_encrypted_event_binding_rejects_changed_actor(self):
        session, _ = self.start()
        session.events.update(actor=self.head)
        with self.assertRaises(MedicalDataUnavailable):
            self.advance(session)
        session.refresh_from_db()
        self.assertEqual(session.revision, 1)

    def test_forged_completion_without_signature_evidence_is_rejected(self):
        from django.utils import timezone
        from .signing_services import assert_signing_evidence
        session, _ = self.start()
        MedicalSigningSession.objects.filter(pk=session.pk).update(state="completed", ended_at=timezone.now())
        session.refresh_from_db()
        with self.assertRaises(MedicalDataUnavailable):
            assert_signing_evidence(session)
