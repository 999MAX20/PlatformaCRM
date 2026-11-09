from decimal import Decimal

from django.test import TestCase
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.businesses.models import Business, BusinessMember, BusinessRole, RolePermission
from apps.core.models import AuditLog
from apps.pricing.models import KaspiCompetitorOffer, KaspiPricingRule
from apps.pricing.serializers import KaspiCompetitorOfferSerializer
from apps.pricing.services import create_kaspi_recommendation


class PricingBusinessValidationTests(TestCase):
    def setUp(self):
        self.api = APIClient()
        self.owner = User.objects.create_user(username="pricing-boundary-owner", email="pricing-boundary-owner@example.invalid")
        self.other_owner = User.objects.create_user(username="pricing-boundary-other", email="pricing-boundary-other@example.invalid")
        self.business = Business.objects.create(owner=self.owner, name="Pricing A", slug="pricing-boundary-a")
        self.other_business = Business.objects.create(owner=self.other_owner, name="Pricing B", slug="pricing-boundary-b")
        self.rule = self.make_rule(self.business, "A")
        self.second_rule = self.make_rule(self.business, "A2")
        self.other_rule = self.make_rule(self.other_business, "B")
        self.offer = KaspiCompetitorOffer.objects.create(
            business=self.business, rule=self.rule, competitor_name="Synthetic competitor", price=Decimal("90"),
        )
        self.url = f"/api/pricing/kaspi/competitor-offers/{self.offer.pk}/"
        self.api.force_authenticate(self.owner)

    def make_rule(self, business, sku):
        return KaspiPricingRule.objects.create(
            business=business, product_sku=sku, current_price=Decimal("100"), min_price=Decimal("10"),
        )

    def assert_offer_unchanged(self):
        self.offer.refresh_from_db()
        self.assertEqual((self.offer.business_id, self.offer.rule_id, self.offer.price),
                         (self.business.pk, self.rule.pk, Decimal("90")))

    def test_patch_omitting_business_cannot_link_foreign_rule(self):
        response = self.api.patch(self.url, {"rule": self.other_rule.pk}, format="json")
        self.offer.refresh_from_db()
        self.assertEqual((response.status_code, self.offer.business_id, self.offer.rule_id),
                         (400, self.business.pk, self.rule.pk))

    def test_string_form_and_explicit_business_do_not_bypass_validation(self):
        for format, payload in (
            ("multipart", {"rule": str(self.other_rule.pk)}),
            ("json", {"rule": str(self.other_rule.pk), "business": self.business.pk}),
        ):
            with self.subTest(format=format):
                self.assertEqual(self.api.patch(self.url, payload, format=format).status_code, 400)
                self.assert_offer_unchanged()

    def test_owner_of_both_businesses_still_cannot_cross_link(self):
        self.other_business.owner = self.owner
        self.other_business.save(update_fields=["owner"])
        response = self.api.patch(self.url, {"rule": self.other_rule.pk}, format="json")
        self.assertEqual(response.status_code, 400)
        self.assert_offer_unchanged()

    def test_common_serializer_enforces_effective_saved_business(self):
        serializer = KaspiCompetitorOfferSerializer(self.offer, data={"rule": self.other_rule.pk}, partial=True)
        self.assertFalse(serializer.is_valid())

    def test_unchanged_link_and_same_business_relink_remain_allowed_and_audited(self):
        before = AuditLog.objects.filter(business=self.business, action=AuditLog.Actions.UPDATE).count()
        self.assertEqual(self.api.patch(self.url, {"price": "91.00"}, format="json").status_code, 200)
        self.offer.refresh_from_db()
        self.assertEqual(self.offer.rule_id, self.rule.pk)
        self.assertEqual(self.offer.price, Decimal("91"))
        self.assertEqual(self.api.patch(self.url, {"rule": self.second_rule.pk}, format="json").status_code, 200)
        self.offer.refresh_from_db()
        self.assertEqual((self.offer.business_id, self.offer.rule_id), (self.business.pk, self.second_rule.pk))
        self.assertEqual(AuditLog.objects.filter(business=self.business, action=AuditLog.Actions.UPDATE).count(), before + 2)

    def test_full_update_and_create_keep_same_business_controls(self):
        payload = {"business": self.business.pk, "rule": self.rule.pk, "competitor_name": "Updated", "price": "92.00"}
        self.assertEqual(self.api.put(self.url, payload, format="json").status_code, 200)
        self.assertEqual(self.api.put(self.url, {**payload, "rule": self.other_rule.pk}, format="json").status_code, 400)
        for include_business in (False, True):
            create = {"rule": self.rule.pk, "competitor_name": "Created", "price": "93.00"}
            if include_business:
                create["business"] = self.business.pk
            self.assertEqual(self.api.post("/api/pricing/kaspi/competitor-offers/", create, format="json").status_code, 201)
        self.assertEqual(self.api.post("/api/pricing/kaspi/competitor-offers/", {
            **payload, "rule": self.other_rule.pk,
        }, format="json").status_code, 400)

    def test_business_reparent_is_still_denied(self):
        self.other_business.owner = self.owner
        self.other_business.save(update_fields=["owner"])
        response = self.api.patch(self.url, {"business": self.other_business.pk, "rule": self.other_rule.pk}, format="json")
        self.assertEqual(response.status_code, 400)
        self.assert_offer_unchanged()

    def test_existing_inconsistent_link_cannot_be_silently_preserved(self):
        KaspiCompetitorOffer.objects.filter(pk=self.offer.pk).update(rule=self.other_rule)
        response = self.api.patch(self.url, {"price": "91.00"}, format="json")
        self.assertEqual(response.status_code, 400)
        self.offer.refresh_from_db()
        self.assertEqual(self.offer.price, Decimal("90"))

    def test_existing_inconsistent_link_can_be_explicitly_repaired(self):
        KaspiCompetitorOffer.objects.filter(pk=self.offer.pk).update(rule=self.other_rule)
        response = self.api.patch(self.url, {"rule": self.rule.pk}, format="json")
        self.assertEqual(response.status_code, 200)
        self.assert_offer_unchanged()

    def test_recommendation_ignores_legacy_foreign_business_offer(self):
        KaspiCompetitorOffer.objects.create(
            business=self.business, rule=self.other_rule, competitor_name="Inconsistent legacy row", price=Decimal("1"),
        )
        KaspiCompetitorOffer.objects.create(
            business=self.other_business, rule=self.other_rule, competitor_name="Valid B row", price=Decimal("90"),
        )
        recommendation = create_kaspi_recommendation(self.other_rule)
        self.assertEqual((recommendation.business_id, recommendation.competitor_price, recommendation.target_price),
                         (self.other_business.pk, Decimal("90"), Decimal("89")))

    def test_autopilot_requires_same_business_competitor_observation(self):
        KaspiCompetitorOffer.objects.create(
            business=self.business, rule=self.other_rule, competitor_name="Inconsistent legacy row", price=Decimal("90"),
        )
        self.api.force_authenticate(self.other_owner)
        url = f"/api/pricing/kaspi/rules/{self.other_rule.pk}/enable-autopilot/"
        confirmations = {key: True for key in ("confirm_min_price", "confirm_daily_limit", "confirm_monitoring", "confirm_writeback_risk")}
        denied = self.api.post(url, confirmations, format="json")
        self.other_rule.refresh_from_db()
        self.assertEqual((denied.status_code, self.other_rule.mode), (400, KaspiPricingRule.Modes.RECOMMEND))
        KaspiCompetitorOffer.objects.create(
            business=self.other_business, rule=self.other_rule, competitor_name="Valid B row", price=Decimal("90"),
        )
        self.assertEqual(self.api.post(url, confirmations, format="json").status_code, 200)

    def test_foreign_object_and_read_only_role_remain_denied(self):
        other_offer = KaspiCompetitorOffer.objects.create(
            business=self.other_business, rule=self.other_rule, competitor_name="Other", price=Decimal("90"),
        )
        self.assertEqual(self.api.patch(f"/api/pricing/kaspi/competitor-offers/{other_offer.pk}/", {"price": "1"}, format="json").status_code, 404)
        viewer = User.objects.create_user(username="pricing-viewer", email="pricing-viewer@example.invalid")
        role = BusinessRole.objects.create(business=self.business, name="Read pricing")
        RolePermission.objects.create(business_role=role, resource="integrations", action="view", scope="business")
        RolePermission.objects.create(business_role=role, resource="integrations", action="update", scope="none", is_allowed=False)
        BusinessMember.objects.create(business=self.business, user=viewer, role="operator", business_role=role)
        self.api.force_authenticate(viewer)
        self.assertEqual(self.api.get(self.url).status_code, 200)
        self.assertEqual(self.api.patch(self.url, {"price": "1"}, format="json").status_code, 403)

    def test_null_rule_and_business_are_not_effective_value_bypasses(self):
        for payload in ({"rule": None}, {"business": None, "rule": self.other_rule.pk}):
            with self.subTest(payload_type=list(payload)):
                self.assertEqual(self.api.patch(self.url, payload, format="json").status_code, 400)
                self.assert_offer_unchanged()
