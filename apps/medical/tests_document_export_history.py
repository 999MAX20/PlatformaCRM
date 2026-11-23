from unittest.mock import patch

from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.test import APIClient

from apps.businesses.models import Business, RolePermission
from . import tests_document_artifact_access as fixtures
from .audit import MedicalAuditUnavailable, write_patient_audit
from .document_content import append_document_revision
from .document_export_history import list_document_export_history
from .models import MedicalAuditEvent, MedicalDocument, MedicalRoleAssignment
from .tests_patient_services import key


@override_settings(MEDICAL_DATA_KEYS={"test": key(7)}, MEDICAL_DATA_ACTIVE_KEY_ID="test",
                   MEDICAL_IDENTITY_INDEX_KEY=key(8))
class DocumentExportHistoryTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        fixtures.DocumentArtifactAccessTests.setUpTestData.__func__(cls)

    def setUp(self):
        fixtures.DocumentArtifactAccessTests.setUp(self)

    def scope(self, basis="appointment"):
        return {"actor": self.head if basis == "head" else self.doctor,
            "business_id": self.business.pk, "patient_id": self.patient.pk, "version_id": self.version.pk,
            **{"appointment": {"appointment_id": self.appointment.pk},
               "participation": {"participation_id": self.participation.pk},
               "correction": {"correction_access_id": self.document_grant.pk},
               "head": {"head_branch_id": self.first.pk}}[basis]}

    def event(self, action="document_exported", **changes):
        return write_patient_audit(**({"actor": self.doctor, "business": self.business, "patient": self.patient,
            "action": action, "document_version": self.version} | changes))

    def test_every_current_basis_can_read_history_without_export_permission(self):
        first = self.event()
        second = self.event("document_print_requested", actor=self.head)
        self.event("read")
        RolePermission.objects.filter(business_role=self.role, resource="medical_documents", action="export").update(is_allowed=False)
        for basis in ("appointment", "participation", "correction", "head"):
            rows = list_document_export_history(**self.scope(basis))["results"]
            self.assertEqual([row["id"] for row in rows], [second.pk, first.pk])
            self.assertEqual(rows[0]["actor"], {"id": self.head.pk, "name": self.head.full_name})
            self.assertEqual(rows[0]["revision"], self.version.revision)
            self.assertEqual(set(rows[0]), {"id", "action", "created_at", "actor", "version_id", "revision"})

    def test_cursor_is_stable_and_other_documents_are_excluded(self):
        events = [self.event() for _ in range(3)]
        other = MedicalDocument.objects.create(business=self.business, encounter=self.encounter_record, template_code="other")
        version = append_document_revision(document=other, source_version=self.first_version, author=self.doctor,
            template={"code": "other", "version": 1, "title": "Other", "text": "Private"})
        self.event(document_version=version)
        later = append_document_revision(document=self.version.document, source_version=self.first_version, author=self.doctor,
            template={"code": "synthetic", "version": 1, "title": "Synthetic", "text": "Later revision"})
        self.event(document_version=later)
        page = list_document_export_history(**self.scope(), limit=2)
        self.assertEqual([row["id"] for row in page["results"]], [events[2].pk, events[1].pk])
        self.event()
        next_page = list_document_export_history(**self.scope(), limit=2, before_id=page["next_before_id"])
        self.assertEqual([row["id"] for row in next_page["results"]], [events[0].pk])
        self.assertIsNone(next_page["next_before_id"])
        for changes in ({"limit": 51}, {"limit": True}, {"before_id": 0}):
            with self.assertRaises(ValidationError):
                list_document_export_history(**self.scope(), **changes)

    def test_empty_read_is_audited_and_audit_failure_is_closed(self):
        self.assertEqual(list_document_export_history(**self.scope())["results"], [])
        self.assertTrue(MedicalAuditEvent.objects.filter(action="read", document_version=self.version).exists())
        with patch("apps.medical.document_export_history.write_patient_audit", side_effect=MedicalAuditUnavailable):
            with self.assertRaises(MedicalAuditUnavailable):
                list_document_export_history(**self.scope())

    def test_wrong_tenant_branch_version_and_expired_grant_are_denied(self):
        foreign = Business.objects.create(owner=self.owner, name="Other", slug="history-other")
        for changes in ({"business_id": foreign.pk}, {"version_id": self.version.pk + 100000}, {"actor": self.owner}):
            with self.assertRaises(PermissionDenied):
                list_document_export_history(**(self.scope() | changes))
        with self.assertRaises(PermissionDenied):
            list_document_export_history(**(self.scope("head") | {"head_branch_id": self.second.pk}))
        with patch("apps.medical.correction_access_context.timezone.now", return_value=self.document_grant.expires_at):
            with self.assertRaises(PermissionDenied):
                list_document_export_history(**self.scope("correction"))

    def test_revocation_closes_all_bases(self):
        MedicalRoleAssignment.objects.filter(pk__in=[self.assignment.pk, self.head_assignment.pk]).update(revoked_at=timezone.now())
        for basis in ("appointment", "participation", "correction", "head"):
            with self.assertRaises(PermissionDenied):
                list_document_export_history(**self.scope(basis))

    def test_http_is_private_strict_and_reports_denied_access(self):
        api = APIClient(); api.force_authenticate(self.doctor)
        scope = self.scope(); scope.pop("actor"); version_id = scope.pop("version_id")
        path = f"/api/medical/documents/versions/{version_id}/export-history/"
        self.event()
        response = api.get(path, scope)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Cache-Control"], "no-store, private")
        self.assertEqual(len(response.data["results"]), 1)
        self.assertEqual(api.get(path, scope | {"action": "export"}).status_code, 400)
        api.force_authenticate(self.owner)
        self.assertEqual(api.get(path, scope).status_code, 403)
        self.assertTrue(MedicalAuditEvent.objects.filter(action="access_denied", actor=self.owner).exists())
