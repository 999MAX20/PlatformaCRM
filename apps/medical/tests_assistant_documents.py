from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from rest_framework.exceptions import PermissionDenied

from apps.branches.models import BranchAccess
from apps.businesses.models import Business, BusinessMember, BusinessRole, RolePermission
from apps.core.domain_errors import InvalidTransition
from apps.scheduling.models import Appointment
from .assistant_invitations import invite_appointment_assistant, accept_appointment_assistant, revoke_appointment_assistant
from .document_review_services import transition_document_review
from .assistant_documents import read_assistant_document_draft, preview_assistant_document_template
from .models import MedicalRoleAssignment, MedicalDocumentRevision
from . import tests_document_services as fixtures
from .tests_patient_services import key


@override_settings(MEDICAL_DATA_KEYS={"test": key(7)}, MEDICAL_DATA_ACTIVE_KEY_ID="test",
                   MEDICAL_IDENTITY_INDEX_KEY=key(8))
class AssistantDocumentTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        fixtures.DocumentServiceTests.setUpTestData.__func__(cls)
        cls.assistant = get_user_model().objects.create_user(username="document-assistant", email="document-assistant@example.test")
        member = BusinessMember.objects.create(business=cls.business, user=cls.assistant, role="specialist")
        role = BusinessRole.objects.create(business=cls.business, name="Document assistant")
        cls.assistant_role = MedicalRoleAssignment.objects.create(member=member, business_role=role,
            kind="assistant", granted_by=cls.owner)
        cls.assistant_role.branches.add(cls.first)
        BranchAccess.objects.create(member=member, all_branches=True)
        cls.assistant_member = member
        for resource, actions in (("medical_records", ["view"]), ("medical_documents", ["create", "update"])):
            for action in actions:
                RolePermission.objects.create(business_role=role, resource=resource, action=action, scope="team", is_allowed=True)
        RolePermission.objects.create(business_role=cls.role, resource="medical_participation", action="create",
                                      scope="own", is_allowed=True)

    def setUp(self):
        fixtures.DocumentServiceTests.setUp(self)
        self.invitation, _ = invite_appointment_assistant(actor=self.doctor, business_id=self.business.pk,
            patient_id=self.patient.pk, appointment_id=self.appointment.pk, target_member_id=self.assistant_member.pk,
            expected_updated_at=self.appointment.updated_at, idempotency_key="invite-document-assistant")
        accept_appointment_assistant(actor=self.assistant, business_id=self.business.pk,
            invitation_id=self.invitation.pk, expected_revision=1, idempotency_key="accept-document-assistant")

    def save(self, **changes):
        return fixtures.DocumentServiceTests.save(self, **({"actor": self.assistant,
            "assistant_invitation_id": self.invitation.pk} | changes))

    read = fixtures.DocumentServiceTests.read

    def test_assistant_preparation_preserves_primary_clinician_and_doctor_can_confirm(self):
        version, replayed = self.save()
        self.assertFalse(replayed)
        payload = self.read(version)["snapshot"]
        self.assertEqual(payload["prepared_by"]["user_id"], self.assistant.pk)
        self.assertEqual(payload["performed_by"]["user_id"], self.doctor.pk)
        self.assertEqual(version.author_id, self.assistant.pk)
        self.assertTrue(self.save()[1])
        scope = dict(business_id=self.business.pk, patient_id=self.patient.pk, version_id=version.pk,
            appointment_id=self.appointment.pk, reason="", expected_state_revision=1,
            target="ready_for_review", idempotency_key="submit-assistant-document")
        with self.assertRaises(PermissionDenied):
            transition_document_review(actor=self.assistant, **scope)
        transition_document_review(actor=self.doctor, **scope)
        transition_document_review(actor=self.doctor, **(scope | {"target": "reviewed", "expected_state_revision": 2,
                                                               "idempotency_key": "confirm-assistant-document"}))
        with self.assertRaises(InvalidTransition):
            self.save(document_id=version.document_id, expected_document_revision=1, idempotency_key="edit-reviewed")

    def test_append_preserves_previous_author_and_stale_write_is_rejected(self):
        first, _ = self.save()
        second, _ = self.save(document_id=first.document_id, expected_document_revision=1, idempotency_key="second")
        self.assertEqual((first.revision, second.revision), (1, 2))
        with self.assertRaises(InvalidTransition):
            self.save(document_id=first.document_id, expected_document_revision=1, idempotency_key="stale")
        self.assertEqual(MedicalDocumentRevision.objects.count(), 2)

    def test_explicit_basis_cannot_be_omitted_or_borrowed_by_doctor(self):
        for changes in ({"assistant_invitation_id": None}, {"actor": self.doctor},
                        {"assistant_invitation_id": self.invitation.pk + 1000}):
            with self.subTest(changes=list(changes)), self.assertRaises(PermissionDenied):
                self.save(**changes)

    def test_revoke_and_calendar_cancel_stop_writes_and_replay(self):
        self.save()
        revoke_appointment_assistant(actor=self.doctor, business_id=self.business.pk,
            invitation_id=self.invitation.pk, expected_revision=2, idempotency_key="revoke-document-assistant")
        with self.assertRaises(PermissionDenied):
            self.save()
        self.assertEqual(MedicalDocumentRevision.objects.count(), 1)

    def test_current_calendar_state_and_foreign_business_fail_closed(self):
        foreign = Business.objects.create(owner=self.owner, name="Foreign", slug="assistant-document-foreign")
        with self.assertRaises(PermissionDenied):
            self.save(business_id=foreign.pk)
        Appointment.objects.filter(pk=self.appointment.pk).update(status="cancelled")
        with self.assertRaises(PermissionDenied):
            self.save()

    def test_failed_medical_audit_rolls_back_document_and_retry_is_fresh(self):
        with patch("apps.medical.document_services.write_patient_audit", side_effect=RuntimeError("synthetic audit failure")):
            with self.assertRaises(RuntimeError):
                self.save()
        self.assertFalse(MedicalDocumentRevision.objects.exists())
        self.assertFalse(self.save()[1])

    def test_common_approved_template_source_does_not_expose_personal_or_suspended_templates(self):
        from .common_template_services import save_common_template_draft, submit_common_template
        from .template_reviews import decide_template_review
        from .models import MedicalDocumentTemplate
        head = get_user_model().objects.create_user(username="assistant-template-head", email="assistant-template-head@example.test")
        member = BusinessMember.objects.create(business=self.business, user=head, role="specialist")
        role = BusinessRole.objects.create(business=self.business, name="Assistant template reviewer")
        MedicalRoleAssignment.objects.create(member=member, business_role=role, kind="head", granted_by=self.owner)
        for action in ("view", "create", "update", "approve"):
            RolePermission.objects.create(business_role=role, resource="medical_documents", action=action,
                                          scope="business", is_allowed=True)
        template, _ = save_common_template_draft(actor=head, business_id=self.business.pk,
            title="Synthetic approved assistant source", text="Synthetic document text", idempotency_key="assistant-source")
        source = {"template": None, "template_version_id": template.pk, "document_text": "Synthetic prepared text"}
        with self.assertRaises(PermissionDenied):
            self.save(**source)
        submit_common_template(actor=head, business_id=self.business.pk, version_id=template.pk, idempotency_key="submit-source")
        decide_template_review(actor=head, business_id=self.business.pk, version_id=template.pk,
                               decision="approved", reason="", idempotency_key="approve-source")
        preview = preview_assistant_document_template(actor=self.assistant, business_id=self.business.pk,
            patient_id=self.patient.pk, encounter_id=self.encounter_record.pk, invitation_id=self.invitation.pk,
            template_version_id=template.pk)
        source["expected_source_digest"] = preview["source_digest"]
        version, _ = self.save(**source)
        self.assertEqual(self.read(version)["snapshot"]["template_source"]["version_id"], template.pk)
        MedicalDocumentTemplate.objects.filter(pk=template.template_id).update(is_active=False)
        with self.assertRaises(InvalidTransition):
            self.save(**source)
        MedicalDocumentTemplate.objects.filter(pk=template.template_id).update(is_active=True, owner_member=self.member)
        with self.assertRaises(PermissionDenied):
            self.save(**source)

    def test_assistant_read_is_current_draft_only_and_is_audited_before_content(self):
        first, _ = self.save()
        second, _ = self.save(document_id=first.document_id, expected_document_revision=1, idempotency_key="read-latest")
        scope = dict(actor=self.assistant, business_id=self.business.pk, patient_id=self.patient.pk,
            encounter_id=self.encounter_record.pk, invitation_id=self.invitation.pk, document_id=first.document_id)
        self.assertEqual(read_assistant_document_draft(**scope)["version_id"], second.pk)
        with patch("apps.medical.document_services.write_patient_audit", side_effect=RuntimeError("synthetic failure")):
            with self.assertRaises(RuntimeError):
                read_assistant_document_draft(**scope)
        revoke_appointment_assistant(actor=self.doctor, business_id=self.business.pk,
            invitation_id=self.invitation.pk, expected_revision=2, idempotency_key="revoke-read")
        with self.assertRaises(PermissionDenied):
            read_assistant_document_draft(**scope)
