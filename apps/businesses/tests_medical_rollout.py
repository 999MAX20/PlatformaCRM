import json
from concurrent.futures import ThreadPoolExecutor
from io import StringIO
from threading import Barrier
from unittest import skipUnless
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.core.management.base import CommandError
from django.db import connection, connections, close_old_connections
from django.test import TestCase, TransactionTestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounts.google_auth_signup import create_owner_account
from apps.clients.models import Client
from apps.core.domain_errors import InvalidTransition
from apps.core.models import AuditLog
from apps.medical.models import DentalMedicalRecord, MedicalRoleAssignment, PatientProfile
from .capabilities import capability_payload, is_module_enabled
from .medical_rollout import activate_medical_profile, preview_medical_rollout
from .models import Business, BusinessCapability, BusinessMember
from .profiles import BusinessProfileInvalid, CORE_MODULES, PROFILE_MODULES, create_profiled_business


@override_settings(DENTAL_MEDICAL_RELEASE_ENABLED=False)
class MedicalRolloutTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.owner = get_user_model().objects.create_user(username="rollout", email="rollout@example.test")
        cls.business = Business.objects.create(owner=cls.owner, name="Synthetic dental", slug="rollout",
            business_type="dentistry", currency="KZT", language="kk", sla_minutes=73)
        cls.member = BusinessMember.objects.create(business=cls.business, user=cls.owner, role="owner")
        cls.patient_client = Client.objects.create(business=cls.business, full_name="Synthetic client")

    def activate(self):
        return activate_medical_profile(business_id=self.business.pk)

    def test_release_disabled_preserves_old_creation_and_blocks_apply(self):
        new = create_profiled_business(owner=self.owner, name="Before release", slug="before", business_type="dentistry")
        self.assertEqual(new.profile_version, 1)
        with self.assertRaises(InvalidTransition):
            self.activate()
        with self.assertRaises(CommandError):
            call_command("activate_dental_medical", apply=True, stdout=StringIO())
        self.business.refresh_from_db()
        self.assertIsNone(self.business.profile_key)

    def test_default_command_is_read_only_even_when_release_is_ready(self):
        for ready in (False, True):
            with override_settings(DENTAL_MEDICAL_RELEASE_ENABLED=ready):
                output = StringIO()
                call_command("activate_dental_medical", stdout=output)
                self.assertEqual(json.loads(output.getvalue())["planned"], 1)
        self.business.refresh_from_db()
        self.assertIsNone(self.business.profile_key)
        self.assertFalse(BusinessCapability.objects.exists())
        self.assertFalse(AuditLog.objects.exists())

    @override_settings(DENTAL_MEDICAL_RELEASE_ENABLED=True)
    def test_legacy_upgrade_preserves_rows_settings_ids_and_does_not_create_clinical_data(self):
        disabled = BusinessCapability.objects.create(business=self.business, module_key="ai", is_enabled=False,
                                                    configured_by=self.owner)
        before = Business.objects.values().get(pk=self.business.pk)
        cap_before = BusinessCapability.objects.values().get(pk=disabled.pk)
        self.assertEqual(self.activate()["status"], "activated")
        after = Business.objects.values().get(pk=self.business.pk)
        for field in set(before) - {"profile_key", "profile_version", "profile_assigned_at", "updated_at"}:
            self.assertEqual(after[field], before[field], field)
        self.assertEqual(BusinessCapability.objects.values().get(pk=disabled.pk), cap_before)
        self.assertEqual(Client.objects.get(pk=self.patient_client.pk).business_id, self.business.pk)
        self.assertEqual(BusinessMember.objects.get(pk=self.member.pk).role, "owner")
        self.assertFalse(PatientProfile.objects.exists())
        self.assertFalse(DentalMedicalRecord.objects.exists())
        self.assertFalse(MedicalRoleAssignment.objects.exists())
        self.assertTrue(is_module_enabled(self.business, "medical_records"))
        event = AuditLog.objects.get(business=self.business)
        self.assertIsNone(event.actor_id)
        self.assertEqual(event.metadata["previous_profile"], None)

    @override_settings(DENTAL_MEDICAL_RELEASE_ENABLED=True)
    def test_repeat_preserves_timestamp_capability_ids_and_explicit_disabled_v2(self):
        self.activate()
        BusinessCapability.objects.filter(business=self.business, module_key="medical_records").update(is_enabled=False)
        before = Business.objects.values().get(pk=self.business.pk)
        caps = list(self.business.capabilities.order_by("pk").values())
        self.assertEqual(self.activate()["status"], "unchanged")
        self.assertEqual(Business.objects.values().get(pk=self.business.pk), before)
        self.assertEqual(list(self.business.capabilities.order_by("pk").values()), caps)
        self.assertEqual(AuditLog.objects.filter(business=self.business).count(), 1)

        self.assertFalse(is_module_enabled(self.business, "medical_records"))

    @override_settings(DENTAL_MEDICAL_RELEASE_ENABLED=True)
    def test_v1_upgrade_changes_only_medical_capability_and_profile(self):
        with override_settings(DENTAL_MEDICAL_RELEASE_ENABLED=False):
            business = create_profiled_business(owner=self.owner, name="V1", slug="v1", business_type="dentistry")
        preserved = list(business.capabilities.exclude(module_key="medical_records").order_by("pk").values())
        medical_id = business.capabilities.get(module_key="medical_records").pk
        activate_medical_profile(business_id=business.pk)
        self.assertEqual(list(business.capabilities.exclude(module_key="medical_records").order_by("pk").values()), preserved)
        self.assertTrue(business.capabilities.get(pk=medical_id).is_enabled)
        self.assertEqual(AuditLog.objects.filter(business=business).count(), 2)

    @override_settings(DENTAL_MEDICAL_RELEASE_ENABLED=True)
    def test_legacy_dependencies_and_stale_cache_keep_denial(self):
        BusinessCapability.objects.create(business=self.business, module_key="clients", is_enabled=False)
        self.business._capability_map = {key: True for key in PROFILE_MODULES}
        self.activate()
        payload = capability_payload(self.business)
        self.assertFalse(payload["modules"]["clients"])
        self.assertFalse(payload["modules"]["visit_plans"])
        self.assertFalse(payload["modules"]["plan_payments"])
        self.assertFalse(payload["modules"]["medical_records"])
        self.assertFalse(is_module_enabled(self.business, "medical_records"))

    @override_settings(DENTAL_MEDICAL_RELEASE_ENABLED=True)
    def test_audit_failure_rolls_back_all_changes(self):
        with patch("apps.businesses.medical_rollout.write_actor_audit_log", side_effect=RuntimeError("Synthetic audit failure")):
            with self.assertRaises(RuntimeError):
                self.activate()
        self.business.refresh_from_db()
        self.assertIsNone(self.business.profile_key)
        self.assertFalse(self.business.capabilities.exists())
        self.assertEqual(self.activate()["status"], "activated")

    @override_settings(DENTAL_MEDICAL_RELEASE_ENABLED=True)
    def test_new_businesses_get_v2_but_other_industries_keep_core(self):
        for industry in Business.BusinessTypes.values:
            business = create_profiled_business(owner=self.owner, name=industry, slug=industry, business_type=industry)
            self.assertEqual(business.profile_version, 2 if industry == "dentistry" else 1)
            enabled = set(business.capabilities.filter(is_enabled=True).values_list("module_key", flat=True))
            self.assertEqual(enabled, set(PROFILE_MODULES if industry == "dentistry" else CORE_MODULES))
            if industry != "dentistry":
                with self.assertRaises(InvalidTransition):
                    activate_medical_profile(business_id=business.pk)

    @override_settings(DENTAL_MEDICAL_RELEASE_ENABLED=True)
    def test_invalid_configuration_is_not_repaired_and_command_can_resume(self):
        invalid = Business.objects.create(owner=self.owner, name="Invalid", slug="invalid", business_type="dentistry",
            profile_key="dentistry", profile_version=999, profile_assigned_at=timezone.now())
        other = Business.objects.create(owner=self.owner, name="Other", slug="other")
        with self.assertRaises(BusinessProfileInvalid):
            preview_medical_rollout(business_id=invalid.pk)
        output = StringIO()
        with self.assertRaises(CommandError):
            call_command("activate_dental_medical", apply=True, stdout=output, stderr=StringIO())
        result = json.loads(output.getvalue())
        self.assertEqual((result["activated"], result["failed"]), (1, 1))
        invalid.refresh_from_db(); other.refresh_from_db()
        self.assertEqual(invalid.profile_version, 999)
        self.assertIsNone(other.profile_key)
        self.assertFalse(other.capabilities.exists())
        output = StringIO()
        with self.assertRaises(CommandError):
            call_command("activate_dental_medical", apply=True, stdout=output, stderr=StringIO())
        self.assertEqual(json.loads(output.getvalue())["unchanged"], 1)
        self.assertEqual(AuditLog.objects.filter(business=self.business).count(), 1)

@override_settings(DENTAL_MEDICAL_RELEASE_ENABLED=True)
class MedicalRolloutCreationAPITests(TestCase):
    def assert_clinical_access_not_granted(self, owner, business):
        self.assertEqual((business.profile_key, business.profile_version), ("dentistry", 2))
        self.assertTrue(is_module_enabled(business, "medical_records"))
        self.assertFalse(MedicalRoleAssignment.objects.filter(member__business=business).exists())
        self.assertFalse(PatientProfile.objects.exists())
        self.assertFalse(DentalMedicalRecord.objects.exists())
        api = APIClient()
        api.force_authenticate(owner)
        response = api.get("/api/medical/document-templates/workspace-access/", {"business_id": business.pk})
        self.assertEqual(response.status_code, 403, response.data)

    def test_business_creation_api_assigns_v2_without_owner_clinical_access(self):
        owner = get_user_model().objects.create_user(username="rollout-api", email="rollout-api@example.test")
        api = APIClient()
        api.force_authenticate(owner)
        response = api.post("/api/businesses/", {
            "name": "Synthetic dental API", "slug": "rollout-api", "business_type": "dentistry"
        }, format="json")
        self.assertEqual(response.status_code, 201, response.data)
        self.assert_clinical_access_not_granted(owner, Business.objects.get(pk=response.data["id"]))

    def test_shared_signup_creation_assigns_v2_without_owner_clinical_access(self):
        owner, business = create_owner_account({
            "email": "rollout-signup@example.test", "password": "Synthetic-test-82!",
            "business_name": "Synthetic dental signup", "business_type": "dentistry"
        })
        self.assertTrue(business.members.filter(user=owner, role="owner").exists())
        self.assert_clinical_access_not_granted(owner, business)


@skipUnless(connection.vendor == "postgresql", "Real row locks require PostgreSQL")
@override_settings(DENTAL_MEDICAL_RELEASE_ENABLED=True)
class MedicalRolloutConcurrencyTests(TransactionTestCase):
    def test_two_rollouts_create_one_profile_transition_and_audit(self):
        owner = get_user_model().objects.create_user(username="rollout-race")
        business = Business.objects.create(owner=owner, name="Synthetic race", slug="race", business_type="dentistry")
        barrier = Barrier(2)

        def upgrade():
            close_old_connections()
            try:
                barrier.wait(timeout=10)
                return activate_medical_profile(business_id=business.pk)["status"]
            finally:
                connections.close_all()

        with ThreadPoolExecutor(max_workers=2) as executor:
            results = [executor.submit(upgrade) for _ in range(2)]
            self.assertCountEqual([future.result(timeout=20) for future in results], ["activated", "unchanged"])
        self.assertEqual(BusinessCapability.objects.filter(business=business).count(), len(PROFILE_MODULES))
        self.assertEqual(AuditLog.objects.filter(business=business).count(), 1)
