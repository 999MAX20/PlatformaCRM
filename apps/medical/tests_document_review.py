from unittest.mock import patch

from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.test import APIClient

from apps.businesses.models import Business, RolePermission
from apps.core.domain_errors import InvalidTransition
from . import tests_document_artifact_access as fixtures
from .audit import MedicalAuditUnavailable
from .document_content import append_document_revision
from .document_review_services import read_document_review, transition_document_review
from .identity_crypto import MedicalDataUnavailable, decrypt_medical_value
from .models import MedicalAuditEvent, MedicalDocumentReviewTransition
from .tests_patient_services import key


@override_settings(MEDICAL_DATA_KEYS={"test": key(7)}, MEDICAL_DATA_ACTIVE_KEY_ID="test",
                   MEDICAL_IDENTITY_INDEX_KEY=key(8))
class DocumentReviewTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        fixtures.DocumentArtifactAccessTests.setUpTestData.__func__(cls)

    def setUp(self):
        fixtures.DocumentArtifactAccessTests.setUp(self)

    def change(self, **changes):
        return transition_document_review(**({"actor": self.doctor, "business_id": self.business.pk,
            "patient_id": self.patient.pk, "version_id": self.version.pk, "appointment_id": self.appointment.pk,
            "expected_state_revision": 1, "target": "ready_for_review", "reason": "",
            "idempotency_key": "review-submit"} | changes))

    def append(self):
        self.version.document.refresh_from_db()
        return append_document_revision(document=self.version.document, source_version=self.first_version,
            author=self.doctor, template={"code": "synthetic", "version": 1, "title": "Synthetic", "text": "Changed"})

    def test_submit_replay_return_preserves_bytes_and_blocks_edit(self):
        snapshot = self.version.snapshot_encrypted
        event, replayed = self.change()
        self.assertFalse(replayed)
        self.assertEqual((event.state, event.state_revision), ("ready_for_review", 2))
        with self.assertRaises(InvalidTransition):
            self.append()
        replay, replayed = self.change()
        self.assertTrue(replayed)
        self.assertEqual(replay.pk, event.pk)
        returned, _ = self.change(target="draft", expected_state_revision=2,
            reason="Private clinical correction", idempotency_key="return")
        self.assertEqual(returned.state_revision, 3)
        self.assertNotIn("Private", returned.reason_encrypted)
        self.assertEqual(decrypt_medical_value(returned.reason_encrypted, business_id=self.business.pk,
            subject_id=returned.pk, purpose="document_review_reason"), "Private clinical correction")
        self.version.refresh_from_db()
        self.assertEqual(self.version.snapshot_encrypted, snapshot)
        self.assertEqual(self.append().revision, 2)
        self.assertEqual(MedicalAuditEvent.objects.filter(action__startswith="document_review_").count(), 2)

    def test_stale_state_and_version_cannot_submit(self):
        self.change()
        self.change(target="draft", expected_state_revision=2, reason="Return", idempotency_key="return")
        with self.assertRaises(InvalidTransition):
            self.change(idempotency_key="stale")
        self.append()
        with self.assertRaises(InvalidTransition):
            self.change(expected_state_revision=3, idempotency_key="old-version")

    def test_participation_basis_can_submit(self):
        transition, _ = self.change(appointment_id=None, participation_id=self.participation.pk)
        self.assertEqual(transition.state, "ready_for_review")

    def test_confirmation_is_exact_version_not_signature_and_return_removes_current_confirmation(self):
        snapshot = self.version.snapshot_encrypted
        with self.assertRaises(InvalidTransition):
            self.change(target="reviewed", idempotency_key="early")
        self.change()
        confirmed, replayed = self.change(target="reviewed", expected_state_revision=2, idempotency_key="confirm")
        self.assertFalse(replayed)
        self.assertEqual((confirmed.state, confirmed.state_revision), ("reviewed", 3))
        self.assertEqual(self.change(target="reviewed", expected_state_revision=2, idempotency_key="confirm")[0].pk, confirmed.pk)
        with self.assertRaises(InvalidTransition):
            self.append()
        with self.assertRaises(InvalidTransition):
            self.change(target="reviewed", expected_state_revision=2, idempotency_key="stale-confirm")
        self.assertEqual(MedicalAuditEvent.objects.filter(action="document_review_confirmed").count(), 1)
        self.change(target="draft", expected_state_revision=3, idempotency_key="reopen", reason="Correction needed")
        self.version.document.refresh_from_db()
        self.assertEqual(self.version.document.state, "draft")
        self.assertTrue(MedicalDocumentReviewTransition.objects.filter(pk=confirmed.pk, state="reviewed").exists())
        self.version.refresh_from_db()
        self.assertEqual(self.version.snapshot_encrypted, snapshot)
        self.assertEqual(self.append().revision, 2)

    def test_confirmation_denied_after_role_revocation_and_rolls_back_on_audit_failure(self):
        self.change()
        with patch("apps.medical.document_review_services.write_patient_audit", side_effect=MedicalAuditUnavailable):
            with self.assertRaises(MedicalAuditUnavailable):
                self.change(target="reviewed", expected_state_revision=2, idempotency_key="confirm")
        self.version.document.refresh_from_db()
        self.assertEqual(self.version.document.state, "ready_for_review")
        self.assertFalse(MedicalDocumentReviewTransition.objects.filter(state="reviewed").exists())
        self.assignment.revoked_at = timezone.now()
        self.assignment.save(update_fields=["revoked_at"])
        with self.assertRaises(PermissionDenied):
            self.change(target="reviewed", expected_state_revision=2, idempotency_key="confirm")

    def test_owner_other_tenant_and_branch_denied(self):
        foreign = Business.objects.create(owner=self.owner, name="Other review", slug="review-other")
        for changes in ({"actor": self.owner}, {"actor": self.head}, {"business_id": foreign.pk},
                        {"version_id": self.version.pk + 100000}):
            with self.assertRaises(PermissionDenied):
                self.change(**changes)
        self.encounter_record.branch = self.second
        self.encounter_record.save(update_fields=["branch"])
        with self.assertRaises(PermissionDenied):
            self.change()
        self.assertFalse(MedicalDocumentReviewTransition.objects.exists())

    def test_revocation_and_update_permission_denied_even_on_replay(self):
        self.change()
        RolePermission.objects.filter(business_role=self.role, resource="medical_documents", action="update").update(is_allowed=False)
        with self.assertRaises(PermissionDenied):
            self.change()
        RolePermission.objects.filter(business_role=self.role, resource="medical_documents", action="update").update(is_allowed=True)
        self.assignment.revoked_at = timezone.now()
        self.assignment.save(update_fields=["revoked_at"])
        with self.assertRaises(PermissionDenied):
            self.change()

    def test_audit_failure_rolls_back_transition(self):
        with patch("apps.medical.document_review_services.write_patient_audit", side_effect=MedicalAuditUnavailable):
            with self.assertRaises(MedicalAuditUnavailable):
                self.change()
        self.version.document.refresh_from_db()
        self.assertEqual((self.version.document.state, self.version.document.state_revision), ("draft", 1))
        self.assertFalse(MedicalDocumentReviewTransition.objects.exists())
        self.assertFalse(self.change()[1])

    def test_return_reason_and_supported_targets_required(self):
        for changes in ({"target": "signed"}, {"target": "draft", "reason": " "},
                        {"expected_state_revision": True}, {"idempotency_key": ""}):
            with self.assertRaises(ValidationError):
                self.change(**changes)

    def test_current_read_bases_history_reason_and_read_audit_failure(self):
        self.change()
        self.change(target="draft", expected_state_revision=2, reason="Synthetic return", idempotency_key="return")
        for basis, actor in (({"appointment_id": self.appointment.pk}, self.doctor),
                ({"participation_id": self.participation.pk}, self.doctor),
                ({"correction_access_id": self.document_grant.pk}, self.doctor),
                ({"head_branch_id": self.first.pk}, self.head)):
            scope = {"actor": actor, "business_id": self.business.pk, "patient_id": self.patient.pk,
                "version_id": self.version.pk, **basis}
            result = read_document_review(**scope, limit=1)
            self.assertEqual(result["document_state"], "draft")
            self.assertEqual(result["results"][0]["reason"], "Synthetic return")
            self.assertEqual(result["can_transition"], "appointment_id" in basis or "participation_id" in basis)
            page = read_document_review(**scope, before_id=result["next_before_id"])
            self.assertEqual([event["state"] for event in page["results"]], ["ready_for_review"])
            with patch("apps.medical.document_review_services.write_patient_audit", side_effect=MedicalAuditUnavailable):
                with self.assertRaises(MedicalAuditUnavailable):
                    read_document_review(**scope)

    def test_http_requires_current_scope_and_rejects_signature_or_head_override(self):
        api = APIClient(); api.force_authenticate(self.doctor)
        path = f"/api/medical/documents/versions/{self.version.pk}/"
        scope = {"business_id": self.business.pk, "patient_id": self.patient.pk, "appointment_id": self.appointment.pk}
        payload = {**scope, "target": "ready_for_review", "expected_state_revision": 1}
        response = api.post(path + "review-transition/", payload, format="json", HTTP_IDEMPOTENCY_KEY="http")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Cache-Control"], "no-store, private")
        self.assertEqual(response.data["state"], "ready_for_review")
        self.assertEqual(api.get(path + "review/", scope).data["document_state"], "ready_for_review")
        confirmed = api.post(path + "review-transition/", payload | {"target": "reviewed", "expected_state_revision": 2},
            format="json", HTTP_IDEMPOTENCY_KEY="http-confirm")
        self.assertEqual(confirmed.status_code, 200)
        self.assertEqual(confirmed.data["state"], "reviewed")
        self.assertEqual(api.post(path + "review-transition/", payload | {"signed": True}, format="json").status_code, 400)
        api.force_authenticate(self.head)
        self.assertEqual(api.post(path + "review-transition/", payload, format="json", HTTP_IDEMPOTENCY_KEY="head").status_code, 403)
        self.assertTrue(MedicalAuditEvent.objects.filter(action="access_denied", actor=self.head).exists())

    def test_encrypted_return_reason_cannot_be_transplanted_to_another_transition(self):
        first, _ = self.change()
        second, _ = self.change(target="draft", expected_state_revision=2, reason="Private reason", idempotency_key="return")
        MedicalDocumentReviewTransition.objects.filter(pk=first.pk).update(reason_encrypted=second.reason_encrypted)
        with self.assertRaises(MedicalDataUnavailable):
            read_document_review(actor=self.doctor, business_id=self.business.pk, patient_id=self.patient.pk,
                version_id=self.version.pk, appointment_id=self.appointment.pk)
