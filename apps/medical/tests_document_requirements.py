from unittest.mock import patch

from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied
from rest_framework.test import APIClient

from apps.businesses.models import Business
from . import tests_document_rule_snapshots as fixtures
from .audit import MedicalAuditUnavailable
from .document_requirements import read_document_requirements
from .models import MedicalAuditEvent, MedicalRoleAssignment
from .tests_document_rules import default_rule
from .tests_patient_services import key


@override_settings(MEDICAL_DATA_KEYS={"test": key(7)}, MEDICAL_DATA_ACTIVE_KEY_ID="test",
                   MEDICAL_IDENTITY_INDEX_KEY=key(8))
class DocumentRequirementsTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        fixtures.DocumentRuleSnapshotTests.setUpTestData.__func__(cls)

    def setUp(self):
        fixtures.DocumentRuleSnapshotTests.setUp(self)

    rules = fixtures.DocumentRuleSnapshotTests.rules
    save = fixtures.DocumentRuleSnapshotTests.save

    def configure(self, fields):
        return self.rules(content={"name": "Synthetic required fields", "default": default_rule(required_fields=fields),
            "services": []})

    def read(self, version, **changes):
        return read_document_requirements(**(dict(actor=self.doctor, business_id=self.business.pk,
            patient_id=self.patient.pk, version_id=version.pk, appointment_id=self.appointment.pk) | changes))

    def test_required_fields_use_saved_values_not_updated_business(self):
        self.business.legal_name = ""
        self.business.save(update_fields=["legal_name"])
        self.configure(["patient.full_name", "clinic.legal_name"])
        version = self.save()
        before = self.read(version)
        self.assertEqual(before["fields"], [{"field": "patient.full_name", "present": True},
            {"field": "clinic.legal_name", "present": False}])
        self.assertFalse(before["fields_complete"])
        self.business.legal_name = "Synthetic legal name added later"
        self.business.save(update_fields=["legal_name"])
        self.assertEqual(self.read(version), before)
        new = self.save(idempotency_key="new-filled-document")
        self.assertTrue(self.read(new)["fields_complete"])

    def test_whitespace_is_not_a_complete_required_field(self):
        self.business.legal_name = "   "
        self.business.save(update_fields=["legal_name"])
        self.configure(["clinic.legal_name"])
        self.assertFalse(self.read(self.save())["fields_complete"])

    def test_unconfigured_document_is_not_complete_and_no_fields_is_explicit(self):
        legacy = self.save()
        self.assertFalse(self.read(legacy)["configured"])
        self.assertFalse(self.read(legacy)["fields_complete"])
        self.configure([])
        self.assertFalse(self.read(legacy)["configured"])
        configured = self.read(self.save(idempotency_key="configured-new"))
        self.assertTrue(configured["configured"])
        self.assertTrue(configured["fields_complete"])
        self.assertEqual(configured["document_state"], "draft")

    def test_old_revision_stays_readable_but_is_not_current(self):
        self.configure(["patient.full_name"])
        version = self.save()
        latest = self.save(document_id=version.document_id, expected_document_revision=1,
            document_text="Synthetic changed contents", reason="Synthetic correction", idempotency_key="edit")
        self.assertFalse(self.read(version)["current"])
        self.assertTrue(self.read(latest)["current"])
        self.assertEqual(self.read(version)["rule_version_id"], self.read(latest)["rule_version_id"])

    def test_owner_foreign_business_and_revocation_cannot_read(self):
        self.configure([])
        version = self.save()
        other = Business.objects.create(owner=self.owner, name="Foreign requirements", slug="foreign-requirements")
        for changes in ({"actor": self.owner}, {"business_id": other.pk},
                {"appointment_id": None, "head_branch_id": self.encounter_record.branch_id}):
            with self.assertRaises(PermissionDenied):
                self.read(version, **changes)
        MedicalRoleAssignment.objects.filter(member__user=self.doctor).update(revoked_at=timezone.now())
        with self.assertRaises(PermissionDenied):
            self.read(version)

    def test_read_is_audited_and_failed_audit_releases_no_result(self):
        self.configure([])
        version = self.save()
        self.read(version)
        self.assertTrue(MedicalAuditEvent.objects.filter(document_version=version, action="read").exists())
        with patch("apps.medical.document_requirements.write_patient_audit", side_effect=MedicalAuditUnavailable):
            with self.assertRaises(MedicalAuditUnavailable):
                self.read(version)

    def test_http_is_private_strict_and_does_not_return_field_values(self):
        self.configure(["patient.full_name"])
        version = self.save()
        api = APIClient()
        api.force_authenticate(self.doctor)
        path = f"/api/medical/documents/versions/{version.pk}/requirements/"
        scope = {"business_id": self.business.pk, "patient_id": self.patient.pk, "appointment_id": self.appointment.pk}
        response = api.get(path, scope)
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response["Cache-Control"], "no-store, private")
        self.assertEqual(response.data["fields"], [{"field": "patient.full_name", "present": True}])
        self.assertEqual(api.get(path, scope | {"language": "ru"}).status_code, 400)
        api.force_authenticate(self.owner)
        denied = api.get(path, scope)
        self.assertEqual(denied.status_code, 403)
        self.assertEqual(denied["Cache-Control"], "no-store, private")
        self.assertTrue(MedicalAuditEvent.objects.filter(action="access_denied", actor=self.owner).exists())
