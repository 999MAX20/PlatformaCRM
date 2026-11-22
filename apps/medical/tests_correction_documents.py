from unittest.mock import patch

from django.db import DatabaseError
from django.test import TestCase, override_settings
from rest_framework.exceptions import PermissionDenied, ValidationError

from apps.branches.models import BranchAccess
from apps.businesses.models import RolePermission
from . import tests_document_template_source as fixtures
from . import tests_patient_services as crypto_fixtures
from .audit import MedicalAuditUnavailable
from .correction_access_reads import read_correction_target
from .correction_access_services import request_correction_access, review_correction_access
from .correction_access_writes import save_correction_target
from .document_content import read_document_revision
from .models import MedicalAuditEvent, MedicalDocumentRevision, MedicalRoleAssignment


@override_settings(MEDICAL_DATA_KEYS={"test": crypto_fixtures.key(7)}, MEDICAL_DATA_ACTIVE_KEY_ID="test",
                   MEDICAL_IDENTITY_INDEX_KEY=crypto_fixtures.key(8))
class CorrectionDocumentTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        fixtures.DocumentTemplateSourceTests.setUpTestData.__func__(cls)
        head_assignment = MedicalRoleAssignment.objects.get(member__user=cls.head)
        head_assignment.branches.add(cls.first)
        BranchAccess.objects.create(member=head_assignment.member, all_branches=True)
        for action in ("manage", "view"):
            RolePermission.objects.create(business_role=head_assignment.business_role, resource="medical_records",
                action=action, scope="business")

    def setUp(self):
        fixtures.DocumentTemplateSourceTests.setUp(self)
        fixtures.DocumentTemplateSourceTests.approve(self)
        self.original = fixtures.DocumentTemplateSourceTests.save(self)[0]
        self.grant = request_correction_access(actor=self.doctor, business_id=self.business.pk,
            encounter_id=self.encounter_record.pk, document_id=self.original.document_id,
            expected_patient_revision=self.patient.revision, expected_target_revision=1,
            reason="Synthetic document correction", idempotency_key="request")[0]
        self.grant = review_correction_access(actor=self.head, business_id=self.business.pk, request_id=self.grant.pk,
            expected_revision=1, decision="approve", reason="Synthetic approval", idempotency_key="review")[0]

    def save(self, **overrides):
        return save_correction_target(**(dict(actor=self.doctor, business_id=self.business.pk, request_id=self.grant.pk,
            expected_revision=1, reason="Synthetic correction", document_text="Corrected synthetic text", idempotency_key="save") | overrides))

    def test_correction_retains_captured_identity_and_clinical_source_after_later_changes(self):
        before = read_document_revision(self.original)
        type(self.encounter_record).objects.filter(pk=self.encounter_record.pk).update(revision=2)
        type(self.appointment).objects.filter(pk=self.appointment.pk).update(status="completed")
        self.business.legal_name = "Later name"
        self.business.save(update_fields=["legal_name"])
        version, replayed = self.save()
        after = read_document_revision(version)
        self.assertFalse(replayed)
        self.assertEqual(after["document_text"], "Corrected synthetic text")
        for field in set(before) - {"document_text", "reason", "prepared_by"}:
            self.assertEqual(after[field], before[field], field)
        self.assertEqual(version.source_version_id, self.original.source_version_id)
        self.assertEqual(read_document_revision(self.original), before)
        self.assertTrue(self.save()[1])
        self.assertEqual(MedicalAuditEvent.objects.get(action="document_draft_saved").correction_access_id, self.grant.pk)
        result = read_correction_target(actor=self.doctor, business_id=self.business.pk, request_id=self.grant.pk)
        self.assertEqual(result["content"]["document_text"], "Corrected synthetic text")

    def test_document_permission_does_not_allow_encounter_edit_and_audit_failure_rolls_back(self):
        with self.assertRaises(ValidationError):
            self.save(content={"plan": "Not allowed"})
        with patch("apps.medical.audit.MedicalAuditEvent.objects.create", side_effect=DatabaseError), self.assertRaises(MedicalAuditUnavailable):
            self.save()
        self.assertEqual(MedicalDocumentRevision.objects.count(), 1)
        self.assignment.branches.clear()
        with self.assertRaises(PermissionDenied):
            self.save()
