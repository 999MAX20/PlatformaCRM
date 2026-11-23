from datetime import timedelta
from unittest.mock import patch

from django.test import TestCase, override_settings
from rest_framework.exceptions import PermissionDenied, NotFound
from rest_framework.test import APIClient

from apps.businesses.models import Business, RolePermission
from apps.core.domain_errors import InvalidTransition
from apps.core.models import FileAttachment
from . import tests_document_finalization as fixtures
from .audit import MedicalAuditUnavailable
from .document_corrections import correct_final_document, correction_source
from .document_content import read_document_revision
from .document_finalization_services import finalization_evidence
from .document_review_services import read_document_review
from .models import MedicalDocumentCorrection, MedicalDocumentRevision
from .tests_patient_services import key


@override_settings(MEDICAL_DATA_KEYS={"test": key(7)}, MEDICAL_DATA_ACTIVE_KEY_ID="test",
    MEDICAL_IDENTITY_INDEX_KEY=key(8), USE_S3=False, MEDICAL_SYNTHETIC_SIGNING_ENABLED=True, ENVIRONMENT="test")
class FinalDocumentCorrectionTests(TestCase):
    setUpTestData = classmethod(fixtures.DocumentFinalizationTests.setUpTestData.__func__)
    setUp = fixtures.DocumentFinalizationTests.setUp
    rules = fixtures.DocumentFinalizationTests.rules
    save = fixtures.DocumentFinalizationTests.save
    prepare = fixtures.DocumentFinalizationTests.prepare
    change = fixtures.DocumentFinalizationTests.change
    confirm = fixtures.DocumentFinalizationTests.confirm
    render = fixtures.DocumentFinalizationTests.render
    def start(self, **changes):
        return fixtures.DocumentFinalizationTests.start(self, **({"idempotency_key": f"start-{self.version.pk}"} | changes))

    def advance(self, session, **changes):
        return fixtures.DocumentFinalizationTests.advance(self, session,
            **({"idempotency_key": f"advance-{session.pk}-{session.revision}"} | changes))
    finalize = fixtures.DocumentFinalizationTests.finalize
    sign_all = fixtures.DocumentFinalizationTests.sign_all
    no_signers = fixtures.DocumentFinalizationTests.no_signers

    def correct(self, **changes):
        return correct_final_document(**(dict(actor=self.doctor, business_id=self.business.pk,
            patient_id=self.patient.pk, version_id=self.version.pk, appointment_id=self.appointment.pk,
            expected_state_revision=4, document_text="Corrected synthetic text", reason="Correct a transcription",
            idempotency_key="correct-final") | changes))

    def test_original_proof_and_bytes_preserved_new_version_requires_whole_cycle(self):
        self.sign_all(); original, _ = self.finalize()
        old = self.version; snapshot = read_document_revision(old); proof = original.evidence_encrypted
        with self.artifact.attachment.file.open("rb") as stream:
            original_bytes = stream.read()
        self.version, replayed = self.correct()
        self.assertFalse(replayed)
        self.assertEqual(correction_source(self.version).pk, original.pk)
        self.assertEqual(read_document_revision(old), snapshot)
        self.assertEqual(finalization_evidence(original)["version_id"], old.pk)
        original.refresh_from_db(); self.assertEqual(original.evidence_encrypted, proof)
        with original.artifact.attachment.file.open("rb") as stream:
            self.assertEqual(stream.read(), original_bytes)
        with self.assertRaises(InvalidTransition):
            self.render()
        with self.assertRaises(NotFound):
            self.finalize(expected_state_revision=5, idempotency_key="premature")
        self.change(expected_state_revision=5, idempotency_key="correct-submit")
        self.change(expected_state_revision=6, target="reviewed", idempotency_key="correct-reviewed")
        with self.assertRaises(InvalidTransition):
            self.render()
        self.confirm(expected_state_revision=7, idempotency_key="correct-head")
        self.artifact, _ = self.render()
        FileAttachment.objects.filter(pk=self.artifact.attachment_id).update(scan_status="clean", scan_sha256=self.artifact.sha256)
        self.assertNotEqual(self.artifact.pk, original.artifact_id)
        self.sign_all()
        new, _ = self.finalize(expected_state_revision=7, idempotency_key="correct-finalized")
        self.assertNotEqual(new.pk, original.pk)
        again, _ = self.correct(expected_state_revision=8, idempotency_key="correct-again")
        self.assertEqual(correction_source(again).pk, new.pk)

    def test_replay_stale_and_rollback(self):
        self.no_signers(); self.finalize()
        count = MedicalDocumentRevision.objects.count()
        with patch("apps.medical.document_corrections.write_patient_audit", side_effect=MedicalAuditUnavailable):
            with self.assertRaises(MedicalAuditUnavailable): self.correct()
        self.assertEqual(MedicalDocumentRevision.objects.count(), count)
        self.assertFalse(MedicalDocumentCorrection.objects.exists())
        self.version.document.refresh_from_db(); self.assertEqual(self.version.document.state, "finalized")
        new, _ = self.correct()
        self.assertTrue(self.correct()[1])
        with self.assertRaises(InvalidTransition): self.correct(idempotency_key="stale")
        self.assertEqual(MedicalDocumentRevision.objects.count(), count + 1)
        self.assertEqual(correction_source(new).version_id, self.version.pk)

    def test_corrective_edit_keeps_lineage_and_rejects_snapshot_replacement(self):
        self.no_signers(); original, _ = self.finalize()
        self.version, _ = self.correct()
        before = read_document_revision(self.version)
        with self.assertRaises(InvalidTransition):
            self.save(document_id=self.version.document_id, expected_document_revision=self.version.revision,
                document_text="Must not replace frozen source", reason="Try ordinary editor", idempotency_key="wrong-editor")
        edited, _ = self.correct(expected_state_revision=5, document_text="Second corrective draft", idempotency_key="edit-correction")
        self.assertEqual(correction_source(edited).pk, original.pk)
        after = read_document_revision(edited)
        for field in set(before) - {"reason", "document_text", "prepared_by"}:
            self.assertEqual(before[field], after[field], field)
        from .identity_crypto import MedicalDataUnavailable
        MedicalDocumentCorrection.objects.filter(version=edited).update(evidence_encrypted="tampered")
        with self.assertRaises(MedicalDataUnavailable): correction_source(edited)

    def test_access_tenant_branch_and_revoked_replay(self):
        self.no_signers(); self.finalize()
        other = Business.objects.create(owner=self.owner, name="Independent correction tenant")
        for changes in ({"business_id": other.pk}, {"actor": self.head, "appointment_id": None, "head_branch_id": self.first.pk}):
            with self.assertRaises(PermissionDenied): self.correct(**changes)
        self.assignment.branches.remove(self.first)
        with self.assertRaises(PermissionDenied): self.correct()
        self.assignment.branches.add(self.first)
        self.correct()
        RolePermission.objects.filter(business_role=self.role, resource="medical_documents", action="update").update(is_allowed=False)
        with self.assertRaises(PermissionDenied): self.correct()

    def test_http_old_final_state_and_new_corrective_draft(self):
        self.no_signers(); self.finalize()
        api = APIClient(); api.force_authenticate(self.doctor)
        scope = dict(business_id=self.business.pk, patient_id=self.patient.pk, appointment_id=self.appointment.pk)
        root = f"/api/medical/documents/versions/{self.version.pk}/"
        response = api.post(root + "correction/", scope | {"expected_state_revision": 4,
            "document_text": "Corrected HTTP text", "reason": "Correction"}, format="json", HTTP_IDEMPOTENCY_KEY="http-correction")
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response["Cache-Control"], "no-store, private")
        self.assertEqual(api.get(root, scope).data["state"], "finalized")
        self.assertEqual(api.get(root + "review/", scope).data["document_state"], "finalized")
        self.assertIsNotNone(api.get(root + "head-review/", scope).data["confirmation"])
        new = api.get(f'/api/medical/documents/versions/{response.data["version_id"]}/review/', scope)
        self.assertEqual(new.data["document_state"], "draft")
        self.assertTrue(new.data["can_transition"])
        self.assertTrue(new.data["can_correct"])

    def test_completed_encounter_uses_exact_24h_grant_and_expiry(self):
        from .correction_access_services import request_correction_access, review_correction_access
        from .correction_access_writes import save_correction_target
        self.no_signers(); self.finalize()
        RolePermission.objects.get_or_create(business_role=self.head_assignment.business_role, resource="medical_records",
            action="manage", defaults={"scope": "business", "is_allowed": True})
        grant, _ = request_correction_access(actor=self.doctor, business_id=self.business.pk,
            encounter_id=self.version.document.encounter_id, document_id=self.version.document_id,
            expected_patient_revision=self.patient.revision, expected_target_revision=self.version.revision,
            reason="Correct finalized text", idempotency_key="request-correct-final")
        grant, _ = review_correction_access(actor=self.head, business_id=self.business.pk, request_id=grant.pk,
            expected_revision=1, decision="approve", reason="Exact document only", idempotency_key="grant-correct-final")
        encounter = self.version.document.encounter
        from .encounter_content import CLINICAL_FIELDS
        from .encounter_services import save_primary_encounter_draft
        from .encounter_completion import complete_primary_encounter
        clinical, _ = save_primary_encounter_draft(actor=self.doctor, business_id=self.business.pk,
            patient_id=self.patient.pk, encounter_id=encounter.pk, expected_revision=encounter.revision,
            content={field: "Synthetic completed care" for field in CLINICAL_FIELDS}, idempotency_key="fill-final")
        self.appointment.refresh_from_db()
        complete_primary_encounter(actor=self.doctor, business_id=self.business.pk, patient_id=self.patient.pk,
            encounter_id=encounter.pk, expected_revision=clinical.revision,
            expected_appointment_updated_at=self.appointment.updated_at, reason="Synthetic early finish",
            idempotency_key="complete-before-correction")
        args = dict(actor=self.doctor, business_id=self.business.pk, request_id=grant.pk, expected_revision=self.version.revision,
            document_text="Corrected after completion", reason="Transcription", idempotency_key="timed-final")
        self.version, _ = save_correction_target(**args)
        basis = dict(appointment_id=None, correction_access_id=grant.pk)
        self.change(expected_state_revision=5, idempotency_key="timed-submit", **basis)
        self.confirm(expected_state_revision=6, idempotency_key="timed-head")
        self.change(expected_state_revision=6, target="reviewed", idempotency_key="timed-review", **basis)
        self.artifact, _ = self.render(**basis)
        FileAttachment.objects.filter(pk=self.artifact.attachment_id).update(scan_status="clean", scan_sha256=self.artifact.sha256)
        self.finalize(expected_state_revision=7, idempotency_key="timed-finalize", **basis)
        self.assertEqual(grant.expires_at - grant.reviewed_at, timedelta(hours=24))
        with patch("apps.medical.correction_access_context.timezone.now", return_value=grant.expires_at):
            with self.assertRaises(PermissionDenied): save_correction_target(**args)
