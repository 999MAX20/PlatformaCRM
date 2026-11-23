from datetime import timedelta
from unittest.mock import patch

from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied, Throttled

from apps.businesses.models import Business, RolePermission
from apps.core.domain_errors import InvalidTransition
from . import tests_document_finalization as fixtures
from .audit import MedicalAuditUnavailable
from .issuance_services import create_document_grant, transition_document_grant
from .issuance_portal import login_portal, portal_documents, portal_pdf
from .models import MedicalDocumentGrant, MedicalDocumentGrantEvent
from .tests_document_rules import default_rule
from .tests_patient_services import key


@override_settings(MEDICAL_DATA_KEYS={"test": key(7)}, MEDICAL_DATA_ACTIVE_KEY_ID="test",
    MEDICAL_IDENTITY_INDEX_KEY=key(8), USE_S3=False, MEDICAL_SYNTHETIC_SIGNING_ENABLED=True,
    MEDICAL_SYNTHETIC_ISSUANCE_ENABLED=True, ENVIRONMENT="test")
class DocumentIssuanceTests(TestCase):
    setUpTestData = classmethod(fixtures.DocumentFinalizationTests.setUpTestData.__func__)
    rules, save = fixtures.DocumentFinalizationTests.rules, fixtures.DocumentFinalizationTests.save
    change, confirm, render = fixtures.DocumentFinalizationTests.change, fixtures.DocumentFinalizationTests.confirm, fixtures.DocumentFinalizationTests.render
    finalize = fixtures.DocumentFinalizationTests.finalize

    def prepare(self):
        self.rule_version = self.rules(content={"name": "Synthetic issuable document", "services": [],
            "default": default_rule(issuable=True, reviewers=["primary_clinician", "medical_head"])})
        self.version = self.save()
        self.change()

    def setUp(self):
        fixtures.DocumentFinalizationTests.setUp(self)
        RolePermission.objects.create(business_role=self.role, resource="medical_documents", action="issue", scope="own")

    def create(self, **changes):
        return create_document_grant(**(dict(actor=self.doctor, business_id=self.business.pk, patient_id=self.patient.pk,
            branch_id=self.first.pk, encounter_id=self.encounter_record.pk, version_ids=[self.version.pk],
            personally_verified=True, verification_reason="Synthetic personal document check", idempotency_key="grant") | changes))

    def activate(self, grant, **changes):
        return transition_document_grant(**(dict(actor=self.doctor, business_id=self.business.pk, patient_id=self.patient.pk,
            branch_id=self.first.pk, grant_id=grant.pk, expected_revision=grant.revision, action="activate", reason="",
            idempotency_key="activate") | changes))

    def login(self, code, **changes):
        return login_portal(**(dict(business_slug=self.business.slug, code=code, address="synthetic-address") | changes))

    def test_pending_code_no_access_then_72h_and_exact_pdf_repeated(self):
        grant, code, replayed = self.create()
        self.assertFalse(replayed); self.assertEqual(len(code), 20)
        self.assertIsNone(grant.expires_at)
        self.assertNotIn(code, grant.evidence_encrypted)
        self.assertNotEqual(code, grant.code_hash)
        duplicate, secret, repeated = self.create()
        self.assertEqual(duplicate.pk, grant.pk); self.assertIsNone(secret); self.assertTrue(repeated)
        with self.assertRaises(PermissionDenied): self.login(code)
        with self.assertRaises(InvalidTransition): self.activate(grant)
        self.finalize()
        activated, _ = self.activate(grant)
        self.assertEqual(activated.expires_at - activated.activated_at, timedelta(hours=72))
        token, expiry = self.login(code)
        scope = dict(business_slug=self.business.slug, token=token)
        result = portal_documents(**scope)
        self.assertEqual(len(result["documents"]), 1)
        public_id = result["documents"][0]["id"]
        self.assertEqual(portal_pdf(**scope, public_id=public_id), portal_pdf(**scope, public_id=public_id, download=True))
        self.assertTrue(MedicalDocumentGrantEvent.objects.filter(grant=grant, action="document_opened", actor__isnull=True).exists())
        self.assertLessEqual(expiry, activated.expires_at)
        with patch("django.utils.timezone.now", return_value=activated.expires_at):
            with self.assertRaises(PermissionDenied): self.login(code)
        self.assertTrue(self.version.finalization.artifact.attachment.file.storage.exists(self.version.finalization.artifact.attachment.file.name))

    def test_reissue_and_revocation_close_existing_sessions(self):
        self.finalize(); grant, code, _ = self.create(); self.activate(grant)
        token, _ = self.login(code)
        new, new_code, _ = self.create(replaces_id=grant.pk, idempotency_key="reissue")
        with self.assertRaises(PermissionDenied): self.login(code)
        with self.assertRaises(PermissionDenied): portal_documents(business_slug=self.business.slug, token=token)
        self.activate(new, idempotency_key="activate-new")
        token, _ = self.login(new_code)
        new.refresh_from_db()
        self.activate(new, action="revoke", reason="Compromised", idempotency_key="revoke")
        with self.assertRaises(PermissionDenied): portal_documents(business_slug=self.business.slug, token=token)

    def test_role_branch_tenant_and_disabled_real_use(self):
        other = Business.objects.create(owner=self.owner, name="Independent issuance clinic")
        for changes in ({"actor": self.owner}, {"business_id": other.pk}, {"branch_id": self.second.pk}):
            with self.assertRaises(PermissionDenied): self.create(**changes)
        with override_settings(ENVIRONMENT="production"):
            with self.assertRaises(PermissionDenied): self.create()
        RolePermission.objects.filter(business_role=self.role, resource="medical_documents", action="issue").update(is_allowed=False)
        with self.assertRaises(PermissionDenied): self.create()

    def test_activation_audit_failure_rolls_back_and_future_correction_stays_private(self):
        self.finalize(); grant, code, _ = self.create()
        with patch("apps.medical.issuance_services.grant_event", side_effect=MedicalAuditUnavailable):
            with self.assertRaises(MedicalAuditUnavailable): self.activate(grant)
        grant.refresh_from_db(); self.assertEqual(grant.state, "pending"); self.assertIsNone(grant.expires_at)
        self.assertIsNone(grant.items.get().finalization_id)
        self.activate(grant)
        token, _ = self.login(code)
        from .document_corrections import correct_final_document
        new, _ = correct_final_document(actor=self.doctor, business_id=self.business.pk, patient_id=self.patient.pk,
            version_id=self.version.pk, appointment_id=self.appointment.pk, expected_state_revision=4,
            document_text="Private correction", reason="Synthetic correction", idempotency_key="correct")
        result = portal_documents(business_slug=self.business.slug, token=token)
        self.assertTrue(result["documents"][0]["has_correction"])
        self.assertEqual(list(grant.items.values_list("version_id", flat=True)), [self.version.pk])
        self.assertNotIn("Private correction", str(result))

    def test_failed_attempts_survive_denial_and_phone_does_not_transfer_access(self):
        for index in range(30):
            with self.assertRaises(PermissionDenied): self.login("WRONG")
        with self.assertRaises(Throttled): self.login("WRONG")
        from .models import MedicalDocumentPortalAttempt
        self.assertEqual(MedicalDocumentPortalAttempt.objects.get().count, 31)
        self.finalize(); grant, code, _ = self.create(); self.activate(grant)
        self.patient.client.phone = "+77001112233"
        self.patient.client.save(update_fields=["phone"])
        with self.assertRaises(PermissionDenied): self.login("77001112233", address="fresh-device")
        self.login(code, address="fresh-device")

    @override_settings(DEBUG=True)
    def test_http_csrf_cookie_private_metadata_exact_file_and_logout(self):
        from rest_framework.test import APIClient
        from uuid import uuid4
        staff = APIClient(); staff.force_authenticate(self.doctor)
        scope = dict(business_id=self.business.pk, patient_id=self.patient.pk, branch_id=self.first.pk)
        root = "/api/medical/document-grants/"
        data = staff.get(root, scope | {"encounter_id": self.encounter_record.pk})
        self.assertEqual(data.status_code, 200, data.data)
        self.assertNotIn("document_text", str(data.data))
        self.assertIn("no-store", data["Cache-Control"])
        payload = scope | dict(encounter_id=self.encounter_record.pk, version_ids=[self.version.pk],
            personally_verified=True, verification_reason="Checked in person")
        invalid = staff.post(root, payload | {"unexpected": True}, format="json", HTTP_IDEMPOTENCY_KEY="http-bad")
        self.assertEqual(invalid.status_code, 400)
        created = staff.post(root, payload, format="json", HTTP_IDEMPOTENCY_KEY="http-create")
        self.assertEqual(created.status_code, 201, created.data)
        code, grant_id = created.data["code"], created.data["grant"]["id"]
        repeated = staff.post(root, payload, format="json", HTTP_IDEMPOTENCY_KEY="http-create")
        self.assertIsNone(repeated.data["code"])
        self.finalize()
        activated = staff.post(f"{root}{grant_id}/transition/", scope | dict(expected_revision=1, action="activate"),
            format="json", HTTP_IDEMPOTENCY_KEY="http-activate")
        self.assertEqual(activated.status_code, 200, activated.data)
        portal = f"/api/medical/portal/{self.business.slug}/"
        client = APIClient(enforce_csrf_checks=True)
        self.assertEqual(client.post(portal, {"code": code}, format="json").status_code, 403)
        csrf = client.get("/api/auth/csrf/").json()["csrf_token"]
        logged = client.post(portal, {"code": code}, format="json", HTTP_X_CSRFTOKEN=csrf)
        self.assertEqual(logged.status_code, 200, getattr(logged, "data", None))
        cookie = logged.cookies["medical_document_session"]
        self.assertTrue(cookie["httponly"]); self.assertEqual(cookie["samesite"], "Strict")
        result = client.get(portal)
        self.assertEqual(result.status_code, 200, result.data)
        item = result.data["documents"][0]["id"]
        url = f"{portal}files/{item}/"
        pdf = client.get(url)
        self.assertEqual(pdf.status_code, 200); self.assertEqual(pdf["Content-Type"], "application/pdf")
        self.assertIn("no-store", pdf["Cache-Control"])
        self.assertIn("attachment", client.get(url + "?download=1")["Content-Disposition"])
        self.assertEqual(APIClient().get(url).status_code, 403)
        self.assertEqual(client.get(f"{portal}files/{uuid4()}/").status_code, 403)
        self.assertEqual(client.post(url, {"code": code}, format="json", HTTP_X_CSRFTOKEN=csrf).status_code, 404)
        self.assertEqual(client.delete(portal).status_code, 403)
        self.assertEqual(client.delete(portal, HTTP_X_CSRFTOKEN=csrf).status_code, 204)
        self.assertEqual(client.get(url).status_code, 403)

    def test_representative_revocation_expiry_and_other_recipient_isolation(self):
        import json
        from apps.clients.models import Client
        from .models import PatientRepresentative
        from .identity_crypto import encrypt_medical_value
        self.finalize()
        relative = Client.objects.create(business=self.business, full_name="Synthetic representative")
        start = timezone.now() - timedelta(minutes=1)
        relation = PatientRepresentative.objects.create(patient=self.patient, representative_client=relative,
            verified_by=self.owner, verified_at=start, valid_from=start, valid_until=start + timedelta(hours=1),
            authority_encrypted="staging")
        authority = {"patient_id": self.patient.pk, "representative_client_id": relative.pk,
            "valid_from": relation.valid_from.isoformat(), "valid_until": relation.valid_until.isoformat(),
            "permissions": ["receive_documents"]}
        relation.authority_encrypted = encrypt_medical_value(json.dumps(authority), business_id=self.business.pk,
            subject_id=relation.pk, purpose="representative_authority")
        relation.save()
        grant, code, _ = self.create(representative_id=relation.pk)
        self.activate(grant)
        token, _ = self.login(code)
        scope = dict(business_slug=self.business.slug, token=token)
        self.assertEqual(len(portal_documents(**scope)["documents"]), 1)
        with patch("django.utils.timezone.now", return_value=relation.valid_until):
            with self.assertRaises(PermissionDenied): self.login(code)
        relation.revoked_at, relation.revoked_by, relation.revocation_encrypted = timezone.now(), self.owner, "synthetic revocation"
        relation.save(update_fields=["revoked_at", "revoked_by", "revocation_encrypted"])
        with self.assertRaises(PermissionDenied): portal_documents(**scope)
        own, own_code, _ = self.create(idempotency_key="patient-own")
        self.activate(own, idempotency_key="patient-activate")
        own_token, _ = self.login(own_code)
        with self.assertRaises(PermissionDenied): portal_pdf(business_slug=self.business.slug, token=own_token, public_id=grant.items.get().public_id)

    def test_integrity_changed_identity_quarantine_and_creation_rollback(self):
        from .identity_crypto import MedicalDataUnavailable
        from .models import MedicalDocumentGrantItem
        with patch("apps.medical.issuance_services.grant_event", side_effect=MedicalAuditUnavailable):
            with self.assertRaises(MedicalAuditUnavailable): self.create()
        self.assertFalse(MedicalDocumentGrant.objects.exists()); self.assertFalse(MedicalDocumentGrantItem.objects.exists())
        self.finalize(); grant, code, _ = self.create(); self.activate(grant)
        self.patient.revision += 1; self.patient.save(update_fields=["revision"])
        with self.assertRaises(MedicalDataUnavailable): self.login(code)
        self.patient.revision -= 1; self.patient.save(update_fields=["revision"])
        token, _ = self.login(code)
        from apps.core.models import FileAttachment
        FileAttachment.objects.filter(pk=self.version.finalization.artifact.attachment_id).update(scan_status="pending")
        from apps.core.file_scanning import FileQuarantined
        with self.assertRaises(FileQuarantined):
            portal_pdf(business_slug=self.business.slug, token=token, public_id=grant.items.get().public_id)
        MedicalDocumentGrant.objects.filter(pk=grant.pk).update(evidence_encrypted="corrupt")
        with self.assertRaises(MedicalDataUnavailable): self.login(code)

    def test_reception_metadata_without_clinical_view_and_paged_history(self):
        from rest_framework.test import APIClient
        from .models import MedicalRoleAssignment
        assignment = MedicalRoleAssignment.objects.get(member__user=self.doctor, member__business=self.business)
        assignment.kind = "reception"; assignment.save(update_fields=["kind"])
        RolePermission.objects.filter(business_role=self.role).exclude(resource="medical_documents", action="issue").update(is_allowed=False)
        staff = APIClient(); staff.force_authenticate(self.doctor)
        scope = dict(business_id=self.business.pk, branch_id=self.first.pk, client_id=self.patient.client_id)
        response = staff.get("/api/medical/document-grants/by-client/", scope)
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data["patient_id"], self.patient.pk)
        for secret in ("iin", "document_text", "demographics"):
            self.assertNotIn(secret, response.data)
        from .issuance_reads import issuance_workspace
        for index in range(22): self.create(idempotency_key=f"history-{index}")
        first = issuance_workspace(actor=self.doctor, business_id=self.business.pk, branch_id=self.first.pk, patient_id=self.patient.pk)
        second = issuance_workspace(actor=self.doctor, business_id=self.business.pk, branch_id=self.first.pk,
            patient_id=self.patient.pk, before_grant_id=first["next_before_grant_id"])
        self.assertEqual(len(first["grants"]), 20); self.assertEqual(len(second["grants"]), 2)
        self.assertFalse({row["id"] for row in first["grants"]} & {row["id"] for row in second["grants"]})
        RolePermission.objects.filter(business_role=self.role, action="issue").update(is_allowed=False)
        self.assertEqual(staff.get("/api/medical/document-grants/by-client/", scope).status_code, 403)

    def test_pack_waits_for_every_exact_version_and_reissue_rollback_preserves_old(self):
        self.finalize()
        pending = self.save(idempotency_key="pending-pack-document")
        grant, code, _ = self.create(version_ids=[self.version.pk, pending.pk])
        with self.assertRaises(InvalidTransition): self.activate(grant)
        grant.refresh_from_db(); self.assertEqual(grant.state, "pending")
        self.assertFalse(grant.items.exclude(finalization=None).exists())
        with self.assertRaises(PermissionDenied): self.login(code)
        old, old_code, _ = self.create(idempotency_key="old-ready")
        self.activate(old, idempotency_key="activate-old")
        with patch("apps.medical.issuance_services.grant_event", side_effect=MedicalAuditUnavailable):
            with self.assertRaises(MedicalAuditUnavailable): self.create(replaces_id=old.pk, idempotency_key="broken-reissue")
        old.refresh_from_db(); self.assertEqual(old.state, "active"); self.login(old_code)
