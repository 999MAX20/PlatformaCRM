from copy import deepcopy

from django.test import TestCase, override_settings

from apps.core.domain_errors import InvalidTransition
from . import tests_document_template_source as fixtures
from . import tests_patient_services as crypto_fixtures
from .credential_services import confirm_medical_credentials
from .credential_snapshot import validate_document_credentials
from .document_content import read_document_revision
from .document_previews import preview_document_template
from .document_rendering import document_snapshot_context, render_document_text
from .identity_crypto import MedicalDataUnavailable
from .models import MedicalCredentialRevision


@override_settings(MEDICAL_DATA_KEYS={"test": crypto_fixtures.key(7)}, MEDICAL_DATA_ACTIVE_KEY_ID="test",
                   MEDICAL_IDENTITY_INDEX_KEY=crypto_fixtures.key(8))
class DocumentCredentialTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        fixtures.DocumentTemplateSourceTests.setUpTestData.__func__(cls)

    def setUp(self):
        fixtures.DocumentTemplateSourceTests.setUp(self)
        fixtures.DocumentTemplateSourceTests.approve(self)

    def confirm(self, *, clinic=False, revision=0, value="Synthetic"):
        return confirm_medical_credentials(actor=self.head, business_id=self.business.pk,
            member_id=None if clinic else self.encounter_record.primary_clinician_id,
            content={"license": value} if clinic else {"specialty": value, "position": value, "qualification": ""},
            expected_revision=revision, reason="", idempotency_key=f"{clinic}-{revision}")[0]

    def save(self, **overrides):
        return fixtures.DocumentTemplateSourceTests.save(self, **overrides)

    def test_confirmed_versions_survive_later_changes_and_render_literally(self):
        clinic = self.confirm(clinic=True, value="{{patient.full_name}}")
        doctor = self.confirm()
        version, _ = self.save()
        before = read_document_revision(version)
        self.assertEqual(before["medical_credentials"]["clinic"]["version_id"], clinic.pk)
        self.assertEqual(before["medical_credentials"]["clinician"]["version_id"], doctor.pk)
        self.confirm(clinic=True, revision=1, value="New license")
        self.confirm(revision=1, value="New specialty")
        self.assertEqual(read_document_revision(version), before)
        result = render_document_text("{{clinic.license}} {{doctor.specialty}} {{doctor.position}} {{doctor.qualification}}",
            document_snapshot_context(before), started_at=self.encounter_record.started_at)
        self.assertEqual(result["document_text"], "{{patient.full_name}} Synthetic Synthetic ")
        self.assertEqual(result["missing_fields"], ["doctor.qualification"])

    def test_absent_or_unconfirmed_credentials_do_not_become_confirmed_document_data(self):
        doctor = self.confirm()
        MedicalCredentialRevision.objects.filter(pk=doctor.pk).update(confirmed_by=None, confirmed_at=None)
        version, _ = self.save()
        self.assertEqual(read_document_revision(version)["medical_credentials"], {"clinic": None, "clinician": None})

    def test_confirmation_change_invalidates_preview(self):
        preview = preview_document_template(actor=self.doctor, business_id=self.business.pk,
            patient_id=self.patient.pk, encounter_id=self.encounter_record.pk,
            appointment_id=self.appointment.pk, template_version_id=self.template.pk)
        self.confirm(clinic=True)
        with self.assertRaises(InvalidTransition):
            self.save(expected_source_digest=preview["source_digest"])

    def test_snapshot_rejects_foreign_binding_and_invalid_confirmation(self):
        self.confirm()
        version, _ = self.save()
        source = read_document_revision(version)["medical_credentials"]
        for key, value in (("business_id", self.business.pk + 1), ("member_id", True),
                           ("confirmed_at", "not-a-date"), ("confirmed_by_id", None)):
            forged = deepcopy(source)
            forged["clinician"][key] = value
            with self.subTest(key=key), self.assertRaises(MedicalDataUnavailable):
                validate_document_credentials(forged, business_id=self.business.pk,
                    member_id=self.encounter_record.primary_clinician_id)
