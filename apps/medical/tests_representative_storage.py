from datetime import timedelta

from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.db.models.deletion import ProtectedError
from django.test import TestCase
from django.utils import timezone

from apps.businesses.models import BusinessCapability
from apps.clients.models import Client, ClientMergeLog
from apps.clients.services import merge_clients, merge_clients_dry_run
from apps.clients.updates import update_client_snapshot
from apps.core.domain_errors import InvalidTransition
from apps.core.import_workspace.entities import write_basic_entity
from .models import PatientProfile, PatientRepresentative
from . import tests_patient_profile as fixtures


class RepresentativeStorageTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        fixtures.PatientProfileSchemaTests.setUpTestData.__func__(cls)
        cls.patient = PatientProfile.objects.create(business=cls.business, client=cls.patient_client, created_by=cls.owner)

    def representation(self, **overrides):
        now = timezone.now()
        return PatientRepresentative.objects.create(**{
            "patient": self.patient, "representative_client": self.duplicate,
            "authority_encrypted": "synthetic-ciphertext", "verified_by": self.owner,
            "verified_at": now, "valid_from": now, "valid_until": now + timedelta(days=1), **overrides,
        })

    def test_shared_contact_is_not_an_identity_or_automatic_patient_profile(self):
        relation = self.representation()
        self.assertEqual(relation.representative_client_id, self.duplicate.pk)
        self.assertEqual(Client.objects.filter(business=self.business).count(), 2)
        self.assertEqual(PatientProfile.objects.filter(business=self.business).count(), 1)
        child = Client.objects.create(business=self.business, full_name="Second child", phone=self.duplicate.phone)
        patient = PatientProfile.objects.create(business=self.business, client=child, created_by=self.owner)
        second = self.representation(patient=patient)
        self.assertNotEqual(relation.patient_id, second.patient_id)
        self.assertEqual(relation.representative_client_id, second.representative_client_id)

    def test_cross_tenant_and_self_representation_fail_validation(self):
        for client in (self.foreign, self.patient_client):
            with self.subTest(client=client.pk):
                relation = PatientRepresentative(patient=self.patient, representative_client=client)
                with self.assertRaises(ValidationError):
                    relation.clean()

    def test_valid_relation_passes_model_validation(self):
        self.representation().full_clean()

    def test_database_requires_evidence_positive_revision_valid_period_and_complete_revocation(self):
        now = timezone.now()
        cases = [
            {"authority_encrypted": ""}, {"revision": 0},
            {"valid_from": now, "valid_until": now},
            {"valid_from": now, "valid_until": now - timedelta(seconds=1)},
            {"revoked_at": now}, {"revoked_by": self.owner},
            {"revocation_encrypted": "orphaned-reason"},
            {"verified_at": now, "revoked_at": now - timedelta(seconds=1),
             "revoked_by": self.owner, "revocation_encrypted": "synthetic-reason"},
        ]
        for values in cases:
            with self.subTest(values=values), self.assertRaises(IntegrityError), transaction.atomic():
                self.representation(**values)
        self.assertFalse(PatientRepresentative.objects.exists())

    def test_period_can_be_open_ended_without_inventing_a_legal_limit(self):
        self.representation(valid_until=None).full_clean()

    def test_revocation_keeps_link_and_protects_both_people_from_hard_delete(self):
        relation = self.representation()
        relation.revoked_at = timezone.now()
        relation.revoked_by = self.owner
        relation.revocation_encrypted = "synthetic-reason-ciphertext"
        relation.revision = 2
        relation.save()
        relation.full_clean()
        for target in (self.patient, self.duplicate, self.patient_client):
            with self.subTest(target=type(target).__name__), self.assertRaises(ProtectedError):
                target.delete()
        self.assertTrue(PatientRepresentative.objects.filter(pk=relation.pk, revision=2).exists())

    def test_merge_of_representative_is_blocked_in_both_directions_without_transfer(self):
        self.representation()
        ordinary = Client.objects.create(business=self.business, full_name="Unrelated client")
        for target, duplicate in ((ordinary, self.duplicate), (self.duplicate, ordinary)):
            for command in (merge_clients, merge_clients_dry_run):
                with self.subTest(command=command.__name__, target=target.pk), self.assertRaises(InvalidTransition):
                    command(target_client=target, duplicate_client=duplicate)
        self.duplicate.refresh_from_db()
        ordinary.refresh_from_db()
        self.assertFalse(self.duplicate.is_archived)
        self.assertFalse(ordinary.is_archived)
        self.assertFalse(ClientMergeLog.objects.exists())

    def test_identity_guards_survive_module_disabled_and_revocation(self):
        relation = self.representation()
        PatientRepresentative.objects.filter(pk=relation.pk).update(revoked_at=timezone.now(),
            revoked_by=self.owner, revocation_encrypted="synthetic-reason", revision=2)
        BusinessCapability.objects.filter(business=self.business, module_key="medical_records").update(is_enabled=False)
        self.duplicate.full_name = "Different person"
        with self.assertRaises(InvalidTransition):
            self.duplicate.save(update_fields=["full_name"])
        self.duplicate.refresh_from_db()
        self.duplicate.business = self.other
        with self.assertRaises(InvalidTransition):
            self.duplicate.save(update_fields=["business"])
        self.duplicate.refresh_from_db()
        self.assertEqual(self.duplicate.business_id, self.business.pk)
        self.assertEqual(self.duplicate.full_name, "Synthetic relative")

    def test_conditional_editor_and_import_cannot_reassign_verified_person(self):
        self.representation()
        with self.assertRaises(InvalidTransition):
            update_client_snapshot(client=self.duplicate, expected_updated_at=self.duplicate.updated_at,
                                   values={"full_name": "Another person"})
        with self.assertRaises(InvalidTransition):
            write_basic_entity(business=self.business, actor=self.owner, entity_type="clients",
                values={"full_name": "Another person"}, decision={"action": "update",
                    "target_id": self.duplicate.pk, "update_fields": ["full_name"]}, reference="synthetic")
        self.duplicate.refresh_from_db()
        self.assertEqual(self.duplicate.full_name, "Synthetic relative")

    def test_contacts_and_archive_remain_editable_without_transferring_authority(self):
        relation = self.representation()
        self.duplicate.full_name = "Unsaved name draft"
        self.duplicate.phone = "+77000000003"
        self.duplicate.is_archived = True
        self.duplicate.save(update_fields=["phone", "is_archived"])
        self.duplicate.refresh_from_db()
        relation.refresh_from_db()
        self.assertEqual(self.duplicate.full_name, "Synthetic relative")
        self.assertEqual(self.duplicate.phone, "+77000000003")
        self.assertEqual(relation.representative_client_id, self.duplicate.pk)
        self.assertEqual(relation.revision, 1)
        self.assertEqual(relation.authority_encrypted, "synthetic-ciphertext")
