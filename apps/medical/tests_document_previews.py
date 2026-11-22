from datetime import datetime, timezone
from unittest.mock import patch

from django.test import SimpleTestCase, TestCase, override_settings
from rest_framework.exceptions import NotFound, PermissionDenied, ValidationError

from apps.clients.models import Client
from apps.core.domain_errors import InvalidTransition
from . import tests_document_template_source as fixtures
from . import tests_patient_services as crypto_fixtures
from .audit import MedicalAuditUnavailable
from .document_previews import preview_document_template
from .document_content import append_document_revision
from .document_rendering import render_document_text
from .models import MedicalAuditEvent, MedicalDocumentRevision


class LiteralDocumentRenderingTests(SimpleTestCase):
    def setUp(self):
        self.context = {"patient_identity": {"full_name": "{{clinical.diagnosis}}", "iin": None, "demographics": {}},
            "encounter_source": {"timezone": "Asia/Almaty", "record_number": "SYNTHETIC"},
            "doctor": {"name": "Synthetic doctor"}, "business": dict.fromkeys(("name", "legal_name", "tax_id", "address", "phone"), ""),
            "branch": dict.fromkeys(("name", "address", "city", "phone"), ""), "clinical": {"diagnosis": "Confirmed synthetic conclusion"}}

    def render(self, text):
        return render_document_text(text, self.context, started_at=datetime(2026, 1, 1, 22, 0, tzinfo=timezone.utc))

    def test_single_pass_allowlist_no_expression_evaluation_and_missing_fields(self):
        result = self.render("{{ patient.full_name }} {{patient.iin}} {{__import__('os')}} {{clinical.diagnosis}}")
        self.assertEqual(result["document_text"], "{{clinical.diagnosis}}  {{__import__('os')}} Confirmed synthetic conclusion")
        self.assertEqual(result["missing_fields"], ["patient.iin"])
        self.assertEqual(result["unknown_fields"], ["__import__('os')"])

    def test_local_date_and_literal_non_template_text(self):
        self.assertEqual(self.render("{{encounter.date}} {{record.number}} <b>literal</b>")["document_text"],
                         "2026-01-02 SYNTHETIC <b>literal</b>")
        self.assertEqual(self.render("Unchanged text")["document_text"], "Unchanged text")

    def test_expansion_limit_stops_large_repeated_fields(self):
        self.context["clinical"]["plan"] = "x" * 32768
        with self.assertRaises(ValidationError):
            self.render("{{clinical.plan}}" * 5)
        with self.assertRaises(ValidationError):
            self.render("x" * 131073)

    def test_risk_placeholders_keep_missing_distinct_from_clinician_text(self):
        template = "{{clinical.allergies}} / {{clinical.contraindications}}"
        missing = self.render(template)
        self.assertEqual(missing["missing_fields"], ["clinical.allergies", "clinical.contraindications"])
        self.assertEqual(missing["unknown_fields"], [])
        self.context["clinical"].update(allergies="Synthetic allergy", contraindications="Synthetic restriction")
        rendered = self.render(template)
        self.assertEqual(rendered["document_text"], "Synthetic allergy / Synthetic restriction")
        self.assertEqual(rendered["missing_fields"], [])


@override_settings(MEDICAL_DATA_KEYS={"test": crypto_fixtures.key(7)}, MEDICAL_DATA_ACTIVE_KEY_ID="test",
                   MEDICAL_IDENTITY_INDEX_KEY=crypto_fixtures.key(8))
class DocumentPreviewTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        fixtures.DocumentTemplateSourceTests.setUpTestData.__func__(cls)

    def setUp(self):
        fixtures.DocumentTemplateSourceTests.setUp(self)
        fixtures.DocumentTemplateSourceTests.approve(self)

    def preview(self, **overrides):
        return preview_document_template(**(dict(actor=self.doctor, business_id=self.business.pk,
            patient_id=self.patient.pk, encounter_id=self.encounter_record.pk,
            appointment_id=self.appointment.pk, template_version_id=self.template.pk) | overrides))

    def save(self, **overrides):
        return fixtures.DocumentTemplateSourceTests.save(self, **overrides)

    def test_preview_is_audited_and_creates_no_document(self):
        result = self.preview()
        self.assertEqual(result["document_text"], "Original {{patient}} text")
        self.assertEqual(result["unknown_fields"], ["patient"])
        self.assertEqual(len(result["source_digest"]), 64)
        self.assertEqual(result["patient_revision"], self.patient.revision)
        self.assertTrue(MedicalAuditEvent.objects.filter(action="read", encounter_version=self.first_version).exists())
        self.assertFalse(MedicalDocumentRevision.objects.exists())
        first, _ = self.save(expected_source_digest=result["source_digest"])
        Client.objects.filter(pk=self.patient.client_id).update(full_name="Changed synthetic patient")
        self.assertTrue(self.save(expected_source_digest=result["source_digest"])[1])
        self.assertEqual(MedicalDocumentRevision.objects.count(), 1)
        self.assertEqual(first.revision, 1)

    def test_changed_patient_or_clinic_invalidates_preview_before_save(self):
        token = self.preview()["source_digest"]
        type(self.business).objects.filter(pk=self.business.pk).update(address="Changed synthetic clinic")
        with self.assertRaises(InvalidTransition):
            self.save(expected_source_digest=token)
        self.assertFalse(MedicalDocumentRevision.objects.exists())
        fresh = self.preview()["source_digest"]
        self.assertNotEqual(fresh, token)
        Client.objects.filter(pk=self.patient.client_id).update(full_name="Changed synthetic patient")
        with self.assertRaises(InvalidTransition):
            self.save(expected_source_digest=fresh)

    def test_owner_wrong_patient_wrong_document_and_revoked_branch_deny(self):
        for changes in ({"actor": self.owner}, {"patient_id": self.patient.pk + 999}, {"document_id": 999}):
            with self.subTest(changes=changes), self.assertRaises((PermissionDenied, NotFound)) as caught:
                self.preview(**changes)
            self.assertIn(getattr(caught.exception, "status_code", None), (403, 404))
        self.assignment.branches.clear()
        with self.assertRaises(PermissionDenied):
            self.preview()

    def test_preview_audit_failure_rolls_back_all_read_events(self):
        before = MedicalAuditEvent.objects.count()
        with patch("apps.medical.document_previews.write_patient_audit", side_effect=MedicalAuditUnavailable()):
            with self.assertRaises(MedicalAuditUnavailable):
                self.preview()
        self.assertEqual(MedicalAuditEvent.objects.count(), before)

    def test_invalid_digest_rejected_and_forged_digest_conflicts(self):
        for value in (True, "", "g" * 64):
            with self.assertRaises(ValidationError):
                self.save(expected_source_digest=value)
        with self.assertRaises(InvalidTransition):
            self.save(expected_source_digest="0" * 64)

    def test_source_change_between_check_and_snapshot_rolls_back(self):
        token = self.preview()["source_digest"]
        def changed(**kwargs):
            type(self.doctor).objects.filter(pk=self.doctor.pk).update(full_name="Changed during capture")
            return append_document_revision(**kwargs)
        with patch("apps.medical.document_services.append_document_revision", side_effect=changed):
            with self.assertRaises(InvalidTransition):
                self.save(expected_source_digest=token)
        self.assertFalse(MedicalDocumentRevision.objects.exists())
