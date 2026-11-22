from unittest.mock import patch

from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from apps.businesses.models import Business
from . import tests_patient_services as crypto_fixtures
from .audit import MedicalAuditUnavailable
from .models import MedicalDocumentTemplate, MedicalDocumentTemplateRevision, MedicalTemplateReview
from .template_services import save_personal_template_draft
from . import tests_template_reviews as review_fixtures


@override_settings(MEDICAL_DATA_KEYS={"test": crypto_fixtures.key(7)}, MEDICAL_DATA_ACTIVE_KEY_ID="test",
                   MEDICAL_IDENTITY_INDEX_KEY=crypto_fixtures.key(8))
class TemplateReviewAPITests(TestCase):
    @classmethod
    def setUpTestData(cls):
        review_fixtures.TemplateReviewTests.setUpTestData.__func__(cls)

    def setUp(self):
        review_fixtures.TemplateReviewTests.setUp(self)
        self.api = APIClient()
        self.api.force_authenticate(self.doctor)
        self.root = "/api/medical/document-templates/"
        self.version_url = f"{self.root}versions/{self.version.pk}/"
        self.scope = {"business_id": self.business.pk}

    def command(self, action, payload=None, key="command"):
        response = self.api.post(self.version_url + action + "/", self.scope | (payload or {}),
            format="json", HTTP_IDEMPOTENCY_KEY=key)
        self.private(response)
        return response

    def private(self, response):
        self.assertEqual(response["Cache-Control"], "no-store, private")
        self.assertEqual(response["Pragma"], "no-cache")

    def test_author_submission_head_queue_and_exact_decision(self):
        response = self.command("submit")
        self.assertEqual(response.status_code, 200, response.data)
        self.assertFalse(response.data["replayed"])
        self.assertTrue(self.command("submit").data["replayed"])
        self.api.force_authenticate(self.head)
        response = self.api.get(self.root + "pending-reviews/", self.scope)
        self.private(response)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["results"][0]["version_id"], self.version.pk)
        self.assertEqual(self.api.get(self.version_url, self.scope).status_code, 403)
        response = self.api.get(self.version_url + "review/", self.scope)
        self.private(response)
        self.assertEqual(response.data["state"], "pending")
        self.assertEqual(response.data["template"]["text"], "Synthetic text")
        payload = {"decision": "approved"}
        self.assertEqual(self.command("decision", payload).status_code, 200)
        self.assertTrue(self.command("decision", payload).data["replayed"])
        self.assertEqual(self.api.get(self.root + "pending-reviews/", self.scope).data["results"], [])
        self.api.force_authenticate(self.doctor)
        self.assertEqual(self.api.get(self.version_url + "review/", self.scope).data["state"], "approved")

    def test_no_implicit_approval_or_private_head_read(self):
        self.api.force_authenticate(self.head)
        self.assertEqual(self.api.get(self.version_url + "review/", self.scope).status_code, 403)
        self.assertEqual(self.command("submit").status_code, 403)
        self.api.force_authenticate(self.doctor)
        self.assertEqual(self.command("submit", {"state": "approved"}).status_code, 400)
        self.assertFalse(MedicalTemplateReview.objects.exists())
        self.assertEqual(self.command("submit").status_code, 200)
        self.assertEqual(self.command("decision", {"decision": "approved"}).status_code, 403)
        self.assertEqual(self.api.get(self.root + "pending-reviews/", self.scope).status_code, 403)
        self.api.force_authenticate(self.owner)
        self.assertEqual(self.command("decision", {"decision": "approved"}).status_code, 403)

    def test_rejection_reason_conflict_invalid_key_and_audit_rollback(self):
        self.assertEqual(self.command("submit", key="").status_code, 400)
        with patch("apps.medical.template_reviews.write_template_audit", side_effect=MedicalAuditUnavailable):
            self.assertEqual(self.command("submit").status_code, 503)
        self.assertFalse(MedicalTemplateReview.objects.exists())
        self.assertEqual(self.command("submit").status_code, 200)
        self.api.force_authenticate(self.head)
        self.assertEqual(self.command("decision", {"decision": "rejected"}).status_code, 400)
        payload = {"decision": "rejected", "reason": "Revise wording"}
        self.assertEqual(self.command("decision", payload).status_code, 200)
        self.assertEqual(self.command("decision", payload | {"reason": "Other"}).status_code, 409)
        response = self.api.get(self.version_url + "review/", self.scope)
        self.assertEqual(response.data["decision_reason"], "Revise wording")

    def test_queue_rejects_unbounded_and_unknown_parameters(self):
        self.api.force_authenticate(self.head)
        for extra in ({"limit": 51}, {"before_id": 0}, {"state": "approved"}):
            response = self.api.get(self.root + "pending-reviews/", self.scope | extra)
            self.private(response)
            self.assertEqual(response.status_code, 400)
        self.api.force_authenticate(None)
        response = self.api.get(self.root + "pending-reviews/", self.scope)
        self.private(response)
        self.assertIn(response.status_code, (401, 403))

    def test_foreign_review_is_not_listed_or_read(self):
        other = Business.objects.create(owner=self.owner, name="Other", slug="review-api-other")
        template = MedicalDocumentTemplate.objects.create(business=other, code="foreign", revision=1)
        version = MedicalDocumentTemplateRevision.objects.create(template=template, revision=1,
            author=self.doctor, snapshot_encrypted="must-not-decrypt")
        MedicalTemplateReview.objects.create(version=version, submitted_by=self.doctor)
        self.command("submit")
        self.api.force_authenticate(self.head)
        response = self.api.get(self.root + "pending-reviews/", self.scope)
        self.assertEqual([row["version_id"] for row in response.data["results"]], [self.version.pk])
        self.assertEqual(self.api.get(self.root + "pending-reviews/", {"business_id": other.pk}).status_code, 403)
        self.version_url = f"{self.root}versions/{version.pk}/"
        self.assertEqual(self.api.get(self.version_url + "review/", self.scope).status_code, 403)
        self.assertEqual(self.command("decision", {"decision": "approved"}).status_code, 403)

    def test_stale_version_and_revoked_reviewer_cannot_decide(self):
        self.command("submit")
        save_personal_template_draft(actor=self.doctor, business_id=self.business.pk,
            template_id=self.version.template_id, expected_revision=1, title="Updated", text="",
            idempotency_key="update")
        self.api.force_authenticate(self.head)
        self.assertEqual(self.api.get(self.root + "pending-reviews/", self.scope).data["results"], [])
        self.assertEqual(self.command("decision", {"decision": "approved"}).status_code, 409)
        self.head_assignment.revoked_at = timezone.now()
        self.head_assignment.save(update_fields=["revoked_at"])
        self.assertEqual(self.api.get(self.root + "pending-reviews/", self.scope).status_code, 403)
        self.assertEqual(self.api.get(self.version_url + "review/", self.scope).status_code, 403)
        self.assertEqual(self.command("decision", {"decision": "approved"}).status_code, 403)
