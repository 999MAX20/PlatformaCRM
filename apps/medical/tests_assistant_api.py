from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from apps.businesses.models import BusinessMember, BusinessRole, RolePermission
from .common_template_services import save_common_template_draft, submit_common_template
from .models import MedicalAuditEvent, MedicalRoleAssignment
from .template_reviews import decide_template_review
from . import tests_assistant_documents as fixtures
from .tests_patient_services import key


@override_settings(MEDICAL_DATA_KEYS={"test": key(7)}, MEDICAL_DATA_ACTIVE_KEY_ID="test",
                   MEDICAL_IDENTITY_INDEX_KEY=key(8))
class AssistantAPITests(TestCase):
    @classmethod
    def setUpTestData(cls):
        fixtures.AssistantDocumentTests.setUpTestData.__func__(cls)

    def setUp(self):
        fixtures.AssistantDocumentTests.setUp(self)
        self.api = APIClient()
        self.api.force_authenticate(self.assistant)
        self.root = "/api/medical/appointment-assistants/"
        self.scope = {"business_id": self.business.pk, "patient_id": self.patient.pk,
                      "encounter_id": self.encounter_record.pk}

    save = fixtures.AssistantDocumentTests.save

    def private(self, response):
        self.assertEqual(response["Cache-Control"], "no-store, private")
        self.assertEqual(response["Pragma"], "no-cache")
        return response

    def post(self, path, payload, key="assistant-api"):
        return self.private(self.api.post(self.root + path, payload, format="json", HTTP_IDEMPOTENCY_KEY=key))

    def approved_template(self):
        head = get_user_model().objects.create_user(username="assistant-api-head", email="assistant-api-head@example.test")
        member = BusinessMember.objects.create(business=self.business, user=head, role="specialist")
        role = BusinessRole.objects.create(business=self.business, name="API reviewer")
        MedicalRoleAssignment.objects.create(member=member, business_role=role, kind="head", granted_by=self.owner)
        for action in ("view", "create", "update", "approve"):
            RolePermission.objects.create(business_role=role, resource="medical_documents", action=action,
                                          scope="business", is_allowed=True)
        version, _ = save_common_template_draft(actor=head, business_id=self.business.pk,
            title="API assistant source", text="Synthetic {{record.number}}", idempotency_key="api-source")
        submit_common_template(actor=head, business_id=self.business.pk, version_id=version.pk, idempotency_key="api-submit")
        decide_template_review(actor=head, business_id=self.business.pk, version_id=version.pk,
            decision="approved", reason="", idempotency_key="api-approve")
        return version

    def test_invite_accept_preview_save_read_and_revoke_over_http(self):
        self.api.force_authenticate(self.doctor)
        response = self.post(f"{self.invitation.pk}/revoke/", {"business_id": self.business.pk, "expected_revision": 2}, "initial-revoke")
        self.assertEqual(response.status_code, 200, response.data)
        response = self.post("", {"business_id": self.business.pk, "patient_id": self.patient.pk,
            "appointment_id": self.appointment.pk, "target_member_id": self.assistant_member.pk,
            "expected_updated_at": self.appointment.updated_at.isoformat()}, "new-http-invite")
        self.assertEqual(response.status_code, 201, response.data)
        invitation_id = response.data["id"]
        self.api.force_authenticate(self.assistant)
        response = self.post(f"{invitation_id}/accept/", {"business_id": self.business.pk, "expected_revision": 1}, "http-accept")
        self.assertEqual(response.status_code, 200, response.data)
        template = self.approved_template()
        response = self.private(self.api.get(self.root + f"{invitation_id}/preview/",
            self.scope | {"template_version_id": template.pk}))
        self.assertEqual(response.status_code, 200, response.data)
        payload = self.scope | {"template_version_id": template.pk, "document_text": response.data["document_text"],
            "expected_source_digest": response.data["source_digest"], "expected_encounter_revision": response.data["encounter_revision"],
            "expected_patient_revision": response.data["patient_revision"]}
        saved = self.post(f"{invitation_id}/save-document/", payload, "http-save")
        self.assertEqual(saved.status_code, 201, saved.data)
        self.assertTrue(self.post(f"{invitation_id}/save-document/", payload, "http-save").data["replayed"])
        read_scope = self.scope | {"document_id": saved.data["id"]}
        response = self.private(self.api.get(self.root + f"{invitation_id}/document/", read_scope))
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data["snapshot"]["prepared_by"]["user_id"], self.assistant.pk)
        self.api.force_authenticate(self.doctor)
        self.assertEqual(self.post(f"{invitation_id}/revoke/", {"business_id": self.business.pk,
            "expected_revision": 2}, "http-revoke").status_code, 200)
        self.api.force_authenticate(self.assistant)
        self.assertEqual(self.private(self.api.get(self.root + f"{invitation_id}/document/", read_scope)).status_code, 403)
        self.assertEqual(self.post(f"{invitation_id}/save-document/", payload, "http-save").status_code, 403)

    def test_strict_scope_and_no_unsigned_identity_or_other_actor_access(self):
        version, _ = self.save()
        url = self.root + f"{self.invitation.pk}/document/"
        scope = self.scope | {"document_id": version.document_id}
        self.assertEqual(self.private(self.api.get(url, scope | {"patient_id": self.patient.pk + 1000})).status_code, 403)
        denied = MedicalAuditEvent.objects.get(action="access_denied")
        self.assertIsNone(denied.patient_id)
        self.assertEqual(self.private(self.api.get(url, scope | {"version_id": version.pk})).status_code, 400)
        self.assertEqual(self.post(f"{self.invitation.pk}/save-document/", self.scope | {"participation_id": 1}).status_code, 400)
        self.api.force_authenticate(self.owner)
        self.assertEqual(self.private(self.api.get(url, scope)).status_code, 403)
        self.api.force_authenticate(None)
        self.assertIn(self.private(self.api.get(url, scope)).status_code, (401, 403))
