from unittest.mock import patch

from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.exceptions import NotFound, PermissionDenied, ValidationError
from rest_framework.test import APIClient

from apps.businesses.models import Business, RolePermission
from . import tests_document_artifact_access as fixtures
from . import tests_patient_services as crypto
from .audit import MedicalAuditUnavailable
from .document_reads import list_document_revisions, list_patient_documents
from .document_services import read_document_for_treating_clinician
from .models import MedicalAuditEvent, MedicalRoleAssignment


@override_settings(MEDICAL_DATA_KEYS={"test": crypto.key(7)}, MEDICAL_DATA_ACTIVE_KEY_ID="test",
                   MEDICAL_IDENTITY_INDEX_KEY=crypto.key(8))
class DocumentHeadReadTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        fixtures.DocumentArtifactAccessTests.setUpTestData.__func__(cls)

    def setUp(self):
        fixtures.DocumentArtifactAccessTests.setUp(self)

    def scope(self, **changes):
        return dict(actor=self.head, business_id=self.business.pk, patient_id=self.patient.pk,
                    head_branch_id=self.first.pk) | changes

    def test_head_lists_history_and_exact_version_without_own_booking(self):
        type(self.appointment).objects.filter(pk=self.appointment.pk).update(status="completed")
        page = list_patient_documents(**self.scope())
        self.assertEqual([row["version_id"] for row in page["results"]], [self.version.pk])
        history = list_document_revisions(document_id=self.version.document_id, **self.scope())
        self.assertEqual(history["results"][0]["version_id"], self.version.pk)
        version = read_document_for_treating_clinician(version_id=self.version.pk, **self.scope())
        self.assertEqual(version["snapshot"]["template"]["title"], "Synthetic")
        self.assertTrue(MedicalAuditEvent.objects.filter(patient=self.patient, action="read").exists())

    def test_selected_branch_filters_list_and_rejects_direct_history_and_version(self):
        self.head_assignment.branches.add(self.second)
        scope = self.scope(head_branch_id=self.second.pk)
        self.assertEqual(list_patient_documents(**scope)["results"], [])
        with self.assertRaises(PermissionDenied):
            list_patient_documents(encounter_id=self.encounter_record.pk, **scope)
        with self.assertRaises(PermissionDenied):
            list_document_revisions(document_id=self.version.document_id, **scope)
        with self.assertRaises(PermissionDenied):
            read_document_for_treating_clinician(version_id=self.version.pk, **scope)

    def test_head_branch_grant_is_mandatory_and_cannot_be_combined_with_booking(self):
        with self.assertRaises(PermissionDenied):
            list_patient_documents(**self.scope(head_branch_id=self.second.pk))
        with self.assertRaises(ValidationError):
            list_patient_documents(**self.scope(appointment_id=self.appointment.pk))
        with self.assertRaises(ValidationError):
            list_patient_documents(**self.scope(head_branch_id=True))

    def test_doctor_owner_and_revoked_head_cannot_use_head_scope(self):
        for actor in (self.doctor, self.owner):
            with self.subTest(actor=actor.pk), self.assertRaises(PermissionDenied):
                list_patient_documents(**self.scope(actor=actor))
        MedicalRoleAssignment.objects.filter(pk=self.head_assignment.pk).update(revoked_at=timezone.now())
        with self.assertRaises(PermissionDenied):
            read_document_for_treating_clinician(version_id=self.version.pk, **self.scope())

    def test_tenant_and_record_permission_are_enforced(self):
        other = Business.objects.create(owner=self.owner, name="Other", slug="head-read-other")
        with self.assertRaises(PermissionDenied):
            list_patient_documents(**self.scope(business_id=other.pk))
        with self.assertRaises(NotFound):
            list_patient_documents(**self.scope(patient_id=self.patient.pk + 100000))
        RolePermission.objects.filter(business_role=self.role, resource="medical_records", action="view").update(is_allowed=False)
        with self.assertRaises(PermissionDenied):
            list_patient_documents(**self.scope())

    def test_audit_failure_blocks_even_empty_head_list(self):
        self.head_assignment.branches.add(self.second)
        with patch("apps.medical.document_services.write_patient_audit", side_effect=MedicalAuditUnavailable):
            with self.assertRaises(MedicalAuditUnavailable):
                list_patient_documents(**self.scope(head_branch_id=self.second.pk))

    def test_http_reads_allow_head_scope_but_workspace_does_not_grant_editing(self):
        client = APIClient()
        client.force_authenticate(self.head)
        params = {key: value for key, value in self.scope().items() if key != "actor"}
        root = "/api/medical/documents/"
        for path in (root, f"{root}{self.version.document_id}/revisions/", f"{root}versions/{self.version.pk}/"):
            response = client.get(path, params)
            self.assertEqual(response.status_code, 200, response.data)
            self.assertIn("no-store", response["Cache-Control"])
        response = client.get(root + "workspace-access/", params | {"encounter_id": self.encounter_record.pk})
        self.assertEqual(response.status_code, 400)
        response = client.get(root, params | {"appointment_id": self.appointment.pk})
        self.assertEqual(response.status_code, 400)

    def test_client_entry_exposes_head_documents_only_with_current_document_permission(self):
        client = APIClient()
        client.force_authenticate(self.head)
        params = {"business_id": self.business.pk, "branch_id": self.first.pk, "client_id": self.patient.client_id}
        path = "/api/medical/encounters/client-appointments/"
        response = client.get(path, params)
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data["head_documents"], {"patient_id": self.patient.pk})
        self.assertEqual(response.data["results"], [])
        self.assertEqual(client.get(path, params | {"branch_id": self.second.pk}).status_code, 403)
        client.force_authenticate(self.doctor)
        self.assertNotIn("head_documents", client.get(path, params).data)
        client.force_authenticate(self.head)
        RolePermission.objects.filter(business_role=self.role, resource="medical_documents", action="view").update(is_allowed=False)
        response = client.get(path, params)
        self.assertEqual(response.status_code, 200, response.data)
        self.assertNotIn("head_documents", response.data)
