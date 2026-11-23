from unittest.mock import patch

from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.exceptions import NotFound, PermissionDenied, ValidationError

from apps.businesses.models import Business, RolePermission
from . import tests_access_basis_combinations as fixtures
from . import tests_patient_services as crypto
from .correction_access_services import request_correction_access, review_correction_access
from .document_artifact_access import document_artifact_access
from .document_content import append_document_revision
from .audit import write_patient_audit
from .models import MedicalDocument, MedicalRoleAssignment


@override_settings(MEDICAL_DATA_KEYS={"test": crypto.key(7)}, MEDICAL_DATA_ACTIVE_KEY_ID="test",
                   MEDICAL_IDENTITY_INDEX_KEY=crypto.key(8))
class DocumentArtifactAccessTests(TestCase):
    def test_export_audit_accepts_exact_version_for_every_current_basis(self):
        for basis in ("appointment", "participation", "correction", "head"):
            context = self.access(basis, action="export")
            actor = self.head if basis == "head" else self.doctor
            for action in ("document_exported", "document_print_requested"):
                event = write_patient_audit(actor=actor, business=context.business, patient=context.patient,
                    action=action, document_version=context.version, correction_access=context.correction)
                self.assertEqual(event.document_version_id, self.version.pk)
                self.assertEqual(event.correction_access_id, context.correction.pk if context.correction else None)

    @classmethod
    def setUpTestData(cls):
        fixtures.AccessBasisCombinationTests.setUpTestData.__func__(cls)
        for action in ("view", "create", "update", "export"):
            RolePermission.objects.create(business_role=cls.role, resource="medical_documents", action=action,
                                          scope="business", is_allowed=True)

    def setUp(self):
        fixtures.AccessBasisCombinationTests.setUp(self)
        document = MedicalDocument.objects.create(business=self.business, encounter=self.encounter_record,
                                                   template_code="synthetic")
        self.version = append_document_revision(document=document, source_version=self.first_version,
            author=self.doctor, template={"code": "synthetic", "version": 1, "title": "Synthetic", "text": "Private"})
        grant = request_correction_access(actor=self.doctor, business_id=self.business.pk,
            encounter_id=self.encounter_record.pk, document_id=document.pk,
            expected_patient_revision=self.patient.revision, expected_target_revision=1,
            reason="Synthetic document correction", idempotency_key="document-request")[0]
        self.document_grant = review_correction_access(actor=self.head, business_id=self.business.pk,
            request_id=grant.pk, expected_revision=1, decision="approve", reason="Synthetic approval",
            idempotency_key="document-review")[0]

    def access(self, basis="appointment", **changes):
        scopes = {"appointment": {"appointment_id": self.appointment.pk},
            "participation": {"participation_id": self.participation.pk},
            "correction": {"correction_access_id": self.document_grant.pk},
            "head": {"head_branch_id": self.first.pk, "actor": self.head}}
        return document_artifact_access(**({"actor": self.doctor, "business_id": self.business.pk,
            "patient_id": self.patient.pk, "version_id": self.version.pk} | scopes[basis] | changes))

    def test_four_current_bases_allow_exact_document_without_file_permission(self):
        self.assertFalse(RolePermission.objects.filter(business_role=self.role, resource="medical_files").exists())
        for basis in ("appointment", "participation", "correction", "head"):
            for action in ("view", "export"):
                with self.subTest(basis=basis, action=action):
                    self.assertEqual(self.access(basis, action=action).version.pk, self.version.pk)

    def test_document_export_is_separate_from_view_and_file_export(self):
        RolePermission.objects.filter(business_role=self.role, resource="medical_documents", action="export").update(is_allowed=False)
        RolePermission.objects.create(business_role=self.role, resource="medical_files", action="export", scope="business")
        for basis in ("appointment", "participation", "correction", "head"):
            with self.subTest(basis=basis):
                self.access(basis)
                with self.assertRaises(PermissionDenied):
                    self.access(basis, action="export")

    def test_correction_cannot_expand_to_encounter_grant_or_another_document(self):
        with self.assertRaises(PermissionDenied):
            self.access("correction", correction_access_id=self.correction.pk)
        document = MedicalDocument.objects.create(business=self.business, encounter=self.encounter_record,
                                                   template_code="other")
        other = append_document_revision(document=document, source_version=self.first_version, author=self.doctor,
            template={"code": "other", "version": 1, "title": "Other", "text": "Other"})
        with self.assertRaises(PermissionDenied):
            self.access("correction", version_id=other.pk)
        with patch("apps.medical.correction_access_context.timezone.now", return_value=self.document_grant.expires_at):
            with self.assertRaises(PermissionDenied):
                self.access("correction")
            self.access("participation")

    def test_head_branch_scope_and_nonmedical_owner_are_not_bypasses(self):
        with self.assertRaises(PermissionDenied):
            self.access("head", head_branch_id=self.second.pk)
        with self.assertRaises(PermissionDenied):
            self.access("head", actor=self.doctor)
        for basis in ("appointment", "participation", "correction", "head"):
            with self.subTest(basis=basis), self.assertRaises(PermissionDenied):
                self.access(basis, actor=self.owner)

    def test_revocation_blocks_every_basis_and_invalid_ids_do_not_resolve(self):
        MedicalRoleAssignment.objects.filter(pk__in=[self.assignment.pk, self.head_assignment.pk]).update(revoked_at=timezone.now())
        for basis in ("appointment", "participation", "correction", "head"):
            with self.subTest(basis=basis), self.assertRaises(PermissionDenied):
                self.access(basis)
        for changes in ({"version_id": True}, {"appointment_id": None}, {"participation_id": self.participation.pk}):
            with self.subTest(changes=changes), self.assertRaises(ValidationError):
                self.access(**changes)

    def test_closed_booking_does_not_remove_independent_participation(self):
        type(self.appointment).objects.filter(pk=self.appointment.pk).update(status="completed")
        with self.assertRaises(PermissionDenied):
            self.access("appointment")
        self.access("participation")
        self.access("correction")

    def test_foreign_patient_and_business_never_resolve_version(self):
        with self.assertRaises(NotFound):
            self.access(patient_id=self.patient.pk + 100000)
        other = Business.objects.create(owner=self.owner, name="Other clinic", slug="artifact-acl-other")
        with self.assertRaises(PermissionDenied):
            self.access(business_id=other.pk)
        with self.assertRaises(PermissionDenied):
            self.access(version_id=self.version.pk + 100000)
