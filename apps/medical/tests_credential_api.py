from unittest.mock import patch

from django.db import DatabaseError
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from apps.businesses.models import Business, BusinessMember, RolePermission
from . import tests_patient_services as crypto_fixtures
from . import tests_template_reviews as fixtures
from .models import MedicalCredentialProfile


@override_settings(MEDICAL_DATA_KEYS={"test": crypto_fixtures.key(7)}, MEDICAL_DATA_ACTIVE_KEY_ID="test",
                   MEDICAL_IDENTITY_INDEX_KEY=crypto_fixtures.key(8))
class CredentialAPITests(TestCase):
    @classmethod
    def setUpTestData(cls):
        fixtures.TemplateReviewTests.setUpTestData.__func__(cls)

    def setUp(self):
        self.api = APIClient()
        self.api.force_authenticate(self.head)
        self.root = "/api/medical/credentials/"
        self.scope = {"business_id": self.business.pk, "member_id": self.member.pk}
        self.payload = self.scope | {"content": {"specialty": "Synthetic specialty", "position": "Synthetic position",
            "qualification": ""}, "reason": "", "expected_revision": 0}

    def save(self, **overrides):
        return self.api.post(self.root, self.payload | overrides, format="json", HTTP_IDEMPOTENCY_KEY="confirm-api")

    def test_roundtrip_current_history_exact_version_and_replay(self):
        access = self.api.get(self.root + "workspace-access/", {"business_id": self.business.pk})
        self.assertEqual(access.status_code, 200)
        self.assertTrue(access.data["actions"]["confirm"])
        saved = self.save()
        self.assertEqual(saved.status_code, 201, saved.data)
        replay = self.save()
        self.assertEqual(replay.status_code, 200)
        self.assertTrue(replay.data["replayed"])
        self.assertEqual(self.save(reason="changed").status_code, 409)
        self.api.force_authenticate(self.doctor)
        access = self.api.get(self.root + "workspace-access/", {"business_id": self.business.pk})
        self.assertFalse(access.data["actions"]["confirm"])
        current = self.api.get(self.root, self.scope)
        self.assertEqual(current.data["version"]["content"], self.payload["content"])
        self.assertEqual(current["Cache-Control"], "no-store, private")
        history = self.api.get(self.root + "revisions/", self.scope)
        self.assertEqual(history.data["results"][0]["id"], saved.data["version_id"])
        exact = self.api.get(self.root, self.scope | {"version_id": saved.data["version_id"]})
        self.assertEqual(exact.data, current.data)

    def test_member_options_head_scope_pagination_and_tenant(self):
        other = Business.objects.create(owner=self.owner, name="Other", slug="credential-api-other")
        foreign_member = BusinessMember.objects.create(business=other, user=self.owner)
        first = self.api.get(self.root + "members/", {"business_id": self.business.pk, "limit": 1})
        self.assertEqual(first.status_code, 200, first.data)
        self.assertIsNotNone(first.data["next_before_id"])
        second = self.api.get(self.root + "members/", {"business_id": self.business.pk,
            "limit": 1, "before_id": first.data["next_before_id"]})
        ids = [first.data["results"][0]["id"], second.data["results"][0]["id"]]
        self.assertEqual(len(set(ids)), 2)
        self.assertNotIn(foreign_member.pk, ids)
        self.assertEqual(self.api.get(self.root, self.scope | {"member_id": foreign_member.pk}).status_code, 404)
        self.api.force_authenticate(self.doctor)
        self.assertEqual(self.api.get(self.root + "members/", {"business_id": self.business.pk}).status_code, 403)

    def test_denial_owner_doctor_write_and_foreign_profile(self):
        for actor in (self.owner, self.doctor):
            self.api.force_authenticate(actor)
            response = self.save()
            self.assertEqual(response.status_code, 403)
            self.assertEqual(response["Cache-Control"], "no-store, private")
        self.assertEqual(self.api.get(self.root, {"business_id": self.business.pk}).status_code, 403)
        self.assertEqual(self.api.get(self.root, self.scope | {"member_id": self.head_member.pk}).status_code, 403)
        self.api.force_authenticate(None)
        self.assertIn(self.api.get(self.root, self.scope).status_code, (401, 403))

    def test_strict_validation_and_revoke_after_success(self):
        for change in ({"content": {}}, {"expected_revision": -1}, {"confirmed_by": self.head.pk}):
            self.assertEqual(self.save(**change).status_code, 400)
        self.assertEqual(self.save().status_code, 201)
        RolePermission.objects.filter(business_role=self.head_role, resource="medical_documents", action="approve").update(is_allowed=False)
        self.assertEqual(self.save().status_code, 403)
        for path, params in (("", {"unknown": 1}), ("members/", {"limit": 51}), ("revisions/", {"before_revision": 0})):
            scope = {"business_id": self.business.pk} if path == "members/" else self.scope
            self.assertEqual(self.api.get(self.root + path, scope | params).status_code, 400)

    def test_audit_failure_is_recoverable_without_partial_profile(self):
        with patch("apps.medical.credential_services.MedicalAuditEvent.objects.create", side_effect=DatabaseError):
            response = self.save()
        self.assertEqual(response.status_code, 503, response.data)
        self.assertFalse(MedicalCredentialProfile.objects.exists())
        self.assertEqual(self.save().status_code, 201)
