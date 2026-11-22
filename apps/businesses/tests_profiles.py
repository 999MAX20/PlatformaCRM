from django.contrib.auth import get_user_model
from django.contrib.admin.sites import AdminSite
from django.db import IntegrityError, transaction
from django.test import TestCase
from django.utils import timezone

from apps.businesses.admin import BusinessAdmin
from apps.businesses.capabilities import (
    apply_business_type_defaults, capability_payload, ensure_business_capabilities,
    is_module_enabled,
)
from apps.businesses.models import Business, BusinessCapability
from apps.businesses.profiles import (
    CORE_MODULES, PROFILE_FIELDS, PROFILE_INPUT_KEYS, PROFILE_SPECS,
    BusinessProfileInvalid,
)
from apps.businesses.serializers import BusinessSerializer
from apps.core.domain_errors import InvalidTransition


class BusinessProfileReadTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.owner = get_user_model().objects.create_user(
            username="profile-owner", email="profiles@example.test", password="test-only-482!"
        )
        cls.business = Business.objects.create(
            owner=cls.owner, name="Profile test", slug="profile-test", business_type="dentistry"
        )

    def assign_fixture(self, key="dentistry", version=2):
        Business.objects.filter(pk=self.business.pk).update(
            profile_key=key, profile_version=version, profile_assigned_at=timezone.now(),
            business_type="dentistry" if key == "dentistry" else "other",
        )
        spec = PROFILE_SPECS[(key, version)]
        BusinessCapability.objects.bulk_create([
            BusinessCapability(business=self.business, module_key=module, is_enabled=True)
            for module in spec.modules
        ])

    def test_legacy_does_not_gain_medical_access_from_extra_row(self):
        BusinessCapability.objects.create(
            business=self.business, module_key="medical_records", is_enabled=True
        )
        payload = capability_payload(self.business)
        self.assertIsNone(payload["profile"])
        self.assertFalse(payload["modules"]["medical_records"])
        self.assertTrue(payload["modules"]["visit_plans"])
        self.assertTrue(payload["modules"]["plan_payments"])
        self.business.refresh_from_db()
        self.assertIsNone(self.business.profile_key)

    def test_legacy_plan_keys_follow_existing_dependencies_not_extra_rows(self):
        for key, enabled in (("appointments", False), ("visit_plans", True), ("plan_payments", True)):
            BusinessCapability.objects.create(business=self.business, module_key=key, is_enabled=enabled)
        payload = capability_payload(self.business)
        for key in ("visit_plans", "plan_payments"):
            self.assertFalse(payload["modules"][key])
            self.assertFalse(is_module_enabled(self.business, key))

    def test_core_profile_cannot_gain_dental_modules_from_extra_rows(self):
        self.assign_fixture("core", 1)
        for key in ("visit_plans", "plan_payments", "medical_records"):
            BusinessCapability.objects.create(business=self.business, module_key=key, is_enabled=True)
            self.assertFalse(is_module_enabled(self.business, key))
        self.assertTrue(is_module_enabled(self.business, "clients"))

    def test_published_dentistry_v1_does_not_gain_v2_medical_module(self):
        self.assign_fixture(version=1)
        BusinessCapability.objects.create(business=self.business, module_key="medical_records", is_enabled=True)
        self.assertTrue(is_module_enabled(self.business, "visit_plans"))
        self.assertFalse(is_module_enabled(self.business, "medical_records"))

    def test_profile_reads_do_not_repair_missing_rows(self):
        self.assign_fixture()
        BusinessCapability.objects.filter(business=self.business, module_key="clients").delete()
        before = self.business.capabilities.count()
        ensure_business_capabilities(self.business)
        payload = capability_payload(self.business)
        for key in ("clients", "visit_plans", "plan_payments", "medical_records"):
            self.assertFalse(payload["modules"][key])
        self.assertEqual(self.business.capabilities.count(), before)
        self.assertEqual(payload["profile"]["version"], 2)

    def test_unknown_profile_fails_without_mutating_rows(self):
        self.assign_fixture()
        Business.objects.filter(pk=self.business.pk).update(profile_version=999)
        before = list(self.business.capabilities.values_list("module_key", "is_enabled"))
        for operation in (
            lambda: capability_payload(self.business),
            lambda: ensure_business_capabilities(self.business),
            lambda: is_module_enabled(self.business, "clients"),
        ):
            with self.assertRaises(BusinessProfileInvalid):
                operation()
        self.assertEqual(list(self.business.capabilities.values_list("module_key", "is_enabled")), before)

    def test_defaults_cannot_reset_a_profiled_business(self):
        self.assign_fixture()
        BusinessCapability.objects.filter(business=self.business, module_key="ai").update(is_enabled=False)
        with self.assertRaises(InvalidTransition):
            apply_business_type_defaults(self.business)
        self.assertFalse(is_module_enabled(self.business, "ai"))

    def test_unknown_module_is_denied_for_legacy_and_profiled_business(self):
        self.assertFalse(is_module_enabled(self.business, "future_unknown"))
        self.assign_fixture()
        self.assertFalse(is_module_enabled(self.business, "future_unknown"))

    def test_legacy_defaults_keep_exactly_original_ten_modules(self):
        ensure_business_capabilities(self.business)
        self.assertEqual(set(self.business.capabilities.values_list("module_key", flat=True)), set(CORE_MODULES))

    def test_database_rejects_partial_empty_and_zero_version_profiles(self):
        for values in (
            {"profile_key": "dentistry"},
            {"profile_version": 1},
            {"profile_assigned_at": timezone.now()},
            {"profile_key": "", "profile_version": 1, "profile_assigned_at": timezone.now()},
            {"profile_key": "dentistry", "profile_version": 0, "profile_assigned_at": timezone.now()},
        ):
            with self.subTest(values=values), self.assertRaises(IntegrityError), transaction.atomic():
                Business.objects.filter(pk=self.business.pk).update(**values)

    def test_api_rejects_server_profile_fields_including_null(self):
        for key in PROFILE_INPUT_KEYS:
            with self.subTest(key=key):
                serializer = BusinessSerializer(self.business, data={key: None, "name": "Must not save"}, partial=True)
                self.assertFalse(serializer.is_valid())
                self.assertIn(key, serializer.errors)
        self.business.refresh_from_db()
        self.assertEqual(self.business.name, "Profile test")

    def test_admin_cannot_edit_profile_metadata(self):
        model_admin = BusinessAdmin(Business, AdminSite())
        self.assertTrue(set(PROFILE_FIELDS).issubset(model_admin.get_readonly_fields(None, self.business)))
