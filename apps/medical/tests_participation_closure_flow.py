from unittest.mock import patch

from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from apps.businesses.models import RolePermission
from . import tests_participation_own_end as fixtures
from . import tests_encounter_completion_requirements as documents
from .audit import MedicalAuditUnavailable
from .participation_obligations import participation_obligations
from .tests_patient_services import key
from .tests_document_rules import default_rule


@override_settings(MEDICAL_DATA_KEYS={"test": key(7)}, MEDICAL_DATA_ACTIVE_KEY_ID="test", MEDICAL_IDENTITY_INDEX_KEY=key(8))
class ParticipationClosureFlowTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        fixtures.OwnParticipationEndTests.setUpTestData.__func__(cls)
        RolePermission.objects.create(business_role=cls.role, resource="medical_participation", action="view", scope="own")

    active = fixtures.OwnParticipationEndTests.active
    propose = fixtures.OwnParticipationEndTests.propose
    respond = fixtures.OwnParticipationEndTests.respond
    assign_booking = fixtures.OwnParticipationEndTests.assign_booking

    def setUp(self):
        self.item = self.active()
        self.api = APIClient(); self.api.force_authenticate(self.recipient)
        self.scope = {"business_id": self.business.pk, "patient_id": self.patient.pk}
        self.root = f"/api/medical/participations/{self.item.pk}/"

    def test_private_end_and_terminal_read_no_longer_exposes_obligations(self):
        read = self.api.get(self.root + "closure/", self.scope)
        self.assertEqual(read.status_code, 200, read.data)
        self.assertTrue(read.data["can_end"])
        self.assertEqual(read["Cache-Control"], "no-store, private")
        payload = self.scope | {"expected_revision": read.data["revision"]}
        for replayed in (False, True):
            result = self.api.post(self.root + "end-own/", payload, format="json", HTTP_IDEMPOTENCY_KEY="end")
            self.assertEqual(result.status_code, 200, result.data)
            self.assertEqual(result.data["replayed"], replayed)
        self.assertEqual(self.api.get(self.root + "closure/", self.scope).status_code, 409)

    def test_obligations_block_and_remain_intact(self):
        self.assign_booking()
        read = self.api.get(self.root + "closure/", self.scope)
        self.assertFalse(read.data["can_end"])
        self.assertEqual(read.data["obligations"]["appointments"]["ids"], [self.appointment.pk])
        result = self.api.post(self.root + "end-own/", self.scope | {"expected_revision": 2}, format="json", HTTP_IDEMPOTENCY_KEY="blocked")
        self.assertEqual(result.status_code, 409, result.data)
        self.item.refresh_from_db(); self.assertEqual(self.item.state, "active")

    def test_current_role_branch_owner_and_head_boundaries(self):
        self.api.force_authenticate(self.owner)
        self.assertEqual(self.api.get(self.root + "closure/", self.scope).status_code, 403)
        self.api.force_authenticate(self.doctor)
        self.assertFalse(self.api.get(self.root + "closure/", self.scope).data["own"])
        self.assertEqual(self.api.post(self.root + "end-own/", self.scope | {"expected_revision": 2}, format="json", HTTP_IDEMPOTENCY_KEY="other").status_code, 403)
        self.api.force_authenticate(self.recipient)
        self.target_role.branches.clear()
        self.assertEqual(self.api.get(self.root + "closure/", self.scope).status_code, 403)

    def test_strict_pagination_and_audit_failure(self):
        self.assertEqual(self.api.get(self.root + "closure/", self.scope | {"unknown": 1}).status_code, 400)
        self.assertEqual(self.api.get(self.root + "closure/", self.scope | {"limit": 51}).status_code, 400)
        self.assign_booking()
        result = self.api.get(self.root + "closure/", self.scope | {"limit": 1, "offset": 1})
        self.assertFalse(result.data["can_end"])
        self.assertEqual(result.data["obligations"]["appointments"], {"count": 1, "ids": []})
        with patch("apps.medical.participation_closure_reads.write_patient_audit", side_effect=MedicalAuditUnavailable()):
            self.assertEqual(self.api.get(self.root + "closure/", self.scope).status_code, 503)

    def test_head_mode_requires_manage_and_foreign_scope_is_rejected(self):
        self.assertEqual(self.api.get(self.root + "closure/", self.scope | {"as_head": True}).status_code, 403)
        self.api.force_authenticate(self.doctor)
        self.assertEqual(self.api.get(self.root + "closure/", self.scope | {"as_head": True}).status_code, 200)
        RolePermission.objects.filter(business_role=self.role, resource="medical_participation", action="manage").update(is_allowed=False)
        self.assertEqual(self.api.get(self.root + "closure/", self.scope | {"as_head": True}).status_code, 403)
        self.api.force_authenticate(self.recipient)
        self.assertIn(self.api.get(self.root + "closure/", self.scope | {"business_id": self.business.pk + 999}).status_code, (403, 404))


@override_settings(MEDICAL_DATA_KEYS={"test": key(7)}, MEDICAL_DATA_ACTIVE_KEY_ID="test", MEDICAL_IDENTITY_INDEX_KEY=key(8))
class ParticipationDocumentObligationsTests(TestCase):
    setUpTestData = classmethod(documents.EncounterCompletionRequirementsTests.setUpTestData.__func__)
    setUp = documents.EncounterCompletionRequirementsTests.setUp
    rules = documents.EncounterCompletionRequirementsTests.rules
    save = documents.EncounterCompletionRequirementsTests.save

    def remaining(self):
        return participation_obligations(business=self.business, patient=self.patient,
            member=self.encounter_record.primary_clinician)["documents"]

    def test_required_missing_and_current_draft_include_exact_source(self):
        self.rules()
        self.assertEqual(self.remaining()["items"][0]["blocker"], "document_missing")
        version = self.save()
        row = self.remaining()["items"][0]
        self.assertEqual((row["version_id"], row["encounter_id"], row["appointment_id"]),
            (version.pk, self.encounter_record.pk, self.appointment.pk))

    def test_before_issue_is_obligation_and_captured_rules_cannot_be_relaxed(self):
        rules = self.rules(content={"name": "Issue later", "services": [], "default": default_rule(required_at="before_issue", issuable=True)})
        self.save()
        self.rules(kind_id=rules.kind_id, expected_revision=1, idempotency_key="relax", content={"name": "Optional now", "services": [], "default": default_rule()})
        self.assertEqual(self.remaining()["count"], 1)

    def test_optional_document_does_not_become_mandatory_retroactively(self):
        rules = self.rules(content={"name": "Optional", "services": [], "default": default_rule()})
        self.save()
        self.rules(kind_id=rules.kind_id, expected_revision=1, idempotency_key="tighten")
        self.assertEqual(self.remaining()["count"], 0)
