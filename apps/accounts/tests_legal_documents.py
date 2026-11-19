from django.core.cache import cache
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.businesses.models import Business
from apps.core.models import AuditLog


@override_settings(AUTH_PRIVILEGED_MFA_REQUIRED=False)
class SignupDocumentTests(TestCase):
    def setUp(self):
        cache.clear()
        self.api = APIClient()
        self.payload = {"email": "documents@example.invalid", "password": "DocumentsTest928!", "business_name": "Document fixture"}
        self.documents = ["terms", "privacy", "personal-data", "company-data"]

    def test_missing_partial_and_invalid_acknowledgements_create_nothing(self):
        for value in [None, [], *[self.documents[:index] + self.documents[index+1:] for index in range(4)], ["unknown"], True]:
            with self.subTest(value=value):
                cache.clear()
                payload = dict(self.payload)
                if value is not None:
                    payload["accepted_documents"] = value
                response = self.api.post("/api/auth/signup/owner/", payload, format="json")
                self.assertEqual(response.status_code, 400)
                self.assertFalse(User.objects.filter(email=self.payload["email"]).exists())
                self.assertFalse(Business.objects.exists())
                self.assertFalse(AuditLog.objects.filter(metadata__event="signup_document_acknowledgements").exists())

    def test_complete_acknowledgements_are_audited_as_placeholders(self):
        response = self.api.post("/api/auth/signup/owner/", {**self.payload, "accepted_documents": self.documents}, format="json")
        self.assertEqual(response.status_code, 201, response.data)
        user = User.objects.get(email=self.payload["email"])
        event = AuditLog.objects.get(actor=user, metadata__event="signup_document_acknowledgements")
        self.assertEqual(event.business, Business.objects.get(owner=user))
        self.assertEqual(event.metadata["document_ids"], self.documents)
        self.assertEqual(event.metadata["content_status"], "placeholder")
        self.assertEqual(event.metadata["acceptance_method"], "checkboxes")
        self.assertIsNone(event.metadata["notice_version"])

    def test_submit_notice_records_method_version_and_all_documents_once(self):
        payload = {**self.payload, "accepted_documents": self.documents, "acceptance_method": "signup_submit"}
        response = self.api.post("/api/auth/signup/owner/", payload, format="json")
        self.assertEqual(response.status_code, 201, response.data)
        user = User.objects.get(email=self.payload["email"])
        event = AuditLog.objects.get(actor=user, metadata__event="signup_document_acknowledgements")
        self.assertEqual(event.business.owner, user)
        self.assertEqual(event.metadata["document_ids"], self.documents)
        self.assertEqual(event.metadata["acceptance_method"], "signup_submit")
        self.assertEqual(event.metadata["notice_version"], "signup-submit-2026-11-19")
        self.assertEqual(event.metadata["content_status"], "placeholder")
        response = self.api.post("/api/auth/signup/owner/", payload, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(AuditLog.objects.filter(metadata__event="signup_document_acknowledgements").count(), 1)

    def test_invalid_method_and_incomplete_submit_create_nothing(self):
        for extra in (
            {"acceptance_method": "automatic", "accepted_documents": self.documents},
            {"acceptance_method": "signup_submit", "accepted_documents": self.documents[:-1]},
            {"acceptance_method": "signup_submit"},
        ):
            with self.subTest(extra=extra):
                cache.clear()
                response = self.api.post("/api/auth/signup/owner/", {**self.payload, **extra}, format="json")
                self.assertEqual(response.status_code, 400)
                self.assertFalse(User.objects.filter(email=self.payload["email"]).exists())
                self.assertFalse(Business.objects.exists())
                self.assertFalse(AuditLog.objects.filter(metadata__event="signup_document_acknowledgements").exists())
