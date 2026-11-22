from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.db import transaction
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied

from apps.branches.models import BranchAccess
from apps.businesses.models import BusinessCapability, BusinessMember, BusinessRole
from apps.core.domain_errors import ModuleDisabled
from apps.core.models import AuditLog, CRMCommandIdempotency
from . import tests_correction_access as correction_fixtures
from . import tests_encounter_services as encounter_fixtures
from . import tests_patient_services as crypto_fixtures
from .correction_access_reads import read_correction_target
from .correction_access_services import close_correction_access
from .encounter_reads import read_encounter_for_treating_clinician
from .encounter_services import save_primary_encounter_draft
from .models import MedicalAuditEvent, MedicalEncounterRevision, MedicalRoleAssignment, TreatmentParticipation
from .role_services import revoke_medical_role


@override_settings(MEDICAL_DATA_KEYS={"test": crypto_fixtures.key(7)}, MEDICAL_DATA_ACTIVE_KEY_ID="test",
                   MEDICAL_IDENTITY_INDEX_KEY=crypto_fixtures.key(8))
class AccessBasisCombinationTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        correction_fixtures.CorrectionAccessTests.setUpTestData.__func__(cls)

    def setUp(self):
        encounter_fixtures.PrimaryEncounterDraftTests.setUp(self)
        now = timezone.now()
        self.participation = TreatmentParticipation.objects.create(patient=self.patient, member=self.member,
            branch=self.first, proposed_by=self.head, state="active", proposed_at=now, accepted_at=now)
        requested = correction_fixtures.CorrectionAccessTests.request(self)[0]
        self.correction = correction_fixtures.CorrectionAccessTests.review(self, requested)[0]

    def read(self, basis):
        if basis == "correction":
            return read_correction_target(actor=self.doctor, business_id=self.business.pk,
                                          request_id=self.correction.pk)
        return read_encounter_for_treating_clinician(actor=self.doctor, business_id=self.business.pk,
            patient_id=self.patient.pk, version_id=self.first_version.pk,
            **({"appointment_id": self.appointment.pk} if basis == "appointment"
               else {"participation_id": self.participation.pk}))

    def save(self, basis, revision=1):
        return save_primary_encounter_draft(actor=self.doctor, business_id=self.business.pk,
            patient_id=self.patient.pk, encounter_id=self.encounter_record.pk, expected_revision=revision,
            content={"plan": "Synthetic combination draft"}, reason="Synthetic correction",
            idempotency_key="combination-" + basis,
            **({"correction_access_id": self.correction.pk} if basis == "correction" else
               {"participation_id": self.participation.pk} if basis == "participation" else {}))

    def end_participation(self):
        TreatmentParticipation.objects.filter(pk=self.participation.pk).update(
            state="ended", closed_at=timezone.now(), closed_by=self.head)

    def close_correction(self):
        close_correction_access(actor=self.head, business_id=self.business.pk, request_id=self.correction.pk,
            expected_revision=2, decision="revoke", reason="Synthetic revoke", idempotency_key="revoke")

    def test_completed_booking_preserves_participation_and_correction(self):
        type(self.appointment).objects.filter(pk=self.appointment.pk).update(status="completed")
        with self.assertRaises(PermissionDenied):
            self.read("appointment")
        self.read("participation")
        self.read("correction")
        self.save("participation")
        self.end_participation()
        with self.assertRaises(PermissionDenied):
            self.read("participation")
        with self.assertRaises(PermissionDenied):
            self.save("participation")
        self.read("correction")
        self.save("correction", revision=2)

    def test_ended_participation_does_not_cancel_booking_or_correction(self):
        self.end_participation()
        with self.assertRaises(PermissionDenied):
            self.read("participation")
        self.read("appointment")
        self.read("correction")
        self.save("appointment")
        self.close_correction()
        with self.assertRaises(PermissionDenied):
            self.read("correction")
        self.read("appointment")
        self.assertTrue(self.save("appointment")[1])

    def test_expired_correction_does_not_cancel_independent_participation(self):
        type(self.appointment).objects.filter(pk=self.appointment.pk).update(status="cancelled")
        with patch("apps.medical.correction_access_context.timezone.now", return_value=self.correction.expires_at):
            with self.assertRaises(PermissionDenied):
                self.read("correction")
            self.read("participation")
            self.save("participation")

    def test_no_remaining_basis_cannot_read_or_replay_and_preserves_history(self):
        self.save("appointment")
        self.save("participation", revision=2)
        self.save("correction", revision=3)
        type(self.appointment).objects.filter(pk=self.appointment.pk).update(status="cancelled")
        self.end_participation()
        self.close_correction()
        before = list(MedicalEncounterRevision.objects.values())
        commands = CRMCommandIdempotency.objects.count()
        for revision, basis in enumerate(("appointment", "participation", "correction"), start=1):
            with self.subTest(basis=basis):
                with self.assertRaises(PermissionDenied):
                    self.read(basis)
                with self.assertRaises(PermissionDenied):
                    self.save(basis, revision)
        self.assertEqual(list(MedicalEncounterRevision.objects.values()), before)
        self.assertEqual(CRMCommandIdempotency.objects.count(), commands)

    def test_security_revocation_overrides_all_live_bases_and_saved_command_replay(self):
        bases = ("appointment", "participation", "correction")
        for revision, basis in enumerate(bases, start=1):
            self.read(basis)
            self.save(basis, revision)
        mutations = {
            "account": lambda: get_user_model().objects.filter(pk=self.doctor.pk).update(is_active=False),
            "membership": lambda: BusinessMember.objects.filter(pk=self.member.pk).update(is_active=False),
            "medical_role": lambda: MedicalRoleAssignment.objects.filter(pk=self.assignment.pk).update(revoked_at=timezone.now()),
            "role_definition": lambda: BusinessRole.objects.filter(pk=self.role.pk).update(is_active=False),
            "medical_branch": lambda: self.assignment.branches.clear(),
            "crm_branch": lambda: BranchAccess.objects.filter(pk=self.crm_grant.pk).update(all_branches=False),
            "module": lambda: BusinessCapability.objects.filter(business=self.business, module_key="medical_records").update(is_enabled=False),
        }
        for name, mutate in mutations.items():
            with self.subTest(revocation=name), transaction.atomic():
                mutate()
                before = list(MedicalEncounterRevision.objects.values())
                audits = MedicalAuditEvent.objects.count()
                commands = CRMCommandIdempotency.objects.count()
                for revision, basis in enumerate(bases, start=1):
                    with self.subTest(basis=basis):
                        with self.assertRaises((PermissionDenied, ModuleDisabled)):
                            self.read(basis)
                        with self.assertRaises((PermissionDenied, ModuleDisabled)):
                            self.save(basis, revision)
                self.assertEqual(list(MedicalEncounterRevision.objects.values()), before)
                self.assertEqual(MedicalAuditEvent.objects.count(), audits)
                self.assertEqual(CRMCommandIdempotency.objects.count(), commands)
                transaction.set_rollback(True)

    def test_owner_role_revocation_is_not_blocked_by_draft_or_active_treatment(self):
        before = list(MedicalEncounterRevision.objects.values())
        kwargs = dict(actor=self.owner, business_id=self.business.pk, member_id=self.member.pk,
            expected_revision=self.assignment.revision, idempotency_key="security-revoke",
            reason="Synthetic security incident")
        revoked, replayed = revoke_medical_role(**kwargs)
        self.assertFalse(replayed)
        self.assertIsNotNone(revoked.revoked_at)
        self.assertTrue(revoke_medical_role(**kwargs)[1])
        self.assertEqual(AuditLog.objects.filter(metadata__kind="medical_role_revoked").count(), 1)
        for basis in ("appointment", "participation", "correction"):
            with self.subTest(basis=basis), self.assertRaises(PermissionDenied):
                self.read(basis)
        self.appointment.refresh_from_db()
        self.participation.refresh_from_db()
        self.correction.refresh_from_db()
        self.encounter_record.refresh_from_db()
        self.assertEqual((self.appointment.status, self.participation.state, self.correction.state,
                          self.encounter_record.state), ("created", "active", "active", "draft"))
        self.assertEqual(list(MedicalEncounterRevision.objects.values()), before)
