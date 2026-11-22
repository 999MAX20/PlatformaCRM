from unittest.mock import patch

from django.db import DatabaseError
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from apps.businesses.models import Business, BusinessMember
from . import tests_template_services as fixtures
from . import tests_patient_services as crypto_fixtures
from .document_templates import append_template_revision
from .models import MedicalDocumentTemplate, MedicalDocumentTemplateRevision


@override_settings(MEDICAL_DATA_KEYS={"test": crypto_fixtures.key(7)}, MEDICAL_DATA_ACTIVE_KEY_ID="test",
                   MEDICAL_IDENTITY_INDEX_KEY=crypto_fixtures.key(8))
class PersonalTemplateAPITests(TestCase):
    @classmethod
    def setUpTestData(cls):
        fixtures.PersonalTemplateServiceTests.setUpTestData.__func__(cls)

    def setUp(self):
        self.api = APIClient()
        self.api.force_authenticate(self.doctor)
        self.url = "/api/medical/document-templates/"
        self.scope = {"business_id": self.business.pk}
        self.payload = {**self.scope, "title": "Личный шаблон", "text": "  Оқу үлгісі\n", "reason": "Synthetic reason"}

    def create(self, **overrides):
        return self.api.post(self.url, self.payload | overrides, format="json", HTTP_IDEMPOTENCY_KEY="template-create")

    def read(self, version_id):
        return self.api.get(f"{self.url}versions/{version_id}/", self.scope)

    def private(self, response):
        self.assertEqual(response["Cache-Control"], "no-store, private")
        self.assertEqual(response["Pragma"], "no-cache")

    def test_create_update_list_history_and_exact_version_over_http(self):
        created = self.create()
        self.assertEqual(created.status_code, 201, created.data)
        self.private(created)
        saved = self.api.post(f"{self.url}{created.data['id']}/draft/",
            self.payload | {"text": "New text", "expected_revision": 1}, format="json", HTTP_IDEMPOTENCY_KEY="template-update")
        self.assertEqual(saved.status_code, 200, saved.data)
        self.private(saved)
        old = self.read(created.data["version_id"])
        self.assertEqual(old.status_code, 200, old.data)
        self.assertEqual(old.data["template"]["text"], self.payload["text"])
        self.private(old)
        current = self.read(saved.data["version_id"])
        self.assertEqual(current.data["template"]["text"], "New text")
        listing = self.api.get(self.url, self.scope)
        self.assertEqual(listing.status_code, 200, listing.data)
        self.assertEqual(listing.data["results"][0]["version_id"], saved.data["version_id"])
        self.private(listing)
        history = self.api.get(f"{self.url}{created.data['id']}/revisions/", self.scope | {"limit": 1})
        self.assertEqual(history.status_code, 200, history.data)
        self.assertEqual(history.data["results"][0]["revision"], 2)
        self.private(history)
        last = self.api.get(f"{self.url}{created.data['id']}/revisions/",
            self.scope | {"before_revision": history.data["next_before_revision"], "limit": 1})
        self.assertEqual(last.data["results"][0]["revision"], 1)
        self.assertIsNone(last.data["next_before_revision"])

    def test_retry_conflict_and_stale_revision_do_not_echo_template_text(self):
        created = self.create()
        replay = self.create()
        self.assertEqual(replay.status_code, 200, replay.data)
        self.assertTrue(replay.data["replayed"])
        conflict = self.create(text="Private changed text")
        self.assertEqual(conflict.status_code, 409, conflict.data)
        self.assertNotIn("Private changed text", str(conflict.data))
        self.private(conflict)
        stale = self.api.post(f"{self.url}{created.data['id']}/draft/",
            self.payload | {"expected_revision": 999}, format="json", HTTP_IDEMPOTENCY_KEY="stale")
        self.assertEqual(stale.status_code, 409, stale.data)
        self.assertEqual(MedicalDocumentTemplateRevision.objects.count(), 1)

    def test_unknown_owner_code_approval_and_missing_key_are_rejected(self):
        for changes in ({"owner_member_id": self.member.pk}, {"code": "selected"}, {"approved": True},
                        {"expected_revision": 1}, {"title": " \t"}):
            response = self.create(**changes)
            self.assertEqual(response.status_code, 400, response.data)
            self.private(response)
        response = self.api.post(self.url, self.payload, format="json")
        self.assertEqual(response.status_code, 400, response.data)
        self.assertFalse(MedicalDocumentTemplateRevision.objects.exists())

    def test_anonymous_owner_and_revoked_actor_are_denied(self):
        created = self.create()
        self.api.force_authenticate(None)
        self.assertIn(self.read(created.data["version_id"]).status_code, (401, 403))
        self.api.force_authenticate(self.owner)
        denied = self.read(created.data["version_id"])
        self.assertEqual(denied.status_code, 403, denied.data)
        self.private(denied)
        self.api.force_authenticate(self.doctor)
        self.assignment.revoked_at = timezone.now()
        self.assignment.save(update_fields=["revoked_at"])
        self.assertEqual(self.create().status_code, 403)
        self.assertEqual(self.api.get(self.url, self.scope).status_code, 403)

    def test_foreign_version_is_hidden_with_valid_local_role(self):
        business = Business.objects.create(owner=self.owner, name="Other", slug="template-api-other")
        member = BusinessMember.objects.create(business=business, user=self.doctor)
        template = MedicalDocumentTemplate.objects.create(business=business, owner_member=member, code="other")
        version = append_template_revision(template=template, author=self.doctor,
            title="Other private title", text="Other private text")
        denied = self.read(version.pk)
        self.assertEqual(denied.status_code, 403, denied.data)
        self.assertNotIn("Other private", str(denied.data))
        self.private(denied)
        history = self.api.get(f"{self.url}{template.pk}/revisions/", self.scope)
        self.assertEqual(history.status_code, 403, history.data)
        self.assertEqual(self.api.get(self.url, self.scope).data["results"], [])

    def test_audit_failure_returns_503_without_saving_and_can_retry(self):
        with patch("apps.medical.template_audit.MedicalAuditEvent.objects.create", side_effect=DatabaseError()):
            failed = self.create()
        self.assertEqual(failed.status_code, 503, failed.data)
        self.private(failed)
        self.assertFalse(MedicalDocumentTemplateRevision.objects.exists())
        self.assertEqual(self.create().status_code, 201)

    def test_unsupported_mutations_and_bad_pagination_do_not_change_template(self):
        created = self.create()
        for method in (self.api.patch, self.api.delete):
            response = method(f"{self.url}{created.data['id']}/draft/", self.scope, format="json")
            self.assertEqual(response.status_code, 405, response.data)
        self.assertEqual(self.api.get(self.url, self.scope | {"limit": 51}).status_code, 400)
        self.assertEqual(MedicalDocumentTemplateRevision.objects.count(), 1)
