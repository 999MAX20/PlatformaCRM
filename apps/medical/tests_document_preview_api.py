from unittest.mock import patch

from django.test import TestCase, override_settings

from apps.businesses.models import Business, RolePermission
from apps.clients.models import Client
from . import tests_document_api as fixtures
from . import tests_patient_services as crypto_fixtures
from .audit import MedicalAuditUnavailable
from .common_template_services import save_common_template_draft
from .models import MedicalAuditEvent, MedicalDocumentRevision


@override_settings(MEDICAL_DATA_KEYS={"test": crypto_fixtures.key(7)}, MEDICAL_DATA_ACTIVE_KEY_ID="test",
                   MEDICAL_IDENTITY_INDEX_KEY=crypto_fixtures.key(8))
class DocumentPreviewAPITests(TestCase):
    @classmethod
    def setUpTestData(cls):
        fixtures.DocumentAPITests.setUpTestData.__func__(cls)

    def setUp(self):
        fixtures.DocumentAPITests.setUp(self)

    private = fixtures.DocumentAPITests.private
    command = fixtures.DocumentAPITests.command
    read = fixtures.DocumentAPITests.read

    def preview(self, **overrides):
        return self.read("preview/", **(dict(encounter_id=self.encounter_record.pk,
            template_version_id=self.template.pk) | overrides))

    def test_preview_and_edited_save_replay_and_version(self):
        response = self.preview()
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data["document_text"], "Original {{patient}} text")
        self.assertEqual(response.data["unknown_fields"], ["patient"])
        self.assertIn("patient.full_name", response.data["available_fields"])
        self.assertTrue(MedicalAuditEvent.objects.filter(action="read", encounter_version=self.first_version).exists())
        self.assertFalse(MedicalDocumentRevision.objects.exists())
        payload = self.payload | {"expected_source_digest": response.data["source_digest"]}
        created = self.command(payload=payload)
        self.assertEqual(created.status_code, 201, created.data)
        Client.objects.filter(pk=self.patient.client_id).update(full_name="Changed after successful save")
        replay = self.command(payload=payload)
        self.assertEqual(replay.status_code, 200, replay.data)
        self.assertTrue(replay.data["replayed"])
        self.assertEqual(replay.data["version_id"], created.data["version_id"])
        saved = self.read(f"versions/{created.data['version_id']}/")
        self.assertEqual(saved.data["snapshot"]["document_text"], payload["document_text"])
        self.assertNotEqual(saved.data["snapshot"]["patient_identity"]["full_name"], "Changed after successful save")

    def test_changed_source_conflict_then_fresh_preview_can_save(self):
        token = self.preview().data["source_digest"]
        Client.objects.filter(pk=self.patient.client_id).update(full_name="Updated synthetic patient")
        stale = self.command(payload=self.payload | {"expected_source_digest": token})
        self.assertEqual(stale.status_code, 409, stale.data)
        self.assertFalse(MedicalDocumentRevision.objects.exists())
        fresh = self.preview().data["source_digest"]
        self.assertNotEqual(fresh, token)
        self.assertEqual(self.command(payload=self.payload | {"expected_source_digest": fresh}).status_code, 201)

    def test_edit_preview_requires_current_update_permission(self):
        created = self.command().data
        response = self.preview(document_id=created["id"])
        self.assertEqual(response.status_code, 200, response.data)
        RolePermission.objects.filter(business_role=self.assignment.business_role,
            resource="medical_documents", action="update").update(is_allowed=False)
        self.assertEqual(self.preview().status_code, 200)
        self.assertEqual(self.preview(document_id=created["id"]).status_code, 403)

    def test_strict_fields_and_digest_format(self):
        for query in ({"template_version_id": 0}, {"document_id": 0}, {"source": "forged"},
                      {"participation_id": 1}, {"patient_identity": "forged"}):
            self.assertEqual(self.preview(**query).status_code, 400)
        self.assertEqual(self.read("preview/", encounter_id=self.encounter_record.pk).status_code, 400)
        for digest in (None, True, "", "a" * 63, "a" * 64 + "\n", " a" * 32):
            response = self.command(payload=self.payload | {"expected_source_digest": digest})
            self.assertEqual(response.status_code, 400, response.data)
        self.assertFalse(MedicalDocumentRevision.objects.exists())

    def test_owner_tenant_patient_and_revoked_branch_denied(self):
        other = Business.objects.create(owner=self.owner, name="Other", slug="preview-other")
        self.assertEqual(self.preview(business_id=other.pk).status_code, 403)
        self.assertIn(self.preview(patient_id=self.patient.pk + 999).status_code, (403, 404))
        self.assertEqual(self.preview(document_id=999).status_code, 403)
        self.api.force_authenticate(self.owner)
        self.assertEqual(self.preview().status_code, 403)
        self.api.force_authenticate(self.doctor)
        self.assignment.branches.clear()
        self.assertEqual(self.preview().status_code, 403)
        self.api.force_authenticate(None)
        self.assertIn(self.preview().status_code, (401, 403))

    def test_unapproved_template_denied_without_document(self):
        version, _ = save_common_template_draft(actor=self.head, business_id=self.business.pk,
            title="Unapproved", text="Not approved", idempotency_key="unapproved-preview")
        self.assertEqual(self.preview(template_version_id=version.pk).status_code, 403)
        self.assertFalse(MedicalDocumentRevision.objects.exists())

    def test_audit_failure_returns_private_503_and_rolls_back(self):
        before = MedicalAuditEvent.objects.count()
        with patch("apps.medical.document_previews.write_patient_audit", side_effect=MedicalAuditUnavailable):
            response = self.preview()
        self.assertEqual(response.status_code, 503, response.data)
        self.assertNotIn("Original", str(response.data))
        self.assertEqual(MedicalAuditEvent.objects.count(), before)
        self.assertFalse(MedicalDocumentRevision.objects.exists())
