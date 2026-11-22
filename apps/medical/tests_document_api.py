from unittest.mock import patch

from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from apps.businesses.models import Business
from . import tests_document_template_source as fixtures
from . import tests_patient_services as crypto_fixtures
from .audit import MedicalAuditUnavailable
from .models import MedicalDocumentRevision


@override_settings(MEDICAL_DATA_KEYS={"test": crypto_fixtures.key(7)}, MEDICAL_DATA_ACTIVE_KEY_ID="test",
                   MEDICAL_IDENTITY_INDEX_KEY=crypto_fixtures.key(8))
class DocumentAPITests(TestCase):
    @classmethod
    def setUpTestData(cls):
        fixtures.DocumentTemplateSourceTests.setUpTestData.__func__(cls)

    def setUp(self):
        fixtures.DocumentTemplateSourceTests.setUp(self)
        fixtures.DocumentTemplateSourceTests.approve(self)
        self.api = APIClient()
        self.api.force_authenticate(self.doctor)
        self.root = "/api/medical/documents/"
        self.scope = dict(business_id=self.business.pk, patient_id=self.patient.pk, appointment_id=self.appointment.pk)
        self.payload = dict(business_id=self.business.pk, patient_id=self.patient.pk,
            encounter_id=self.encounter_record.pk, expected_encounter_revision=1,
            expected_patient_revision=self.patient.revision, template_version_id=self.template.pk,
            document_text=" Literal {{patient}} <script>\n synthetic text ")

    def private(self, response):
        self.assertEqual(response["Cache-Control"], "no-store, private")
        self.assertEqual(response["Pragma"], "no-cache")
        return response

    def command(self, path="", payload=None, key="document"):
        return self.private(self.api.post(self.root + path, self.payload if payload is None else payload,
            format="json", HTTP_IDEMPOTENCY_KEY=key))

    def read(self, path="", **overrides):
        return self.private(self.api.get(self.root + path, self.scope | overrides))

    def test_create_update_list_history_and_exact_read(self):
        created = self.command()
        self.assertEqual(created.status_code, 201, created.data)
        self.assertTrue(self.command().data["replayed"])
        first = created.data
        response = self.read(f"versions/{first['version_id']}/")
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data["snapshot"]["document_text"], self.payload["document_text"])
        self.assertEqual(response.data["snapshot"]["template_source"]["version_id"], self.template.pk)
        updated = self.command(f"{first['id']}/draft/", self.payload | dict(expected_document_revision=1,
            document_text="Updated synthetic text"), "update")
        self.assertEqual(updated.status_code, 200, updated.data)
        self.assertEqual(updated.data["revision"], 2)
        self.assertEqual(self.read().data["results"][0]["version_id"], updated.data["version_id"])
        history = self.read(f"{first['id']}/revisions/", limit=1)
        self.assertEqual(history.data["next_before_revision"], 2)
        self.assertEqual(self.read(f"{first['id']}/revisions/", before_revision=2).data["results"][0]["version_id"], first["version_id"])
        self.assertEqual(self.read(f"versions/{first['version_id']}/").data["snapshot"]["document_text"], self.payload["document_text"])

    def test_strict_fields_no_raw_template_or_client_approval(self):
        for field in ("template", "template_source", "approved_by", "state", "author_id"):
            response = self.command(payload=self.payload | {field: "forged"})
            self.assertEqual(response.status_code, 400)
        payload = dict(self.payload)
        del payload["template_version_id"]
        self.assertEqual(self.command(payload=payload).status_code, 400)
        self.assertEqual(self.command(key="").status_code, 400)
        self.assertFalse(MedicalDocumentRevision.objects.exists())
        for query in ({"limit": 51}, {"before_id": 0}, {"unexpected": "field"}, {"participation_id": 1}):
            self.assertEqual(self.read(**query).status_code, 400)

    def test_stale_and_conflicting_commands_and_audit_rollback(self):
        with patch("apps.medical.document_services.write_patient_audit", side_effect=MedicalAuditUnavailable):
            self.assertEqual(self.command().status_code, 503)
        self.assertFalse(MedicalDocumentRevision.objects.exists())
        first = self.command().data
        self.assertEqual(self.command(payload=self.payload | {"document_text": "Changed"}).status_code, 409)
        self.assertEqual(self.command(f"{first['id']}/draft/", self.payload | {"expected_document_revision": 9}, "stale").status_code, 409)
        self.assertEqual(MedicalDocumentRevision.objects.count(), 1)
        with patch("apps.medical.document_services.write_patient_audit", side_effect=MedicalAuditUnavailable):
            self.assertEqual(self.read().status_code, 503)

    def test_owner_tenant_and_revoked_access_denied(self):
        first = self.command().data
        other = Business.objects.create(owner=self.owner, name="Other", slug="document-api-other")
        self.assertEqual(self.read(business_id=other.pk).status_code, 403)
        self.api.force_authenticate(self.owner)
        self.assertEqual(self.command().status_code, 403)
        for path in ("", f"{first['id']}/revisions/", f"versions/{first['version_id']}/"):
            self.assertEqual(self.read(path).status_code, 403)
        self.api.force_authenticate(self.doctor)
        self.assignment.branches.clear()
        self.assertEqual(self.command().status_code, 403)
        self.assertEqual(self.read().status_code, 403)
        self.api.force_authenticate(None)
        self.assertIn(self.read().status_code, (401, 403))

    def test_other_patient_documents_are_absent_and_exact_routes_deny(self):
        from apps.clients.models import Client
        from apps.scheduling.models import Appointment
        from .document_content import append_document_revision
        from .encounter_content import append_encounter_revision
        from .models import DentalMedicalRecord, MedicalDocument, MedicalEncounter, PatientProfile
        self.assertEqual(self.command().status_code, 201)
        client = Client.objects.create(business=self.business, full_name="Other synthetic patient")
        patient = PatientProfile.objects.create(business=self.business, client=client, created_by=self.owner)
        record = DentalMedicalRecord.objects.create(business=self.business, patient=patient,
            number="API-OTHER", opened_by=self.doctor)
        appointment = Appointment.objects.create(business=self.business, client=client, branch=self.first,
            service=self.service, resource=self.staff, start_at=self.appointment.start_at, end_at=self.appointment.end_at)
        encounter = MedicalEncounter.objects.create(business=self.business, patient=patient, record=record,
            appointment=appointment, branch=self.first, primary_clinician=self.member)
        source = append_encounter_revision(encounter=encounter, author=self.doctor, content={"plan": "Other secret"})
        document = MedicalDocument.objects.create(business=self.business, encounter=encounter, template_code="other")
        version = append_document_revision(document=document, source_version=source, author=self.doctor,
            template={"code": "other", "version": 1, "title": "Other secret", "text": "Other"})
        response = self.read()
        self.assertEqual(len(response.data["results"]), 1)
        self.assertNotIn("Other secret", str(response.data))
        self.assertEqual(self.read(f"versions/{version.pk}/").status_code, 403)
        self.assertEqual(self.read(f"{document.pk}/revisions/").status_code, 403)
        self.assertEqual(self.read(encounter_id=encounter.pk).status_code, 403)
