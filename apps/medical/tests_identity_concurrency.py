from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from unittest import skipUnless

from django.db import close_old_connections, connection, connections
from django.test import TransactionTestCase, override_settings

from apps.businesses.models import RolePermission
from apps.clients.models import Client
from apps.core.domain_errors import InvalidTransition
from .identity_correction_reads import list_identity_corrections
from .identity_iin_corrections import decide_iin_correction
from .identity_verification import verify_patient_identity
from .patient_selectors import read_patient_administration
from .patient_services import create_patient_profile
from .models import MedicalAuditEvent, PatientIdentityRevision, PatientProfile
from . import tests_identity_iin_corrections as corrections
from . import tests_patient_services as fixtures
from . import tests_patient_registration as registration


@skipUnless(connection.vendor == "postgresql", "Identity races require real PostgreSQL locks")
@override_settings(MEDICAL_DATA_KEYS={"test": fixtures.key(7)}, MEDICAL_DATA_ACTIVE_KEY_ID="test",
                   MEDICAL_IDENTITY_INDEX_KEY=fixtures.key(8))
class IdentityConcurrencyTests(TransactionTestCase):
    def setUp(self):
        corrections.IINCorrectionTests.setUpTestData.__func__(self)
        corrections.IINCorrectionTests.setUp(self)
        RolePermission.objects.create(business_role=self.assignment.business_role, resource="medical_patients",
                                      action="view", scope="business")

    def parallel(self, commands):
        barrier = Barrier(len(commands))

        def execute(command):
            close_old_connections()
            try:
                barrier.wait(timeout=10)
                try:
                    return command()
                except InvalidTransition:
                    return "conflict"
            finally:
                connections.close_all()

        with ThreadPoolExecutor(max_workers=len(commands)) as executor:
            futures = [executor.submit(execute, command) for command in commands]
            return [future.result(timeout=30) for future in futures]

    def test_same_iin_can_only_be_verified_once(self):
        third = Client.objects.create(business=self.business, full_name="Third synthetic identity")
        commands = []
        for client in (self.relative, third):
            patient, _ = create_patient_profile(actor=self.reception, business_id=self.business.pk,
                branch_id=self.branch.pk, client_id=client.pk, demographics={}, iin="000000000002",
                idempotency_key=f"race-create-{client.pk}")

            def verify(patient_id=patient.pk, client_version=client.updated_at):
                verify_patient_identity(actor=self.reception, business_id=self.business.pk, branch_id=self.branch.pk,
                    patient_id=patient_id, expected_revision=1, expected_client_updated_at=client_version,
                    protocol_reference="synthetic-v1", method="synthetic_document",
                    fields={"check_reference": "Synthetic race check"}, idempotency_key=f"race-verify-{patient_id}")
                return "verified"

            commands.append(verify)
        self.assertCountEqual(self.parallel(commands), ["verified", "conflict"])
        self.assertEqual(PatientProfile.objects.filter(business=self.business, identity_status="verified").count(), 2)

    def test_same_approval_replays_once(self):
        corrections.IINCorrectionTests.history(self)
        correction, _ = corrections.IINCorrectionTests.request(self)

        def decide():
            _, replayed = corrections.IINCorrectionTests.decide(self, correction)
            return replayed

        self.assertCountEqual(self.parallel([decide, decide]), [False, True])
        self.assertEqual(MedicalAuditEvent.objects.filter(identity_correction=correction, action="identity_correction_applied").count(), 1)
        self.assertEqual(PatientIdentityRevision.objects.filter(patient=self.patient, revision=2).count(), 1)

    def test_two_different_approvals_cannot_apply_to_same_source_revision(self):
        corrections.IINCorrectionTests.history(self)
        first, _ = corrections.IINCorrectionTests.request(self)
        second, _ = corrections.IINCorrectionTests.request(self, iin="000000000003", idempotency_key="second-proposal")

        def decide(correction):
            result, _ = decide_iin_correction(actor=self.head, business_id=self.business.pk, correction_id=correction.pk,
                approve=True, reason="Synthetic concurrent review", idempotency_key=f"decision-{correction.pk}")
            return result.state

        self.assertCountEqual(self.parallel([lambda: decide(first), lambda: decide(second)]), ["applied", "conflict"])
        self.patient.refresh_from_db()
        self.assertEqual(self.patient.revision, 3)

    def test_parallel_profile_and_correction_reads_both_persist_audit(self):
        corrections.IINCorrectionTests.history(self)
        correction, _ = corrections.IINCorrectionTests.request(self)
        scope = {"actor": self.reception, "business_id": self.business.pk, "branch_id": self.branch.pk,
                 "client_id": self.patient_client.pk}
        before = MedicalAuditEvent.objects.filter(patient=self.patient, action="read").count()
        results = self.parallel([lambda: read_patient_administration(**scope), lambda: list_identity_corrections(**scope)])
        self.assertEqual(results[0]["id"], self.patient.pk)
        self.assertEqual(results[1]["results"][0]["id"], correction.pk)
        self.assertEqual(MedicalAuditEvent.objects.filter(patient=self.patient, action="read").count() - before, 3)

    def test_registration_same_command_creates_one_client_and_profile(self):
        self.member.role = "admin"
        self.member.save(update_fields=["role"])

        def register():
            patient, replayed = registration.PatientRegistrationTests.register(self)
            return patient.pk, replayed

        results = self.parallel([register, register])
        self.assertEqual(results[0][0], results[1][0])
        self.assertCountEqual([result[1] for result in results], [False, True])
        self.assertEqual(Client.objects.filter(full_name="New synthetic person").count(), 1)
        self.assertEqual(PatientProfile.objects.filter(client__full_name="New synthetic person").count(), 1)
