from unittest.mock import patch

from rest_framework.test import APIClient
from django.test import TestCase

from apps.accounts.models import User
from apps.billing.models import Subscription, SubscriptionPlan
from apps.billing.usage import increment_usage
from apps.businesses.models import Business, BusinessMember


class BillingSettingsScopeTests(TestCase):
    def setUp(self):
        self.api = APIClient()
        self.owner = User.objects.create_user(username="scope-owner", email="scope-owner@example.com")
        self.first = Business.objects.create(owner=self.owner, name="A", slug="scope-a")
        self.second = Business.objects.create(owner=self.owner, name="B", slug="scope-b")
        outsider = User.objects.create_user(username="scope-outsider", email="scope-outsider@example.com")
        self.foreign = Business.objects.create(owner=outsider, name="C", slug="scope-c")
        plan = SubscriptionPlan.objects.get(code="start")
        self.subscriptions = [Subscription.objects.create(business=b, plan=plan) for b in (self.first, self.second, self.foreign)]
        self.api.force_authenticate(self.owner)

    def test_reads_use_selected_business_and_require_unambiguous_selector(self):
        increment_usage(self.second, "ai_requests", amount=7)
        for endpoint in ("current-subscription", "usage-summary", "entitlements"):
            url = f"/api/billing/{endpoint}/"
            with self.subTest(endpoint=endpoint):
                self.assertEqual(self.api.get(url).status_code, 400)
                self.assertEqual(self.api.get(url, {"business": self.foreign.pk}).status_code, 404)
                self.assertEqual(self.api.get(url, {"business": "invalid"}).status_code, 400)
                response = self.api.get(url, {"business": self.second.pk})
                self.assertEqual(response.status_code, 200)
                if endpoint == "current-subscription":
                    self.assertEqual(response.data["business"], self.second.pk)
                else:
                    self.assertEqual(next(row for row in response.data if row["metric"] == "ai_requests")["value"], 7)

    def test_all_mutations_target_selected_business_only(self):
        base = "/api/billing/current-subscription/"
        for endpoint, payload in (("change-plan", {"plan": SubscriptionPlan.objects.get(code="growth").pk}), ("pause", {}), ("resume", {}), ("cancel", {})):
            with self.subTest(endpoint=endpoint):
                self.assertEqual(self.api.post(base + endpoint + "/", payload, format="json").status_code, 400)
                response = self.api.post(base + endpoint + "/", {**payload, "business": self.second.pk}, format="json")
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.data["business"], self.second.pk)
        response = self.api.patch(base + "settings/", {"business": self.second.pk, "billing_email": "second@example.com"}, format="json")
        self.assertEqual(response.status_code, 200)
        for subscription in self.subscriptions:
            subscription.refresh_from_db()
        self.assertEqual(self.subscriptions[0].status, Subscription.Statuses.TRIAL)
        self.assertEqual(self.subscriptions[0].billing_email, "")
        self.assertEqual(self.subscriptions[1].billing_email, "second@example.com")

    def test_selected_business_permission_and_conflicting_selector(self):
        member = User.objects.create_user(username="scope-accountant", email="scope-accountant@example.com")
        BusinessMember.objects.create(business=self.second, user=member, role=BusinessMember.Roles.ACCOUNTANT)
        self.api.force_authenticate(member)
        url = "/api/billing/current-subscription/settings/"
        self.assertEqual(self.api.patch(url, {"business": self.second.pk, "billing_email": "no@example.com"}, format="json").status_code, 403)
        self.api.force_authenticate(self.owner)
        self.assertEqual(self.api.patch(f"{url}?business={self.first.pk}", {"business": self.second.pk}, format="json").status_code, 400)
        self.assertEqual(self.api.patch(url, {"business": self.foreign.pk}, format="json").status_code, 404)

    def test_invalid_settings_and_plan_do_not_mutate_subscription(self):
        base = "/api/billing/current-subscription/"
        for payload in ({"billing_email": "invalid"}, {"invoice_details_json": []}, {"payment_method": "x" * 65}):
            self.assertEqual(self.api.patch(base + "settings/", {"business": self.second.pk, **payload}, format="json").status_code, 400)
        self.assertEqual(self.api.post(base + "change-plan/", {"business": self.second.pk, "plan": "invalid"}, format="json").status_code, 400)
        self.subscriptions[1].refresh_from_db()
        self.assertEqual(self.subscriptions[1].billing_email, "")
        self.assertIsNone(self.subscriptions[1].requested_plan_id)

    def test_audit_failure_rolls_back_billing_metadata(self):
        with patch("apps.billing.services.write_audit_log", side_effect=RuntimeError("audit unavailable")):
            response = self.api.patch("/api/billing/current-subscription/settings/", {"business": self.second.pk, "billing_email": "changed@example.com"}, format="json")
        self.assertEqual(response.status_code, 500)
        self.subscriptions[1].refresh_from_db()
        self.assertEqual(self.subscriptions[1].billing_email, "")

    def test_usage_distinguishes_current_inventory_from_monthly_counters(self):
        BusinessMember.objects.create(business=self.second, user=self.owner, role="owner")
        increment_usage(self.second, "users", amount=99)
        usage = self.api.get("/api/billing/usage-summary/", {"business": self.second.pk})
        rows = {row["metric"]: row for row in usage.data}
        self.assertEqual(rows["users"]["value"], 1)
        self.assertEqual(rows["users"]["period_kind"], "current")
        self.assertIsNone(rows["users"]["period_start"])
        entitlements = self.api.get("/api/billing/entitlements/", {"business": self.second.pk})
        rows = {row["metric"]: row for row in entitlements.data}
        self.assertEqual(rows["ai_requests"]["period_kind"], "month")
        self.assertLess(rows["ai_requests"]["period_start"], rows["ai_requests"]["period_end"])
        self.assertEqual(rows["storage_mb"]["unit"], "MiB")
