import json
from unittest.mock import patch

from django.db import DatabaseError
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied, ValidationError

from apps.businesses.models import BusinessMember, RolePermission
from apps.core.domain_errors import IdempotencyConflict, InvalidTransition
from apps.core.models import CRMCommandIdempotency
from . import tests_participation_services as fixtures
from . import tests_patient_services as crypto_fixtures
from .audit import MedicalAuditUnavailable, write_patient_audit
from .identity_crypto import MedicalKeyUnavailable, decrypt_medical_value
from .models import MedicalAuditEvent, MedicalRoleAssignment, TreatmentParticipation
from .participation_access import assert_treatment_medical_basis
from .participation_closure import end_participation_by_head


@override_settings(MEDICAL_DATA_KEYS={"test": crypto_fixtures.key(7)}, MEDICAL_DATA_ACTIVE_KEY_ID="test",
                   MEDICAL_IDENTITY_INDEX_KEY=crypto_fixtures.key(8))
class ParticipationClosureTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        fixtures.ParticipationCommandTests.setUpTestData.__func__(cls)
        MedicalRoleAssignment.objects.filter(pk=cls.assignment.pk).update(kind="head")
        RolePermission.objects.create(business_role=cls.role, resource="medical_participation", action="manage", scope="business")

    propose = fixtures.ParticipationCommandTests.propose
    respond = fixtures.ParticipationCommandTests.respond

    def active(self):
        item, _ = self.propose()
        return self.respond(item)[0]

    def close(self, item, **overrides):
        return end_participation_by_head(**(dict(actor=self.doctor, business_id=self.business.pk,
            patient_id=self.patient.pk, participation_id=item.pk, expected_revision=2,
            responsible_member_id=self.member.pk, reason="Synthetic closure reason", idempotency_key="closure") | overrides))

    def test_closure_preserves_proposal_appointment_and_revokes_only_participation_basis(self):
        item = self.active()
        original_reason = item.reason_encrypted
        appointment = type(self.appointment).objects.values().get(pk=self.appointment.pk)
        closed, replayed = self.close(item)
        self.assertEqual((closed.state, closed.revision, closed.closed_by_id, closed.remaining_responsible_id, replayed),
                         ("ended", 3, self.doctor.pk, self.member.pk, False))
        self.assertEqual(closed.reason_encrypted, original_reason)
        self.assertEqual(type(self.appointment).objects.values().get(pk=self.appointment.pk), appointment)
        self.assertNotIn("Synthetic closure reason", closed.closure_reason_encrypted)
        payload = json.loads(decrypt_medical_value(closed.closure_reason_encrypted,
            business_id=self.business.pk, subject_id=item.pk, purpose="participation_closure"))
        self.assertEqual(payload, {"reason": "Synthetic closure reason", "revision": 3, "responsible_member_id": self.member.pk})
        with self.assertRaises(PermissionDenied):
            assert_treatment_medical_basis(actor=self.recipient, business=self.business, patient_id=self.patient.pk, participation_id=item.pk)
        self.assertTrue(self.close(item)[1])
        self.assertEqual(MedicalAuditEvent.objects.filter(action="participation_ended", participation_revision=3).count(), 1)
        command = CRMCommandIdempotency.objects.get(action="medical.participation.end_head")
        self.assertEqual(command.response_json, {})
        self.assertNotEqual(command.idempotency_key, "closure")

    def test_owner_recipient_and_doctor_do_not_inherit_head_power(self):
        item = self.active()
        for actor in (self.owner, self.recipient):
            with self.subTest(actor=actor.pk), self.assertRaises(PermissionDenied):
                self.close(item, actor=actor)
        MedicalRoleAssignment.objects.filter(pk=self.assignment.pk).update(kind="doctor")
        with self.assertRaises(PermissionDenied):
            self.close(item)

    def test_current_manage_branch_and_membership_required_including_replay(self):
        item = self.active()
        self.assignment.branches.clear()
        with self.assertRaises(PermissionDenied):
            self.close(item)
        self.assignment.branches.add(self.first)
        self.close(item)
        MedicalRoleAssignment.objects.filter(pk=self.assignment.pk).update(revoked_at=timezone.now())
        with self.assertRaises(PermissionDenied):
            self.close(item)

    def test_reason_responsible_and_stale_version_rejected_without_transition(self):
        item = self.active()
        for overrides in ({"reason": " "}, {"reason": "x" * 2001}, {"responsible_member_id": 999999}):
            with self.subTest(overrides=overrides), self.assertRaises(ValidationError):
                self.close(item, **overrides)
        BusinessMember.objects.filter(pk=self.target.pk).update(is_active=False)
        with self.assertRaises(ValidationError):
            self.close(item, responsible_member_id=self.target.pk)
        with self.assertRaises(InvalidTransition):
            self.close(item, expected_revision=1)
        item.refresh_from_db()
        self.assertEqual(item.state, "active")

    def test_inactive_departed_doctor_does_not_prevent_head_closure(self):
        item = self.active()
        BusinessMember.objects.filter(pk=self.target.pk).update(is_active=False)
        MedicalRoleAssignment.objects.filter(pk=self.target_role.pk).update(revoked_at=timezone.now())
        self.close(item)

    def test_pending_and_terminal_states_cannot_be_closed_with_new_command(self):
        item, _ = self.propose()
        with self.assertRaises(InvalidTransition):
            self.close(item, expected_revision=1)
        self.respond(item)
        self.close(item)
        with self.assertRaises(InvalidTransition):
            self.close(item, expected_revision=3, idempotency_key="second")
        with self.assertRaises(IdempotencyConflict):
            self.close(item, reason="Different reason")

    def test_audit_failure_rolls_back_closure_and_command(self):
        item = self.active()
        with patch("apps.medical.audit.MedicalAuditEvent.objects.create", side_effect=DatabaseError("synthetic")):
            with self.assertRaises(MedicalAuditUnavailable):
                self.close(item)
        item.refresh_from_db()
        self.assertEqual((item.state, item.revision, item.remaining_responsible_id, item.closure_reason_encrypted), ("active", 2, None, ""))
        self.assertFalse(CRMCommandIdempotency.objects.filter(action="medical.participation.end_head").exists())

    def test_cross_patient_and_corrupt_foreign_branch_denied(self):
        item = self.active()
        with self.assertRaises(PermissionDenied):
            self.close(item, participation_id=999999)
        from apps.businesses.models import Business
        from apps.branches.models import Branch
        foreign = Business.objects.create(owner=self.owner, name="Other", slug="closure-other")
        branch = Branch.objects.create(business=foreign, name="Other")
        TreatmentParticipation.objects.filter(pk=item.pk).update(branch=branch)
        with self.assertRaises(PermissionDenied):
            self.close(item)

    def test_foreign_responsible_and_other_patient_cannot_be_used(self):
        item = self.active()
        from apps.businesses.models import Business
        from apps.clients.models import Client
        from .models import PatientProfile
        foreign = Business.objects.create(owner=self.owner, name="Other", slug="responsible-other")
        member = BusinessMember.objects.create(business=foreign, user=self.owner, role="admin")
        with self.assertRaises(ValidationError):
            self.close(item, responsible_member_id=member.pk)
        client = Client.objects.create(business=self.business, full_name="Other patient")
        patient = PatientProfile.objects.create(business=self.business, client=client, created_by=self.owner)
        with self.assertRaises(PermissionDenied):
            self.close(item, patient_id=patient.pk)
        with self.assertRaises(PermissionDenied):
            self.close(item, business_id=foreign.pk)

    def test_missing_keys_do_not_leave_closure_or_command(self):
        item = self.active()
        with override_settings(MEDICAL_DATA_KEYS={}):
            with self.assertRaises(MedicalKeyUnavailable):
                self.close(item)
        item.refresh_from_db()
        self.assertEqual((item.state, item.revision, item.closure_reason_encrypted), ("active", 2, ""))
        self.assertFalse(CRMCommandIdempotency.objects.filter(action="medical.participation.end_head").exists())

    def test_end_audit_rejects_active_wrong_actor_and_stale_snapshot(self):
        item = self.active()
        def audit(actor=None):
            return write_patient_audit(actor=actor or self.doctor, business=self.business, patient=self.patient,
                action="participation_ended", participation=item)
        with self.assertRaises(ValueError):
            audit()
        closed, _ = self.close(item)
        with self.assertRaises(ValueError):
            audit()
        item = closed
        with self.assertRaises(ValueError):
            audit(self.recipient)

    def test_no_manage_permission_blocks_current_command(self):
        item = self.active()
        RolePermission.objects.filter(business_role=self.role, resource="medical_participation", action="manage").update(is_allowed=False)
        with self.assertRaises(PermissionDenied):
            self.close(item)
