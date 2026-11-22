from unittest.mock import patch

from django.db import DatabaseError
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from . import tests_participation_closure as fixtures
from .tests_patient_services import key
from .models import MedicalAuditEvent, MedicalRoleAssignment, TreatmentParticipation


@override_settings(MEDICAL_DATA_KEYS={"test": key(7)}, MEDICAL_DATA_ACTIVE_KEY_ID="test",
                   MEDICAL_IDENTITY_INDEX_KEY=key(8))
class ParticipationAPITests(TestCase):
    @classmethod
    def setUpTestData(cls):
        fixtures.ParticipationClosureTests.setUpTestData.__func__(cls)

    def setUp(self):
        self.api = APIClient()
        self.api.force_authenticate(self.doctor)
        self.url = "/api/medical/participations/"
        self.scope = {"business_id": self.business.pk, "patient_id": self.patient.pk}
        self.proposal = {**self.scope, "branch_id": self.first.pk, "target_member_id": self.target.pk,
            "expected_patient_revision": 1, "reason": "  Synthetic private proposal\n"}

    def post(self, path="", data=None, token="proposal"):
        return self.api.post(self.url + path, data if data is not None else self.proposal,
            format="json", HTTP_IDEMPOTENCY_KEY=token)

    def private(self, response, status):
        self.assertEqual(response.status_code, status, response.data)
        self.assertEqual(response["Cache-Control"], "no-store, private")
        self.assertEqual(response["Pragma"], "no-cache")

    def active(self):
        created = self.post()
        self.private(created, 201)
        self.api.force_authenticate(self.recipient)
        response = self.post(f"{created.data['id']}/respond/", {**self.scope, "expected_revision": 1, "decision": "accept"}, "accept")
        self.private(response, 200)
        self.api.force_authenticate(self.doctor)
        return created.data["id"]

    def ending(self, identifier, **overrides):
        return self.post(f"{identifier}/end-by-head/", {**self.scope, "expected_revision": 2,
            "responsible_member_id": self.member.pk, "reason": "  Synthetic closure\n", **overrides}, "end")

    def test_propose_accept_end_and_replay_return_only_command_metadata(self):
        identifier = self.active()
        replay = self.post()
        self.private(replay, 200)
        self.assertTrue(replay.data["replayed"])
        response = self.ending(identifier)
        self.private(response, 200)
        self.assertEqual(response.data, {"id": identifier, "state": "ended", "revision": 3, "replayed": False})
        self.assertTrue(self.ending(identifier).data["replayed"])
        item = TreatmentParticipation.objects.get(pk=identifier)
        self.assertNotIn("Synthetic closure", item.closure_reason_encrypted)
        self.assertEqual(MedicalAuditEvent.objects.filter(action="participation_ended").count(), 1)

    def test_decline_is_recipient_only_and_withdraw_is_a_separate_pending_action(self):
        identifier = self.post().data["id"]
        body = {**self.scope, "expected_revision": 1, "decision": "decline"}
        self.private(self.post(f"{identifier}/respond/", body, "decline"), 403)
        self.api.force_authenticate(self.recipient)
        self.private(self.post(f"{identifier}/respond/", body, "decline"), 200)
        self.api.force_authenticate(self.doctor)
        second = self.post(token="next-proposal")
        self.private(second, 201)
        identifier = second.data["id"]
        response = self.post(f"{identifier}/withdraw/", {**self.scope, "expected_revision": 1}, "withdraw")
        self.private(response, 200)
        self.assertEqual(response.data["state"], "withdrawn")

    def test_strict_fields_missing_key_and_invalid_commands(self):
        for extra in ({"actor_id": self.owner.pk}, {"state": "active"}, {"branch_id": 0},
                      {"source_appointment_id": self.appointment.pk, "source_participation_id": 123}):
            self.private(self.post(data=self.proposal | extra), 400)
        self.private(self.api.post(self.url, self.proposal, format="json"), 400)
        self.private(self.post(token="x" * 129), 400)
        self.assertFalse(TreatmentParticipation.objects.exists())
        identifier = self.active()
        for extra in ({"reason": " "}, {"responsible_member_id": 0}, {"closed_by": self.doctor.pk}):
            self.private(self.ending(identifier, **extra), 400)

    def test_stale_revision_and_changed_replay_payload_conflict(self):
        identifier = self.active()
        self.private(self.ending(identifier, expected_revision=1), 409)
        self.private(self.ending(identifier), 200)
        self.private(self.ending(identifier, reason="Different"), 409)

    def test_anonymous_owner_recipient_and_revoked_head_denied(self):
        identifier = self.active()
        for actor, status in ((None, 401), (self.owner, 403), (self.recipient, 403)):
            self.api.force_authenticate(actor)
            self.private(self.ending(identifier), status)
        self.api.force_authenticate(self.doctor)
        self.private(self.ending(identifier), 200)
        MedicalRoleAssignment.objects.filter(pk=self.assignment.pk).update(revoked_at=timezone.now())
        self.private(self.ending(identifier), 403)

    def test_branch_and_business_boundaries(self):
        identifier = self.active()
        self.assignment.branches.clear()
        self.private(self.ending(identifier), 403)
        self.assignment.branches.add(self.first)
        from apps.businesses.models import Business
        foreign = Business.objects.create(owner=self.owner, name="Other", slug="participation-api-other")
        self.private(self.ending(identifier, business_id=foreign.pk), 403)
        self.private(self.ending(999999), 403)

    def test_audit_failure_is_private_and_retry_does_not_duplicate_transition(self):
        identifier = self.active()
        with patch("apps.medical.audit.MedicalAuditEvent.objects.create", side_effect=DatabaseError("synthetic")):
            self.private(self.ending(identifier), 503)
        self.assertEqual(TreatmentParticipation.objects.get(pk=identifier).state, "active")
        self.private(self.ending(identifier), 200)
        self.assertEqual(MedicalAuditEvent.objects.filter(action="participation_ended").count(), 1)

    def test_generic_read_and_patch_do_not_expose_or_modify_participation(self):
        identifier = self.active()
        self.private(self.api.get(self.url, self.scope), 405)
        self.private(self.api.patch(f"{self.url}{identifier}/respond/", {"state": "ended"}, format="json"), 405)
        self.assertEqual(TreatmentParticipation.objects.get(pk=identifier).state, "active")
