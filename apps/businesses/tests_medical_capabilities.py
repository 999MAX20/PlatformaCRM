from django.contrib.auth import get_user_model
from django.test import TestCase

from apps.businesses.capabilities import (
    MODULE_REGISTRY,
    assert_resource_enabled,
    capability_payload,
    ensure_business_capabilities,
    is_module_enabled,
    resource_is_enabled,
)
from apps.businesses.models import Business, BusinessCapability
from apps.core.domain_errors import ModuleDisabled


class MedicalCapabilityTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.owner = get_user_model().objects.create_user(
            username="medical-capability-owner", email="medical-capability@example.test",
            password="Synthetic-test-38!"
        )
        cls.dental = Business.objects.create(
            owner=cls.owner, name="Dental capability test", slug="medical-capability",
            business_type=Business.BusinessTypes.DENTISTRY,
        )
        cls.other = Business.objects.create(
            owner=cls.owner, name="Other capability test", slug="other-capability",
            business_type=Business.BusinessTypes.OTHER,
        )

    def enable(self, business):
        return BusinessCapability.objects.create(
            business=business, module_key="medical_records", is_enabled=True
        )

    def test_dentistry_alone_does_not_enable_clinical_resources(self):
        for resource in (
            "medical_patients", "medical_records", "medical_documents",
            "medical_prescriptions", "medical_files",
        ):
            with self.subTest(resource=resource):
                self.assertFalse(resource_is_enabled(self.dental, resource))
                with self.assertRaises(ModuleDisabled):
                    assert_resource_enabled(self.dental, resource)
        self.assertFalse(self.dental.capabilities.exists())

    def test_explicit_enable_is_scoped_to_business_and_industry(self):
        self.enable(self.dental)
        self.enable(self.other)
        self.assertTrue(resource_is_enabled(self.dental, "medical_documents"))
        self.assertFalse(resource_is_enabled(self.other, "medical_documents"))
        second = Business.objects.create(
            owner=self.owner, name="Second dental", slug="second-dental",
            business_type=Business.BusinessTypes.DENTISTRY,
        )
        self.assertFalse(resource_is_enabled(second, "medical_documents"))

    def test_revocation_and_deletion_override_loaded_cache(self):
        row = self.enable(self.dental)
        ensure_business_capabilities(self.dental)
        self.assertTrue(self.dental._capability_map["medical_records"])
        BusinessCapability.objects.filter(pk=row.pk).update(is_enabled=False)
        self.assertFalse(is_module_enabled(self.dental, "medical_records"))
        row.delete()
        self.assertFalse(is_module_enabled(self.dental, "medical_records"))

    def test_industry_change_is_checked_against_database(self):
        self.enable(self.dental)
        Business.objects.filter(pk=self.dental.pk).update(business_type="other")
        self.assertEqual(self.dental.business_type, "dentistry")
        self.assertFalse(is_module_enabled(self.dental, "medical_records"))

    def test_enable_after_negative_cache_is_observed(self):
        ensure_business_capabilities(self.dental)
        self.assertFalse(is_module_enabled(self.dental, "medical_records"))
        self.enable(self.dental)
        self.assertTrue(is_module_enabled(self.dental, "medical_records"))

    def test_existing_crm_defaults_and_saved_choices_are_preserved(self):
        BusinessCapability.objects.create(
            business=self.other, module_key="ai", is_enabled=False
        )
        payload = capability_payload(self.other)
        self.assertEqual(set(payload["modules"]), set(MODULE_REGISTRY))
        self.assertFalse(payload["modules"]["ai"])
        self.assertTrue(payload["modules"]["clients"])
        self.assertTrue(resource_is_enabled(self.other, "payments"))
        self.assertFalse(self.other.capabilities.filter(module_key="medical_records").exists())
