from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from apps.businesses.models import Business, RolePermission
from . import tests_document_rules as fixtures
from .models import MedicalDocumentRuleRevision
from .tests_document_rules import default_rule
from .tests_patient_services import key


@override_settings(MEDICAL_DATA_KEYS={"test": key(7)}, MEDICAL_DATA_ACTIVE_KEY_ID="test",
                   MEDICAL_IDENTITY_INDEX_KEY=key(8))
class DocumentRuleAPITests(TestCase):
    @classmethod
    def setUpTestData(cls):
        fixtures.DocumentRuleTests.setUpTestData.__func__(cls)

    def setUp(self):
        self.api = APIClient()
        self.api.force_authenticate(self.head)
        self.url = "/api/medical/document-kinds/"
        self.scope = {"business_id": self.business.pk}
        self.payload = self.scope | {"content": {"name": "Synthetic rule kind", "default": default_rule(), "services": []},
            "template_ids": [self.template.pk], "reason": "Synthetic setup"}

    def post(self, path="", payload=None, key="rules"):
        return self.api.post(self.url + path, payload or self.payload, format="json", HTTP_IDEMPOTENCY_KEY=key)

    def private(self, response):
        self.assertEqual(response["Cache-Control"], "no-store, private")
        self.assertEqual(response["Pragma"], "no-cache")

    def test_head_creates_reads_searches_and_versions_rules(self):
        access = self.api.get(self.url + "workspace-access/", self.scope)
        self.assertEqual(access.status_code, 200, access.data)
        self.assertTrue(access.data["actions"]["save"])
        self.assertEqual(access.data["validation"], "synthetic")
        self.private(access)
        created = self.post()
        self.assertEqual(created.status_code, 201, created.data)
        self.private(created)
        self.assertEqual(self.post().status_code, 200)
        identifier = created.data["kind_id"]
        path = f"versions/{created.data['version_id']}/"
        snapshot = self.api.get(self.url + path, self.scope)
        self.assertEqual(snapshot.status_code, 200, snapshot.data)
        self.assertFalse(snapshot.data["content"]["docx_allowed"])
        updated = self.post(f"{identifier}/save/", self.payload | {"expected_revision": 1,
            "content": self.payload["content"] | {"name": "Changed synthetic kind", "docx_allowed": True}}, key="rules-update")
        self.assertEqual(updated.status_code, 200, updated.data)
        self.assertEqual(updated.data["revision"], 2)
        self.assertEqual(self.api.get(self.url + path, self.scope).data, snapshot.data)
        page = self.api.get(self.url, self.scope | {"q": "changed"})
        self.assertEqual([row["revision"] for row in page.data["results"]], [2])
        history = self.api.get(self.url + f"{identifier}/history/", self.scope | {"limit": 1})
        self.assertEqual(history.data["results"][0]["revision"], 2)
        previous = self.api.get(self.url + f"{identifier}/history/", self.scope | {"before_id": history.data["next_before_id"]})
        self.assertEqual(previous.data["results"][0]["revision"], 1)
        self.private(previous)

    def test_denials_scope_revoke_and_read_only_head(self):
        created = self.post().data
        for actor in (None, self.owner, self.doctor):
            self.api.force_authenticate(actor)
            for response in (self.api.get(self.url, self.scope), self.post(), self.api.get(
                    self.url + f"versions/{created['version_id']}/", self.scope)):
                self.assertIn(response.status_code, (401, 403), response.data)
                self.private(response)
        self.api.force_authenticate(self.head)
        other = Business.objects.create(owner=self.owner, name="Foreign rules", slug="foreign-rule-api")
        denied = self.api.get(self.url + f"versions/{created['version_id']}/", {"business_id": other.pk})
        self.assertEqual(denied.status_code, 403)
        RolePermission.objects.filter(business_role=self.head_role, action="approve").update(is_allowed=False)
        self.assertEqual(self.post().status_code, 403)
        self.assertFalse(self.api.get(self.url + "workspace-access/", self.scope).data["actions"]["save"])
        self.assertEqual(self.api.get(self.url, self.scope).status_code, 200)
        self.head_assignment.revoked_at = timezone.now()
        self.head_assignment.save(update_fields=["revoked_at"])
        self.assertEqual(self.api.get(self.url, self.scope).status_code, 403)
        self.assertEqual(MedicalDocumentRuleRevision.objects.count(), 1)

    def test_unsupported_fields_bad_rules_and_stale_revision(self):
        self.assertEqual(self.post(payload=self.payload | {"patient_id": 1}).status_code, 400)
        self.assertEqual(self.post(payload=self.payload | {"content": self.payload["content"] | {"validation": "approved"}}).status_code, 400)
        self.assertEqual(self.post(payload=self.payload | {"content": self.payload["content"] | {"default": default_rule(reviewers=[])}}).status_code, 400)
        self.assertEqual(self.post(key="").status_code, 400)
        created = self.post().data
        stale = self.post(f"{created['kind_id']}/save/", self.payload | {"expected_revision": 2}, key="stale")
        self.assertEqual(stale.status_code, 409, stale.data)
        self.private(stale)
        self.assertEqual(self.api.get(self.url, self.scope | {"patient_id": 1}).status_code, 400)
        self.assertEqual(MedicalDocumentRuleRevision.objects.count(), 1)
