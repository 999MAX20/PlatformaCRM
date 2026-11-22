from unittest.mock import patch
import pyotp

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied
from rest_framework.test import APIClient

from apps.businesses.models import Business, BusinessCapability, BusinessMember
from apps.businesses.activation import activate_landing_business
from apps.businesses.profiles import update_business_capability
from apps.businesses.serializers import BusinessSerializer, BusinessCapabilitySerializer
from apps.core.domain_errors import InvalidTransition
from apps.core.models import AuditLog
from apps.onboarding.services import apply_niche_template
from apps.accounts.mfa import issue_step_up_token
from apps.accounts.models import MfaDevice
from apps.integrations.credential_encryption import encrypt_credential_value


class BusinessProfileWriteTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.owner = get_user_model().objects.create_user(
            username="profile-writer", email="profile-writer@example.test", password="test-only-42!"
        )
        cls.foreign = get_user_model().objects.create_user(
            username="profile-foreign", email="profile-foreign@example.test", password="test-only-42!"
        )
        cls.business = Business.objects.create(
            owner=cls.owner, name="Writer fixture", slug="profile-writer", business_type="dentistry"
        )
        cls.capability = BusinessCapability.objects.create(
            business=cls.business, module_key="clients", is_enabled=True
        )

    def assign_profile(self):
        Business.objects.filter(pk=self.business.pk).update(
            profile_key="dentistry", profile_version=2, profile_assigned_at=timezone.now()
        )

    def test_stale_business_update_cannot_change_profile_or_save_other_fields(self):
        serializer = BusinessSerializer(self.business, data={"business_type": "other", "name": "Wrong"}, partial=True)
        self.assertTrue(serializer.is_valid(), serializer.errors)
        self.assign_profile()
        with self.assertRaises(InvalidTransition):
            serializer.save()
        self.business.refresh_from_db()
        self.assertEqual(self.business.name, "Writer fixture")
        self.assertEqual(self.business.business_type, "dentistry")

    def test_profile_allows_ordinary_settings_with_same_industry(self):
        self.assign_profile()
        serializer = BusinessSerializer(self.business, data={"business_type": "dentistry", "name": "Renamed"}, partial=True)
        self.assertTrue(serializer.is_valid(), serializer.errors)
        serializer.save()
        self.business.refresh_from_db()
        self.assertEqual(self.business.name, "Renamed")
        self.assertEqual(self.business.profile_version, 2)

    def test_legacy_capability_write_preserves_audit_and_invalidates_object_cache(self):
        self.capability.business._capability_map = {"clients": True}
        result = update_business_capability(capability=self.capability, actor=self.owner, is_enabled=False)
        self.assertFalse(result.is_enabled)
        self.assertEqual(result.configured_by_id, self.owner.pk)
        self.assertFalse(hasattr(self.capability.business, "_capability_map"))
        self.assertEqual(AuditLog.objects.filter(business=self.business, entity_type="BusinessCapability").count(), 1)

    def test_profile_capability_changes_are_rejected_after_fresh_lock(self):
        self.assign_profile()
        with self.assertRaises(InvalidTransition):
            update_business_capability(capability=self.capability, actor=self.owner, is_enabled=False)
        self.capability.refresh_from_db()
        self.assertTrue(self.capability.is_enabled)
        self.assertFalse(AuditLog.objects.filter(business=self.business).exists())

    def test_same_profile_value_does_not_write_or_audit(self):
        self.assign_profile()
        timestamp = self.capability.updated_at
        update_business_capability(capability=self.capability, actor=self.owner, is_enabled=True)
        self.capability.refresh_from_db()
        self.assertEqual(self.capability.updated_at, timestamp)
        self.assertIsNone(self.capability.configured_by_id)
        self.assertFalse(AuditLog.objects.filter(business=self.business).exists())

    def test_foreign_actor_cannot_write_even_with_known_capability(self):
        with self.assertRaises(PermissionDenied):
            update_business_capability(capability=self.capability, actor=self.foreign, is_enabled=False)
        self.capability.refresh_from_db()
        self.assertTrue(self.capability.is_enabled)

    def test_audit_failure_rolls_back_legacy_write(self):
        with patch("apps.core.audit.write_actor_audit_log", side_effect=RuntimeError("audit unavailable")):
            with self.assertRaises(RuntimeError):
                update_business_capability(capability=self.capability, actor=self.owner, is_enabled=False)
        self.capability.refresh_from_db()
        self.assertTrue(self.capability.is_enabled)
        self.assertIsNone(self.capability.configured_by_id)

    def test_legacy_profile_managed_key_cannot_be_toggled(self):
        row = BusinessCapability.objects.create(business=self.business, module_key="medical_records", is_enabled=False)
        with self.assertRaises(InvalidTransition):
            update_business_capability(capability=row, actor=self.owner, is_enabled=True)

    def test_capability_identity_input_is_rejected(self):
        for field, value in (("business", self.business.pk), ("module_key", "clients")):
            with self.subTest(field=field):
                serializer = BusinessCapabilitySerializer(self.capability, data={field: value}, partial=True)
                self.assertFalse(serializer.is_valid())
                self.assertIn(field, serializer.errors)

    def test_empty_patch_does_not_revert_newer_value(self):
        BusinessCapability.objects.filter(pk=self.capability.pk).update(is_enabled=False)
        serializer = BusinessCapabilitySerializer(self.capability, data={}, partial=True)
        self.assertTrue(serializer.is_valid())
        result = serializer.save(configured_by=self.owner)
        self.assertFalse(result.is_enabled)
        self.assertFalse(AuditLog.objects.filter(business=self.business).exists())

    def test_template_denied_before_partial_changes_even_with_stale_instance(self):
        self.assign_profile()
        with self.assertRaises(InvalidTransition):
            apply_niche_template(self.business, "beauty", actor=self.owner)
        self.business.refresh_from_db()
        self.assertEqual(self.business.business_type, "dentistry")
        self.assertFalse(self.business.services.exists())

    def test_http_capability_profile_conflict_and_noop(self):
        self.assign_profile()
        BusinessMember.objects.create(business=self.business, user=self.owner, role="owner")
        api = APIClient()
        api.force_authenticate(self.owner)
        url = f"/api/business-capabilities/{self.capability.pk}/"
        response = api.patch(url, {"is_enabled": False}, format="json")
        self.assertEqual(response.status_code, 409, response.data)
        response = api.patch(url, {"is_enabled": True}, format="json")
        self.assertEqual(response.status_code, 200, response.data)
        self.assertFalse(AuditLog.objects.filter(business=self.business, entity_type="BusinessCapability").exists())

    def test_http_capability_foreign_business_is_not_found(self):
        api = APIClient()
        api.force_authenticate(self.foreign)
        response = api.patch(f"/api/business-capabilities/{self.capability.pk}/", {"is_enabled": False}, format="json")
        self.assertEqual(response.status_code, 404, response.data)

    def test_http_business_change_rejects_entire_patch(self):
        self.assign_profile()
        BusinessMember.objects.create(business=self.business, user=self.owner, role="owner")
        api = APIClient()
        api.force_authenticate(self.owner)
        response = api.patch(f"/api/businesses/{self.business.pk}/", {"business_type": "other", "name": "Wrong"}, format="json")
        self.assertEqual(response.status_code, 409, response.data)
        self.business.refresh_from_db()
        self.assertEqual(self.business.name, "Writer fixture")

    def test_landing_repeat_without_industry_preserves_assigned_profile(self):
        Business.objects.filter(pk=self.business.pk).update(landing_id="profile-writer-landing")
        self.assign_profile()
        result = activate_landing_business(
            landing_id="profile-writer-landing", owner_email=self.owner.email, business_name="Renamed"
        )
        self.assertFalse(result.created_business)
        self.assertEqual(result.business.business_type, "dentistry")
        self.assertEqual(result.business.profile_version, 2)

    def test_landing_explicit_other_is_conflict_before_owner_changes(self):
        Business.objects.filter(pk=self.business.pk).update(landing_id="profile-writer-landing")
        self.assign_profile()
        old_name = self.owner.full_name
        with self.assertRaises(InvalidTransition):
            activate_landing_business(
                landing_id="profile-writer-landing", owner_email=self.owner.email,
                business_name="Wrong", business_type="other", owner_full_name="Wrong owner"
            )
        self.owner.refresh_from_db()
        self.business.refresh_from_db()
        self.assertEqual(self.owner.full_name, old_name)
        self.assertEqual(self.business.name, "Writer fixture")

    def test_http_landing_repeat_distinguishes_missing_industry_from_other(self):
        Business.objects.filter(pk=self.business.pk).update(landing_id="profile-writer-landing")
        self.assign_profile()
        admin = get_user_model().objects.create_user(
            username="profile-platform", email="profile-platform@example.test",
            password="test-only-52!", role="platform_admin"
        )
        secret = pyotp.random_base32()
        MfaDevice.objects.create(user=admin, encrypted_secret=encrypt_credential_value(secret), confirmed_at=timezone.now())
        token = issue_step_up_token(admin, pyotp.TOTP(secret).now())
        api = APIClient()
        api.force_authenticate(admin)
        payload = {"landing_id": "profile-writer-landing", "owner_email": self.owner.email, "business_name": "Renamed"}
        response = api.post("/api/platform/activate-landing/", payload, format="json", HTTP_X_ZANI_MFA_STEP_UP=token)
        self.assertEqual(response.status_code, 200, response.data)
        self.business.refresh_from_db()
        self.assertEqual(self.business.business_type, "dentistry")
        response = api.post("/api/platform/activate-landing/", {**payload, "business_type": "other"}, format="json", HTTP_X_ZANI_MFA_STEP_UP=token)
        self.assertEqual(response.status_code, 409, response.data)
