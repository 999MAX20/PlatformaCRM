import json
from unittest.mock import patch

from django.db import connection
from django.test import TestCase, override_settings
from django.test.utils import CaptureQueriesContext
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.test import APIClient

from apps.businesses.models import Business, RolePermission
from apps.core.idempotency import CRMCommandConflict
from apps.services.models import Service
from . import tests_patient_services as crypto_fixtures
from . import tests_template_reviews as fixtures
from .audit import MedicalAuditUnavailable
from .document_templates import read_template_revision
from .identity_crypto import MedicalDataUnavailable, decrypt_medical_value, encrypt_medical_value
from .models import MedicalAuditEvent, MedicalDocumentTemplateRevision
from .template_services import save_personal_template_draft, read_personal_template_version
from .template_reviews import submit_personal_template, decide_template_review, read_submitted_template


@override_settings(MEDICAL_DATA_KEYS={"test": crypto_fixtures.key(7)}, MEDICAL_DATA_ACTIVE_KEY_ID="test",
                   MEDICAL_IDENTITY_INDEX_KEY=crypto_fixtures.key(8))
class TemplateMetadataTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        fixtures.TemplateReviewTests.setUpTestData.__func__(cls)
        cls.service = Service.objects.create(business=cls.business, name="Synthetic private procedure")

    def setUp(self):
        self.metadata = {"language": "kk", "category": "Учебная категория", "specialty": "Оқу мамандығы",
                         "service_ids": [self.service.pk]}

    def save(self, **overrides):
        return save_personal_template_draft(**(dict(actor=self.doctor, business_id=self.business.pk,
            title="Synthetic", text="Literal", idempotency_key="metadata", metadata=self.metadata) | overrides))

    def test_metadata_encrypted_and_service_name_captured_from_catalog(self):
        with CaptureQueriesContext(connection) as queries:
            version, _ = self.save()
        snapshot = read_template_revision(version)
        self.assertEqual(snapshot["metadata"], {"language": "kk", "category": "Учебная категория",
            "specialty": "Оқу мамандығы", "services": [{"id": self.service.pk, "name": self.service.name}]})
        writes = "\n".join(row["sql"] for row in queries if not row["sql"].startswith("SELECT"))
        for private in (self.service.name, "Учебная категория", "Оқу мамандығы"):
            self.assertNotIn(private, writes)
            self.assertNotIn(private, version.snapshot_encrypted)

    def test_omitted_update_retains_metadata_after_service_removed(self):
        first, _ = self.save()
        before = read_template_revision(first)
        self.service.delete()
        second, _ = self.save(template_id=first.template_id, expected_revision=1, text="New", metadata=None,
                              idempotency_key="second")
        self.assertEqual(read_template_revision(second)["metadata"], before["metadata"])
        self.assertEqual(read_template_revision(first), before)
        replay, replayed = self.save()
        self.assertTrue(replayed)
        self.assertEqual(replay.pk, first.pk)

    def test_explicit_edit_captures_new_service_name_without_changing_approved_version(self):
        first, _ = self.save()
        submit_personal_template(actor=self.doctor, business_id=self.business.pk, version_id=first.pk, idempotency_key="submit")
        decide_template_review(actor=self.head, business_id=self.business.pk, version_id=first.pk,
            decision="approved", reason="Synthetic approval", idempotency_key="approve")
        before = read_submitted_template(actor=self.head, business_id=self.business.pk, version_id=first.pk)
        Service.objects.filter(pk=self.service.pk).update(name="Changed procedure")
        second, _ = self.save(template_id=first.template_id, expected_revision=1, idempotency_key="second")
        self.assertEqual(read_template_revision(second)["metadata"]["services"][0]["name"], "Changed procedure")
        self.assertEqual(read_template_revision(first)["metadata"], before["metadata"])
        payload = read_personal_template_version(actor=self.doctor, business_id=self.business.pk, version_id=second.pk)
        self.assertIsNone(payload["review"])

    def test_metadata_change_conflicts_with_same_idempotency_key(self):
        self.save()
        with self.assertRaises(CRMCommandConflict):
            self.save(metadata=self.metadata | {"category": "Changed"})
        self.assertEqual(MedicalDocumentTemplateRevision.objects.count(), 1)

    def test_foreign_missing_duplicate_and_wrong_type_service_links_rejected(self):
        other = Business.objects.create(owner=self.owner, name="Other", slug="metadata-other")
        foreign = Service.objects.create(business=other, name="Other procedure")
        for ids in ([foreign.pk], [9999999], [self.service.pk] * 2, [True], ["1"], None, list(range(1, 52))):
            with self.subTest(ids=ids), self.assertRaises(ValidationError):
                self.save(metadata=self.metadata | {"service_ids": ids})
        self.assertFalse(MedicalDocumentTemplateRevision.objects.exists())
        self.assertFalse(MedicalAuditEvent.objects.exists())

    def test_invalid_classification_rejected_and_audit_failure_rolls_back(self):
        for value in ([], {}, self.metadata | {"language": "xx"}, self.metadata | {"category": "x" * 256},
                      self.metadata | {"specialty": None}, self.metadata | {"extra": "private"}):
            with self.subTest(value=value), self.assertRaises(ValidationError):
                self.save(metadata=value)
        with patch("apps.medical.template_services.write_template_audit", side_effect=MedicalAuditUnavailable()):
            with self.assertRaises(MedicalAuditUnavailable):
                self.save()
        self.assertFalse(MedicalDocumentTemplateRevision.objects.exists())

    def test_revoked_write_permission_blocks_metadata_change(self):
        RolePermission.objects.filter(business_role=self.role, resource="medical_documents", action="create").update(is_allowed=False)
        with self.assertRaises(PermissionDenied):
            self.save()
        self.assertFalse(MedicalDocumentTemplateRevision.objects.exists())

    def test_authenticated_corrupt_metadata_fails_closed(self):
        version, _ = self.save()
        original = json.loads(decrypt_medical_value(version.snapshot_encrypted, business_id=self.business.pk,
            subject_id=version.pk, purpose="document_template"))
        for metadata in ({}, {"language": "ru", "category": "", "specialty": "", "services": [{"id": True, "name": "Wrong"}]}):
            payload = original | {"metadata": metadata}
            encrypted = encrypt_medical_value(json.dumps(payload), business_id=self.business.pk,
                subject_id=version.pk, purpose="document_template")
            MedicalDocumentTemplateRevision.objects.filter(pk=version.pk).update(snapshot_encrypted=encrypted)
            with self.assertRaises(MedicalDataUnavailable):
                read_template_revision(version)

    def test_http_roundtrip_strict_metadata_and_clear(self):
        api = APIClient(); api.force_authenticate(self.doctor)
        root = "/api/medical/document-templates/"
        payload = {"business_id": self.business.pk, "title": "Synthetic", "text": "Literal", "metadata": self.metadata}
        response = api.post(root, payload, format="json", HTTP_IDEMPOTENCY_KEY="http")
        self.assertEqual(response.status_code, 201, response.data)
        read = api.get(f"{root}versions/{response.data['version_id']}/", {"business_id": self.business.pk})
        self.assertEqual(read.data["metadata"]["category"], self.metadata["category"])
        self.assertEqual(read["Cache-Control"], "no-store, private")
        for invalid in (None, self.metadata | {"extra": "private"}, self.metadata | {"service_ids": [self.service.pk] * 2}):
            bad = api.post(root, payload | {"metadata": invalid}, format="json", HTTP_IDEMPOTENCY_KEY="invalid")
            self.assertEqual(bad.status_code, 400, bad.data)
        clear = {"language": "", "category": "", "specialty": "", "service_ids": []}
        updated = api.post(f"{root}{response.data['id']}/draft/", payload | {"expected_revision": 1, "metadata": clear},
            format="json", HTTP_IDEMPOTENCY_KEY="clear")
        self.assertEqual(updated.status_code, 200, updated.data)
        read = api.get(f"{root}versions/{updated.data['version_id']}/", {"business_id": self.business.pk})
        self.assertEqual(read.data["metadata"], {"language": "", "category": "", "specialty": "", "services": []})

    def test_common_http_metadata_requires_head_and_retains_scope(self):
        for action in ("create", "update"):
            RolePermission.objects.create(business_role=self.head_role, resource="medical_documents",
                action=action, scope="business", is_allowed=True)
        api = APIClient(); api.force_authenticate(self.doctor)
        root = "/api/medical/document-templates/common/"
        payload = {"business_id": self.business.pk, "title": "Common", "text": "Literal", "metadata": self.metadata}
        denied = api.post(root, payload, format="json", HTTP_IDEMPOTENCY_KEY="common")
        self.assertEqual(denied.status_code, 403)
        api.force_authenticate(self.head)
        saved = api.post(root, payload, format="json", HTTP_IDEMPOTENCY_KEY="common")
        self.assertEqual(saved.status_code, 201, saved.data)
        read = api.get(f"{root}versions/{saved.data['version_id']}/", {"business_id": self.business.pk})
        self.assertEqual(read.status_code, 200, read.data)
        self.assertEqual(read.data["metadata"]["services"][0]["id"], self.service.pk)
        api.force_authenticate(self.doctor)
        self.assertEqual(api.get(f"{root}versions/{saved.data['version_id']}/", {"business_id": self.business.pk}).status_code, 403)
