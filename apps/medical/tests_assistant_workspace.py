from unittest.mock import patch

from django.test import TestCase, override_settings

from apps.businesses.models import Business, RolePermission
from .assistant_invitations import invite_appointment_assistant, revoke_appointment_assistant
from .models import MedicalDocumentTemplate
from .document_review_services import transition_document_review
from . import tests_assistant_api as fixtures
from .tests_patient_services import key


@override_settings(MEDICAL_DATA_KEYS={"test": key(7)}, MEDICAL_DATA_ACTIVE_KEY_ID="test",
                   MEDICAL_IDENTITY_INDEX_KEY=key(8))
class AssistantWorkspaceTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        fixtures.AssistantAPITests.setUpTestData.__func__(cls)

    setUp = fixtures.AssistantAPITests.setUp
    save = fixtures.AssistantAPITests.save
    private = fixtures.AssistantAPITests.private
    approved_template = fixtures.AssistantAPITests.approved_template

    def read(self, path, **changes):
        return self.private(self.api.get(self.root + path, {"business_id": self.business.pk} | changes))

    def test_workspace_and_current_draft_list_are_bound_to_accepted_invitation(self):
        version, _ = self.save()
        response = self.read(f"{self.invitation.pk}/workspace/")
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual((response.data["patient_id"], response.data["encounter_id"]),
                         (self.patient.pk, self.encounter_record.pk))
        self.assertEqual(response.data["actions"], {"create": True, "update": True})
        response = self.read(f"{self.invitation.pk}/drafts/")
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual([row["version_id"] for row in response.data["results"]], [version.pk])
        self.assertNotIn("clinical", str(response.data))
        transition_document_review(actor=self.doctor, business_id=self.business.pk, patient_id=self.patient.pk,
            version_id=version.pk, appointment_id=self.appointment.pk, expected_state_revision=1,
            target="ready_for_review", reason="", idempotency_key="workspace-document-review")
        self.assertEqual(self.read(f"{self.invitation.pk}/drafts/").data["results"], [])

    def test_pending_invitation_has_organizational_inbox_but_no_workspace(self):
        revoke_appointment_assistant(actor=self.doctor, business_id=self.business.pk,
            invitation_id=self.invitation.pk, expected_revision=2, idempotency_key="workspace-revoke")
        pending, _ = invite_appointment_assistant(actor=self.doctor, business_id=self.business.pk,
            patient_id=self.patient.pk, appointment_id=self.appointment.pk, target_member_id=self.assistant_member.pk,
            expected_updated_at=self.appointment.updated_at, idempotency_key="workspace-pending")
        response = self.read("mine/")
        self.assertEqual(response.status_code, 200, response.data)
        self.assertNotIn("patient", str(response.data))
        for path in ("workspace", "drafts", "templates"):
            with self.subTest(path=path):
                self.assertEqual(self.read(f"{pending.pk}/{path}/").status_code, 403)

    def test_templates_are_common_approved_and_active_only(self):
        template = self.approved_template()
        path = f"{self.invitation.pk}/templates/"
        response = self.read(path)
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual([row["version_id"] for row in response.data["results"]], [template.pk])
        MedicalDocumentTemplate.objects.filter(pk=template.template_id).update(is_active=False)
        self.assertEqual(self.read(path).data["results"], [])
        MedicalDocumentTemplate.objects.filter(pk=template.template_id).update(is_active=True, owner_member=self.member)
        self.assertEqual(self.read(path).data["results"], [])

    def test_revocation_foreign_business_and_lost_action_do_not_reuse_old_access(self):
        self.save()
        foreign = Business.objects.create(owner=self.owner, name="Foreign", slug="assistant-workspace-foreign")
        self.assertEqual(self.read(f"{self.invitation.pk}/workspace/", business_id=foreign.pk).status_code, 403)
        RolePermission.objects.filter(business_role=self.assistant_role.business_role,
            resource="medical_documents", action="update").update(is_allowed=False)
        self.assertFalse(self.read(f"{self.invitation.pk}/workspace/").data["actions"]["update"])
        self.assertEqual(self.read(f"{self.invitation.pk}/drafts/").status_code, 403)
        revoke_appointment_assistant(actor=self.doctor, business_id=self.business.pk,
            invitation_id=self.invitation.pk, expected_revision=2, idempotency_key="workspace-end")
        self.assertEqual(self.read(f"{self.invitation.pk}/workspace/").status_code, 403)

    def test_manager_lists_require_own_appointment_and_return_no_clinical_content(self):
        scope = {"patient_id": self.patient.pk, "appointment_id": self.appointment.pk}
        self.assertEqual(self.read("managed/", **scope).status_code, 403)
        self.api.force_authenticate(self.doctor)
        response = self.read("managed/", **scope)
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data["results"][0]["id"], self.invitation.pk)
        self.assertEqual(self.read("candidates/", **scope).data["results"], [])
        self.assertEqual(self.read("managed/", **(scope | {"patient_id": self.patient.pk + 1000})).status_code, 403)

    def test_workspace_audit_failure_prevents_patient_payload(self):
        from .audit import MedicalAuditUnavailable
        with patch("apps.medical.assistant_workspace.write_patient_audit", side_effect=MedicalAuditUnavailable()):
            response = self.read(f"{self.invitation.pk}/workspace/")
        self.assertEqual(response.status_code, 503)
        self.assertNotIn(self.patient.client.full_name, str(response.data))
