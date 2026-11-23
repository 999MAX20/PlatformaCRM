from unittest.mock import patch

from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied, ValidationError

from apps.businesses.models import RolePermission
from apps.core.models import FileAttachment
from . import tests_access_basis_combinations as fixtures
from . import tests_patient_services as crypto
from .file_access import medical_file_context
from .file_reads import medical_file_workspace_access
from .models import MedicalAttachment, MedicalRoleAssignment


@override_settings(MEDICAL_DATA_KEYS={"test": crypto.key(7)}, MEDICAL_DATA_ACTIVE_KEY_ID="test",
                   MEDICAL_IDENTITY_INDEX_KEY=crypto.key(8))
class MedicalFileAccessTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        fixtures.AccessBasisCombinationTests.setUpTestData.__func__(cls)
        for action in ("view", "create", "export"):
            RolePermission.objects.create(business_role=cls.role, resource="medical_files", action=action,
                                          scope="business", is_allowed=True)

    def setUp(self):
        fixtures.AccessBasisCombinationTests.setUp(self)
        self.files = []
        for branch, encounter in ((self.first, self.encounter_record), (self.second, None)):
            blob = FileAttachment.objects.create(business=self.business, uploaded_by=self.doctor,
                file=f"private/attachments/{branch.pk}.pdf", original_name="attachment.pdf",
                content_type="application/pdf", size=10, entity_type="medical_attachment", entity_id="opaque")
            self.files.append(MedicalAttachment.objects.create(business=self.business, patient=self.patient,
                record=self.record, branch=branch, encounter=encounter, attachment=blob, created_by=self.doctor))

    def context(self, basis="appointment", **overrides):
        scopes = {"appointment": {"appointment_id": self.appointment.pk},
                  "participation": {"participation_id": self.participation.pk},
                  "correction": {"correction_access_id": self.correction.pk},
                  "head": {"head_branch_id": self.first.pk, "actor": self.head}}
        return medical_file_context(**({"actor": self.doctor, "business_id": self.business.pk,
                                        "patient_id": self.patient.pk} | scopes[basis] | overrides))

    def test_appointment_and_participation_read_history_across_business_branches(self):
        for basis in ("appointment", "participation"):
            with self.subTest(basis=basis):
                self.assertCountEqual(self.context(basis).files(), self.files)

    def test_correction_scope_never_expands_to_other_patient_files(self):
        self.assertEqual(list(self.context("correction").files()), self.files[:1])
        with patch("apps.medical.correction_access_context.timezone.now", return_value=self.correction.expires_at):
            with self.assertRaises(PermissionDenied):
                self.context("correction")

    def test_head_uses_assigned_area_without_own_appointment_and_cannot_expand_it(self):
        self.assertEqual(list(self.context("head").files()), self.files[:1])
        with self.assertRaises(PermissionDenied):
            self.context("head", head_branch_id=self.second.pk)
        with self.assertRaises(PermissionDenied):
            self.context("head", actor=self.doctor)

    def test_owner_and_wrong_role_do_not_inherit_file_access(self):
        with self.assertRaises(PermissionDenied):
            self.context(actor=self.owner)
        MedicalRoleAssignment.objects.filter(pk=self.assignment.pk).update(kind="reception")
        with self.assertRaises(PermissionDenied):
            self.context()

    def test_missing_file_permission_and_role_revocation_close_all_doctor_bases(self):
        RolePermission.objects.filter(business_role=self.role, resource="medical_files", action="view").update(is_allowed=False)
        for basis in ("appointment", "participation", "correction"):
            with self.subTest(basis=basis), self.assertRaises(PermissionDenied):
                self.context(basis)
        RolePermission.objects.filter(business_role=self.role, resource="medical_files", action="view").update(is_allowed=True)
        MedicalRoleAssignment.objects.filter(pk=self.assignment.pk).update(revoked_at=timezone.now())
        for basis in ("appointment", "participation", "correction"):
            with self.subTest(basis=basis), self.assertRaises(PermissionDenied):
                self.context(basis)

    def test_bases_cannot_be_combined_or_supplied_as_boolean_ids(self):
        with self.assertRaises(ValidationError):
            self.context(participation_id=self.participation.pk)
        with self.assertRaises(ValidationError):
            self.context(appointment_id=True)
        with self.assertRaises(ValidationError):
            self.context(appointment_id=None)

    def test_workspace_resolves_record_for_each_current_basis(self):
        for basis in ({"appointment_id": self.appointment.pk}, {"participation_id": self.participation.pk},
                      {"correction_access_id": self.correction.pk}, {"head_branch_id": self.first.pk}):
            with self.subTest(basis=basis):
                result = medical_file_workspace_access(actor=self.head if "head_branch_id" in basis else self.doctor,
                    business_id=self.business.pk, patient_id=self.patient.pk, **basis)
                self.assertEqual(result["record_id"], self.record.pk)
                self.assertEqual(result["encounter_id"], self.encounter_record.pk if "correction_access_id" in basis else None)

    def test_workspace_correction_rejects_target_substitution_and_expiry(self):
        scope = dict(actor=self.doctor, business_id=self.business.pk, patient_id=self.patient.pk,
                     correction_access_id=self.correction.pk)
        for extra in ({"encounter_id": self.encounter_record.pk + 1000}, {"record_id": self.record.pk + 1000}):
            with self.subTest(extra=extra), self.assertRaises(PermissionDenied):
                medical_file_workspace_access(**scope, **extra)
        with patch("apps.medical.correction_access_context.timezone.now", return_value=self.correction.expires_at):
            with self.assertRaises(PermissionDenied):
                medical_file_workspace_access(**scope)

    def test_workspace_without_active_record_keeps_read_access_without_upload(self):
        type(self.record).objects.filter(pk=self.record.pk).update(state="archived",
            archived_at=timezone.now(), archived_by=self.head)
        result = medical_file_workspace_access(actor=self.doctor, business_id=self.business.pk,
            patient_id=self.patient.pk, participation_id=self.participation.pk)
        self.assertIsNone(result["record_id"])
        self.assertFalse(result["actions"]["upload"])
        self.assertTrue(result["actions"]["export"])
        self.assertCountEqual(self.context("participation").files(), self.files)
