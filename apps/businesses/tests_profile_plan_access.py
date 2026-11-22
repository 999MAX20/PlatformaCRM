from django.contrib.auth import get_user_model
from django.test import TestCase

from apps.businesses.models import Business
from apps.businesses.profiles import create_profiled_business
from apps.clients.models import Client
from apps.core.domain_errors import ModuleDisabled
from apps.payments.plan_balances import assert_plan_money, plan_money_projection
from apps.payments.models import PlanAllocation, PlanTerms
from apps.payments.plan_services import allocate_completed, require_current_terms
from apps.scheduling.models import VisitPlan
from apps.scheduling.plan_access import assert_plan_context
from apps.scheduling.plan_selectors import readable_plans, readable_plan_steps
from apps.scheduling.plan_services import create_plan


class ProfilePlanAccessTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.owner = get_user_model().objects.create_user(username="plan-profile", email="plan-profile@example.test")
        cls.core = create_profiled_business(owner=cls.owner, name="Core", slug="plan-core", business_type="other")
        cls.dental = create_profiled_business(owner=cls.owner, name="Dental", slug="plan-dental", business_type="dentistry")
        cls.legacy = Business.objects.create(owner=cls.owner, name="Legacy", slug="plan-legacy")
        for business in (cls.core, cls.dental, cls.legacy):
            Client.objects.create(business=business, full_name="Synthetic client")

    def create(self, business):
        return create_plan(business=business, actor=self.owner,
                           client=Client.objects.get(business=business), steps=[], idempotency_key="profile-plan")[0]

    def test_core_cannot_create_plan(self):
        with self.assertRaises(ModuleDisabled):
            self.create(self.core)
        self.assertFalse(VisitPlan.objects.filter(business=self.core).exists())

    def test_dental_and_legacy_keep_plan_creation(self):
        for business in (self.dental, self.legacy):
            with self.subTest(business=business.pk):
                plan = self.create(business)
                self.assertEqual(plan.business_id, business.pk)
                self.assertTrue(readable_plans(business=business, actor=self.owner).filter(pk=plan.pk).exists())

    def test_core_cannot_read_existing_plan_even_with_owner_role(self):
        plan = VisitPlan.objects.create(business=self.core, client=Client.objects.get(business=self.core), created_by=self.owner, responsible_user=self.owner)
        with self.assertRaises(ModuleDisabled):
            assert_plan_context(plan, self.owner)
        self.assertFalse(readable_plans(business=self.core, actor=self.owner).exists())
        self.assertFalse(readable_plan_steps(business=self.core, actor=self.owner).exists())

    def test_revocation_is_observed_by_loaded_plan_and_selectors(self):
        plan = self.create(self.dental)
        self.dental.capabilities.filter(module_key="visit_plans").update(is_enabled=False)
        with self.assertRaises(ModuleDisabled):
            assert_plan_context(plan, self.owner)
        self.assertFalse(readable_plans(business=self.dental, actor=self.owner).exists())

    def test_disabled_plan_money_does_not_hide_allowed_plan(self):
        plan = self.create(self.dental)
        self.dental.capabilities.filter(module_key="plan_payments").update(is_enabled=False)
        assert_plan_context(plan, self.owner)
        with self.assertRaises(ModuleDisabled):
            assert_plan_money(plan, self.owner)
        self.assertIsNone(plan_money_projection(plan, self.owner))

    def test_automatic_allocation_observes_money_revocation(self):
        plan = self.create(self.dental)
        PlanTerms.objects.create(plan=plan, revision=1, mode="per_visit", currency="KZT",
                                 total=0, lines=[], composition=[], reason="Synthetic terms",
                                 consent=True, actor=self.owner)
        self.dental.capabilities.filter(module_key="plan_payments").update(is_enabled=False)
        with self.assertRaises(ModuleDisabled):
            require_current_terms(plan)
        with self.assertRaises(ModuleDisabled):
            allocate_completed(plan, self.owner)
        self.assertFalse(PlanAllocation.objects.filter(terms__plan=plan).exists())

    def test_completion_without_financial_terms_keeps_no_money_effect(self):
        plan = self.create(self.dental)
        self.dental.capabilities.filter(module_key="plan_payments").update(is_enabled=False)
        allocate_completed(plan, self.owner)
        self.assertFalse(PlanAllocation.objects.filter(terms__plan=plan).exists())
