from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from apps.businesses.models import Business, BusinessCapability
from apps.clients.models import Client
from apps.clients.updates import ClientEditConflict, update_client_snapshot
from apps.core.domain_errors import InvalidTransition
from apps.core.import_workspace.entities import write_basic_entity
from apps.core.models import AuditLog
from .models import PatientProfile
from . import tests_patient_services as fixtures


class ClientIdentityGuardTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        fixtures.PatientCreationTests.setUpTestData.__func__(cls)
        cls.profile = PatientProfile.objects.create(business=cls.business, client=cls.patient_client,
            created_by=cls.reception, identity_status="verified", verified_at=timezone.now(),
            verified_by=cls.reception, verification_evidence_encrypted="synthetic-evidence")

    def test_direct_save_blocks_verified_name_even_with_module_off(self):
        BusinessCapability.objects.filter(business=self.business, module_key="medical_records").update(is_enabled=False)
        self.patient_client.full_name = "Wrong identity"
        with self.assertRaises(InvalidTransition):
            self.patient_client.save()
        self.patient_client.refresh_from_db()
        self.assertEqual(self.patient_client.full_name, "Synthetic patient")

    def test_partial_name_save_is_guarded(self):
        self.patient_client.full_name = "Wrong identity"
        with self.assertRaises(InvalidTransition):
            self.patient_client.save(update_fields=["full_name"])

    def test_explicit_existing_pk_cannot_bypass_guard_as_new_instance(self):
        replacement = Client(pk=self.patient_client.pk, business=self.business, full_name="Wrong replacement")
        with self.assertRaises(InvalidTransition):
            replacement.save()

    def test_new_explicit_pk_without_profile_can_be_created(self):
        fresh = Client(pk=self.patient_client.pk + 9999, business=self.business, full_name="New identity")
        fresh.save(force_insert=True)
        self.assertTrue(Client.objects.filter(pk=fresh.pk).exists())

    def test_contact_only_save_ignores_unsaved_name_and_preserves_verification(self):
        self.patient_client.full_name = "Unsaved draft"
        self.patient_client.phone = "+77000000003"
        self.patient_client.save(update_fields=["phone"])
        self.patient_client.refresh_from_db()
        self.profile.refresh_from_db()
        self.assertEqual(self.patient_client.full_name, "Synthetic patient")
        self.assertEqual(self.patient_client.normalized_phone, "77000000003")
        self.assertEqual(self.profile.identity_status, "verified")

    def test_preliminary_and_ordinary_client_names_remain_editable(self):
        PatientProfile.objects.filter(pk=self.profile.pk).update(identity_status="unverified",
            verified_at=None, verified_by=None)
        self.patient_client.full_name = "Preliminary corrected name"
        self.patient_client.save(update_fields=["full_name"])
        self.relative.full_name = "Ordinary corrected name"
        self.relative.save(update_fields=["full_name"])
        self.patient_client.refresh_from_db()
        self.assertEqual(self.patient_client.full_name, "Preliminary corrected name")

    def test_unverified_profile_prevents_tenant_move(self):
        PatientProfile.objects.filter(pk=self.profile.pk).update(identity_status="unverified",
            verified_at=None, verified_by=None)
        foreign = Business.objects.create(owner=self.owner, name="Foreign", slug="identity-foreign")
        self.patient_client.business = foreign
        with self.assertRaises(InvalidTransition):
            self.patient_client.save(update_fields=["business"])
        self.patient_client.refresh_from_db()
        self.assertEqual(self.patient_client.business_id, self.business.pk)

    def test_conditional_writer_cannot_bypass_save_guard(self):
        with self.assertRaises(InvalidTransition):
            update_client_snapshot(client=self.patient_client, expected_updated_at=self.patient_client.updated_at,
                                   values={"full_name": "Wrong identity", "notes": "Must roll back"})
        self.patient_client.refresh_from_db()
        self.assertEqual(self.patient_client.notes, "")

    def test_stale_object_cannot_hide_actual_name_change(self):
        self.patient_client.full_name = "Wrong identity"
        with self.assertRaises(InvalidTransition):
            update_client_snapshot(client=self.patient_client, expected_updated_at=self.patient_client.updated_at,
                                   values={"full_name": self.patient_client.full_name})

    def test_same_name_and_contact_update_are_allowed(self):
        result = update_client_snapshot(client=self.patient_client, expected_updated_at=self.patient_client.updated_at,
            values={"full_name": self.patient_client.full_name, "phone": "+77000000003"})
        self.assertEqual(result.phone, "+77000000003")

    def test_stale_version_keeps_existing_conflict(self):
        before = self.patient_client.updated_at
        update_client_snapshot(client=self.patient_client, expected_updated_at=before, values={"notes": "New"})
        with self.assertRaises(ClientEditConflict):
            update_client_snapshot(client=self.patient_client, expected_updated_at=before, values={"full_name": "Wrong"})

    def test_api_owner_cannot_rename_verified_patient(self):
        api = APIClient()
        api.force_authenticate(self.owner)
        count = AuditLog.objects.count()
        response = api.patch(f"/api/clients/{self.patient_client.pk}/", {
            "expected_updated_at": self.patient_client.updated_at.isoformat(), "full_name": "Wrong identity",
        }, format="json")
        self.assertEqual(response.status_code, 409)
        self.assertEqual(AuditLog.objects.count(), count)
        self.patient_client.refresh_from_db()
        self.assertEqual(self.patient_client.full_name, "Synthetic patient")

    def test_import_rejects_name_change_without_success_audit(self):
        count = AuditLog.objects.count()
        with self.assertRaises(InvalidTransition):
            write_basic_entity(business=self.business, actor=self.owner, entity_type="clients",
                values={"full_name": "Imported wrong identity"}, decision={"action": "update",
                    "target_id": self.patient_client.pk, "update_fields": ["full_name"]}, reference="synthetic")
        self.assertEqual(AuditLog.objects.count(), count)
        self.patient_client.refresh_from_db()
        self.assertEqual(self.patient_client.full_name, "Synthetic patient")

    def test_import_contact_update_preserves_identity(self):
        client, outcome, _, _, _ = write_basic_entity(business=self.business, actor=self.owner, entity_type="clients",
            values={"phone": "+77000000003"}, decision={"action": "update",
                "target_id": self.patient_client.pk, "update_fields": ["phone"]}, reference="synthetic")
        self.assertEqual(outcome, "updated")
        self.assertEqual(client.full_name, "Synthetic patient")
        self.assertEqual(client.phone, "+77000000003")
