from unittest.mock import patch
from types import SimpleNamespace

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.contrib.admin.sites import AdminSite
from rest_framework.test import APIClient
from rest_framework.exceptions import ValidationError

from apps.businesses.models import Business
from apps.businesses.profiles import (
    CORE_MODULES, PROFILE_MODULES, BusinessProfileInvalid, create_profiled_business,
    initialize_business_profile,
)
from apps.core.domain_errors import InvalidTransition
from apps.core.models import AuditLog
from apps.businesses.admin import BusinessAdmin
from apps.accounts.google_auth_signup import create_owner_account
from apps.accounts.social_auth import _ensure_first_business


class BusinessProfileInitializationTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.owner = get_user_model().objects.create_user(
            username="profile-new", email="profile-new@example.test", password="test-only-62!"
        )

    def create(self, industry="dentistry", **kwargs):
        return create_profiled_business(
            owner=self.owner, name="New profile", slug=f"profile-{industry}",
            business_type=industry, **kwargs
        )

    def test_new_dental_has_plans_and_no_early_medical_activation(self):
        business = self.create()
        self.assertEqual((business.profile_key, business.profile_version), ("dentistry", 1))
        rows = dict(business.capabilities.values_list("module_key", "is_enabled"))
        self.assertEqual(set(rows), set(PROFILE_MODULES))
        self.assertTrue(rows["visit_plans"])
        self.assertTrue(rows["plan_payments"])
        self.assertFalse(rows["medical_records"])
        self.assertEqual(AuditLog.objects.get(business=business).metadata["kind"], "business_profile_assigned")
        self.assertFalse(business.members.exists())

    def test_other_known_industries_get_core_without_dental_modules(self):
        for industry in Business.BusinessTypes.values:
            if industry == "dentistry":
                continue
            with self.subTest(industry=industry):
                business = self.create(industry)
                self.assertEqual(business.profile_key, "core")
                rows = dict(business.capabilities.values_list("module_key", "is_enabled"))
                self.assertEqual({key for key, enabled in rows.items() if enabled}, set(CORE_MODULES))
                self.assertEqual(business.business_type, industry)

    def test_unknown_industry_is_rejected_before_creation(self):
        with self.assertRaises(ValidationError):
            self.create("unsupported")
        self.assertFalse(Business.objects.exists())

    def test_server_profile_input_is_rejected(self):
        with self.assertRaises(ValidationError):
            self.create(profile_key="dentistry", profile_version=2)
        self.assertFalse(Business.objects.exists())

    def test_audit_failure_rolls_back_business_and_capabilities(self):
        with patch("apps.core.audit.write_actor_audit_log", side_effect=RuntimeError("audit unavailable")):
            with self.assertRaises(RuntimeError):
                self.create()
        self.assertFalse(Business.objects.exists())
        from apps.businesses.models import BusinessCapability
        self.assertFalse(BusinessCapability.objects.exists())

    def test_repeat_preserves_timestamp_rows_and_audit(self):
        business = self.create()
        before = list(business.capabilities.values_list("pk", "is_enabled", "updated_at"))
        repeat = initialize_business_profile(business, actor=self.owner)
        self.assertEqual(repeat.profile_assigned_at, business.profile_assigned_at)
        self.assertEqual(list(business.capabilities.values_list("pk", "is_enabled", "updated_at")), before)
        self.assertEqual(AuditLog.objects.filter(business=business).count(), 1)

    def test_repeat_does_not_repair_drift(self):
        business = self.create()
        business.capabilities.filter(module_key="ai").delete()
        with self.assertRaises(BusinessProfileInvalid):
            initialize_business_profile(business, actor=self.owner)
        self.assertFalse(business.capabilities.filter(module_key="ai").exists())

    def test_saved_legacy_is_not_initialized_by_creation_service(self):
        business = Business.objects.create(owner=self.owner, name="Legacy", slug="legacy")
        with self.assertRaises(InvalidTransition):
            initialize_business_profile(business, actor=self.owner)
        business.refresh_from_db()
        self.assertIsNone(business.profile_key)
        self.assertFalse(business.capabilities.exists())

    def test_password_and_google_shared_creator_assigns_dental_profile(self):
        user, business = create_owner_account({
            "email": "shared-signup@example.test", "password": "Synthetic-test-71!",
            "business_name": "Shared signup", "business_type": "dentistry"
        })
        self.assertEqual((business.profile_key, business.profile_version), ("dentistry", 1))
        self.assertTrue(business.members.filter(user=user, role="owner").exists())
        self.assertFalse(business.capabilities.get(module_key="medical_records").is_enabled)

    def test_signup_profile_audit_failure_also_rolls_back_new_account(self):
        with patch("apps.core.audit.write_actor_audit_log", side_effect=RuntimeError("audit unavailable")):
            with self.assertRaises(RuntimeError):
                create_owner_account({"email": "rollback-signup@example.test", "password": "Synthetic-test-72!", "business_name": "Rollback"})
        self.assertFalse(get_user_model().objects.filter(email="rollback-signup@example.test").exists())
        self.assertFalse(Business.objects.exists())

    def test_business_post_assigns_profile(self):
        api = APIClient()
        api.force_authenticate(self.owner)
        response = api.post("/api/businesses/", {"name": "API creation", "slug": "api-profile", "business_type": "beauty"}, format="json")
        self.assertEqual(response.status_code, 201, response.data)
        business = Business.objects.get(pk=response.data["id"])
        self.assertEqual(business.profile_key, "core")
        self.assertFalse(business.capabilities.get(module_key="visit_plans").is_enabled)

    @override_settings(SOCIAL_AUTH_AUTO_CREATE_MERCHANT=True)
    def test_legacy_social_creates_once_and_preserves_assigned_profile(self):
        _ensure_first_business(self.owner)
        business = Business.objects.get(owner=self.owner)
        self.assertEqual(business.profile_key, "core")
        timestamp = business.profile_assigned_at
        _ensure_first_business(self.owner)
        business.refresh_from_db()
        self.assertEqual(Business.objects.filter(owner=self.owner).count(), 1)
        self.assertEqual(business.profile_assigned_at, timestamp)

    def test_admin_creation_uses_same_initializer(self):
        business = Business(owner=self.owner, name="Admin creation", slug="admin-profile", business_type="dentistry")
        BusinessAdmin(Business, AdminSite()).save_model(SimpleNamespace(user=self.owner), business, None, False)
        business.refresh_from_db()
        self.assertEqual(business.profile_key, "dentistry")
        self.assertEqual(business.capabilities.count(), len(PROFILE_MODULES))

    def test_both_signup_serializers_reject_supplied_profile(self):
        from apps.accounts.serializers import OwnerSignupSerializer
        from apps.accounts.google_auth import GoogleSignupSerializer
        for serializer_type in (OwnerSignupSerializer, GoogleSignupSerializer):
            with self.subTest(serializer=serializer_type.__name__):
                serializer = serializer_type(data={"profile": None})
                self.assertFalse(serializer.is_valid())
                self.assertIn("profile", serializer.errors)
