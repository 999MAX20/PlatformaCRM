from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.db.models.deletion import ProtectedError
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from apps.businesses.models import Business
from apps.clients.models import Client, ClientMergeLog
from apps.clients.services import merge_clients, merge_clients_dry_run
from apps.core.domain_errors import InvalidTransition
from apps.scheduling.models import VisitPlan
from .models import PatientProfile


class PatientProfileSchemaTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.owner = get_user_model().objects.create_user(username="medical-schema", email="schema@example.test")
        cls.business = Business.objects.create(owner=cls.owner, name="Synthetic clinic", slug="medical-schema")
        cls.other = Business.objects.create(owner=cls.owner, name="Other", slug="medical-schema-other")
        cls.patient_client = Client.objects.create(business=cls.business, full_name="Synthetic patient", phone="+77000000001")
        cls.duplicate = Client.objects.create(business=cls.business, full_name="Synthetic relative", phone="+77000000001")
        cls.foreign = Client.objects.create(business=cls.other, full_name="Foreign synthetic patient")

    def profile(self, client=None, **values):
        client = client or self.patient_client
        return PatientProfile.objects.create(client=client, business_id=client.business_id,
                                             created_by=self.owner, **values)

    def verified_values(self):
        return {"identity_status": "verified", "verified_at": timezone.now(), "verified_by": self.owner,
                "verification_evidence_encrypted": "synthetic-encrypted-evidence"}

    def test_existing_client_one_profile_and_shared_phone_does_not_merge_people(self):
        patient = self.profile()
        relative = self.profile(self.duplicate)
        self.assertNotEqual(patient.pk, relative.pk)
        self.assertEqual(Client.objects.filter(business=self.business).count(), 2)
        with self.assertRaises(IntegrityError), transaction.atomic():
            self.profile()

    def test_cross_business_client_is_rejected_by_model_validation(self):
        patient = PatientProfile(business=self.business, client=self.foreign, created_by=self.owner)
        with self.assertRaisesMessage(ValidationError, "Select a client of this business"):
            patient.full_clean()

    def test_verified_digest_is_unique_inside_business_but_not_across_tenants(self):
        values = {**self.verified_values(), "iin_encrypted": "synthetic-ciphertext", "iin_digest": "a" * 64}
        self.profile(**values)
        with self.assertRaises(IntegrityError), transaction.atomic():
            self.profile(self.duplicate, **values)
        self.profile(self.foreign, **values)
        self.assertEqual(PatientProfile.objects.count(), 2)

    def test_unverified_duplicate_cannot_be_promoted_over_verified_identity(self):
        identity = {"iin_encrypted": "synthetic-ciphertext", "iin_digest": "a" * 64}
        self.profile(**identity, **self.verified_values())
        unverified = self.profile(self.duplicate, **identity)
        with self.assertRaises(IntegrityError), transaction.atomic():
            PatientProfile.objects.filter(pk=unverified.pk).update(**self.verified_values())
        unverified.refresh_from_db()
        self.assertEqual(unverified.identity_status, "unverified")

    def test_alternative_identity_does_not_require_fictitious_iin(self):
        first = self.profile(**self.verified_values())
        second = self.profile(self.duplicate, **self.verified_values())
        self.assertIsNone(first.iin_digest)
        self.assertIsNone(second.iin_digest)

    def test_database_rejects_incomplete_or_unknown_identity_state(self):
        for values in ({"identity_status": "verified"}, {"identity_status": "unknown"},
                       {"verified_at": timezone.now()}, {"verified_by": self.owner},
                       {"identity_status": "verified", "verified_at": timezone.now(), "verified_by": self.owner},
                       {"iin_digest": "a" * 64}, {"iin_encrypted": "synthetic-ciphertext"}, {"revision": 0}):
            with self.subTest(values=values), self.assertRaises(IntegrityError), transaction.atomic():
                self.profile(**values)

    def test_archive_preserves_profile_and_ordinary_hard_delete_is_protected(self):
        patient = self.profile()
        self.patient_client.is_archived = True
        self.patient_client.save(update_fields=["is_archived", "updated_at"])
        self.assertTrue(PatientProfile.objects.filter(pk=patient.pk).exists())
        with self.assertRaises(ProtectedError):
            self.patient_client.delete()

    def test_merge_and_preview_block_either_medical_side_before_transfers(self):
        plan = VisitPlan.objects.create(business=self.business, client=self.duplicate,
                                       created_by=self.owner, responsible_user=self.owner)
        original_revision = plan.revision
        for client in (self.patient_client, self.duplicate):
            patient = self.profile(client)
            for command in (merge_clients, merge_clients_dry_run):
                with self.subTest(client=client.pk, command=command.__name__):
                    with patch("apps.clients.services.client_snapshot") as snapshot:
                        with self.assertRaises(InvalidTransition):
                            command(target_client=self.patient_client, duplicate_client=self.duplicate)
                        snapshot.assert_not_called()
            plan.refresh_from_db()
            self.duplicate.refresh_from_db()
            self.assertEqual(plan.client_id, self.duplicate.pk)
            self.assertEqual(plan.revision, original_revision)
            self.assertFalse(self.duplicate.is_archived)
            self.assertFalse(ClientMergeLog.objects.exists())
            patient.delete()

    def test_unrelated_business_profile_does_not_block_ordinary_merge(self):
        self.profile(self.foreign)
        result = merge_clients(target_client=self.patient_client, duplicate_client=self.duplicate, actor=self.owner)
        self.assertEqual(result["target_client_id"], self.patient_client.pk)
        self.duplicate.refresh_from_db()
        self.assertTrue(self.duplicate.is_archived)

    def test_existing_merge_api_returns_conflict_without_identity_contents(self):
        self.profile(demographics_encrypted="synthetic-secret-ciphertext")
        api = APIClient()
        api.force_authenticate(self.owner)
        for action in ("merge", "merge-dry-run"):
            with self.subTest(action=action):
                response = api.post(f"/api/clients/{self.patient_client.pk}/{action}/",
                                    {"duplicate_client_id": self.duplicate.pk}, format="json")
                self.assertEqual(response.status_code, 409, response.data)
                self.assertNotIn("synthetic-secret-ciphertext", str(response.data))
        self.duplicate.refresh_from_db()
        self.assertFalse(self.duplicate.is_archived)
