from unittest.mock import patch

from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.test import APIClient

from apps.branches.models import Branch, BranchAccess
from apps.businesses.models import Business, RolePermission
from apps.core.domain_errors import InvalidTransition
from apps.core.models import AuditLog
from . import tests_reception_claims as fixtures
from .reception_claims import claim_reception_request
from .reception_transfer import transfer_reception_request
from .tests_patient_services import key


@override_settings(MEDICAL_DATA_KEYS={"test": key(7)}, MEDICAL_DATA_ACTIVE_KEY_ID="test",
                   MEDICAL_IDENTITY_INDEX_KEY=key(8))
class ReceptionTransferTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        fixtures.ReceptionClaimTests.setUpTestData.__func__(cls)

    request = fixtures.ReceptionClaimTests.request
    claim = fixtures.ReceptionClaimTests.claim

    def setUp(self):
        self.item, _ = self.request()
        self.claim()
        self.item.refresh_from_db()

    def transfer(self, **changes):
        return transfer_reception_request(**({"actor": self.reception, "business_id": self.business.pk,
            "request_id": self.item.pk, "expected_revision": 2, "assignee_id": self.colleague_member.pk,
            "reason": "Synthetic shift handover", "idempotency_key": "transfer"} | changes))

    def test_transfer_replay_preserves_deadline_and_single_history(self):
        deadline = self.item.acceptance_due_at
        item, replayed = self.transfer()
        same, repeated = self.transfer()
        self.assertFalse(replayed)
        self.assertTrue(repeated)
        self.assertEqual((same.pk, same.assignee_id, same.revision, same.state),
            (item.pk, self.colleague_member.pk, 3, "pending"))
        self.assertEqual(same.acceptance_due_at, deadline)
        events = AuditLog.objects.filter(entity_type="ReceptionBookingRequest", metadata__kind="medical_follow_up_transferred")
        self.assertEqual(events.count(), 1)
        self.assertEqual(events.get().metadata["from_member_id"], self.reception_member.pk)
        self.assertEqual(events.get().metadata["to_member_id"], self.colleague_member.pk)
        with self.assertRaises(PermissionDenied):
            self.transfer(expected_revision=3, idempotency_key="old-assignee")

    def test_release_and_colleague_claim_keep_original_deadline(self):
        item, _ = self.transfer(assignee_id=None)
        self.assertEqual(item.state, "new")
        self.assertIsNone(item.assignee_id)
        self.assertIsNone(item.claimed_at)
        claimed, _ = claim_reception_request(actor=self.colleague, business_id=self.business.pk,
            request_id=item.pk, expected_revision=3, idempotency_key="new-shift-claim")
        self.assertEqual(claimed.assignee_id, self.colleague_member.pk)
        self.assertEqual(claimed.acceptance_due_at, self.item.acceptance_due_at)

    def test_only_current_assignee_and_same_business_recipient(self):
        for actor in (self.owner, self.doctor, self.colleague):
            with self.subTest(actor=actor.pk), self.assertRaises(PermissionDenied):
                self.transfer(actor=actor)
        other = Business.objects.create(owner=self.owner, name="Synthetic transfer other", slug="transfer-other")
        with self.assertRaises(PermissionDenied):
            self.transfer(business_id=other.pk)
        with self.assertRaises(PermissionDenied):
            self.transfer(assignee_id=self.member.pk)
        other_branch = Branch.objects.create(business=other, name="Synthetic foreign branch")
        _, foreign_member, _ = fixtures.reception_member(other, self.owner, other_branch, "foreign-transfer")
        with self.assertRaises(PermissionDenied):
            self.transfer(assignee_id=foreign_member.pk)

    def test_target_must_have_active_role_branch_and_client_access(self):
        self.colleague_assignment.branches.clear()
        with self.assertRaises(PermissionDenied):
            self.transfer()
        self.colleague_assignment.branches.add(self.first)
        BranchAccess.objects.filter(member=self.colleague_member).update(all_branches=False)
        with self.assertRaises(PermissionDenied):
            self.transfer()
        BranchAccess.objects.filter(member=self.colleague_member).update(all_branches=True)
        RolePermission.objects.filter(business_role=self.colleague_member.business_role,
            resource="clients", action="view").update(scope="own")
        with self.assertRaises(PermissionDenied):
            self.transfer()
        RolePermission.objects.filter(business_role=self.colleague_member.business_role,
            resource="clients", action="view").update(scope="business")
        self.colleague_assignment.revoked_at = timezone.now()
        self.colleague_assignment.save(update_fields=["revoked_at"])
        with self.assertRaises(PermissionDenied):
            self.transfer()

    def test_replay_rechecks_actor_access(self):
        self.transfer()
        self.reception_assignment.revoked_at = timezone.now()
        self.reception_assignment.save(update_fields=["revoked_at"])
        with self.assertRaises(PermissionDenied):
            self.transfer()

    def test_disabled_target_and_closed_request_are_denied(self):
        self.colleague.is_active = False
        self.colleague.save(update_fields=["is_active"])
        with self.assertRaises(PermissionDenied):
            self.transfer()
        self.colleague.is_active = True
        self.colleague.save(update_fields=["is_active"])
        self.colleague_member.is_active = False
        self.colleague_member.save(update_fields=["is_active"])
        with self.assertRaises(PermissionDenied):
            self.transfer()
        self.item.state, self.item.closed_at, self.item.closure_reason = "cancelled", timezone.now(), "Synthetic closure"
        self.item.full_clean()
        self.item.save()
        with self.assertRaises(InvalidTransition):
            self.transfer(assignee_id=None)

    def test_stale_invalid_and_audit_failure_leave_assignment_unchanged(self):
        for changes in ({"reason": " "}, {"reason": "x" * 1001}, {"assignee_id": True},
                        {"assignee_id": self.reception_member.pk}, {"expected_revision": True}):
            with self.subTest(changes=changes), self.assertRaises(ValidationError):
                self.transfer(**changes)
        with self.assertRaises(InvalidTransition):
            self.transfer(expected_revision=1)
        with patch("apps.medical.reception_transfer.write_actor_audit_log", side_effect=RuntimeError("synthetic")):
            with self.assertRaises(RuntimeError):
                self.transfer()
        self.item.refresh_from_db()
        self.assertEqual((self.item.assignee_id, self.item.revision), (self.reception_member.pk, 2))
        self.assertFalse(self.transfer()[1])


@override_settings(MEDICAL_DATA_KEYS={"test": key(7)}, MEDICAL_DATA_ACTIVE_KEY_ID="test",
                   MEDICAL_IDENTITY_INDEX_KEY=key(8))
class ReceptionTransferAPITests(TestCase):
    @classmethod
    def setUpTestData(cls):
        fixtures.ReceptionClaimTests.setUpTestData.__func__(cls)

    request = ReceptionTransferTests.request
    claim = ReceptionTransferTests.claim

    def setUp(self):
        ReceptionTransferTests.setUp(self)
        self.api = APIClient()
        self.api.force_authenticate(self.reception)
        self.url = f"/api/reception/booking-requests/{self.item.pk}/transfer/"
        self.payload = {"business_id": self.business.pk, "expected_revision": 2,
            "assignee_id": self.colleague_member.pk, "reason": "Synthetic HTTP handover"}

    def test_transfer_http_and_private_replay(self):
        for replayed in (False, True):
            response = self.api.post(self.url, self.payload, format="json", HTTP_IDEMPOTENCY_KEY="http-transfer")
            self.assertEqual(response.status_code, 200, response.data)
            self.assertEqual(response.data, {"id": self.item.pk, "state": "pending", "revision": 3, "replayed": replayed})
            self.assertEqual(response["Cache-Control"], "no-store, private")
        self.api.force_authenticate(self.colleague)
        response = self.api.post(self.url, self.payload | {"expected_revision": 3, "assignee_id": None},
            format="json", HTTP_IDEMPOTENCY_KEY="http-release")
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data["state"], "new")

    def test_strict_payload_stale_and_denied_responses(self):
        for payload in (self.payload | {"clinical_text": "forbidden"}, self.payload | {"reason": " "},
                        {key: value for key, value in self.payload.items() if key != "assignee_id"}):
            response = self.api.post(self.url, payload, format="json", HTTP_IDEMPOTENCY_KEY="invalid")
            self.assertEqual(response.status_code, 400, response.data)
        stale = self.api.post(self.url, self.payload | {"expected_revision": 1}, format="json", HTTP_IDEMPOTENCY_KEY="stale")
        self.assertEqual(stale.status_code, 409, stale.data)
        for actor in (self.doctor, self.owner, self.colleague, None):
            self.api.force_authenticate(actor)
            response = self.api.post(self.url, self.payload, format="json", HTTP_IDEMPOTENCY_KEY="denied")
            self.assertEqual(response.status_code, 401 if actor is None else 403, response.data)
            self.assertEqual(response["Cache-Control"], "no-store, private")
        self.item.refresh_from_db()
        self.assertEqual((self.item.assignee_id, self.item.revision), (self.reception_member.pk, 2))
