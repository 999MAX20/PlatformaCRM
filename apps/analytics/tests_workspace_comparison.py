from datetime import date
from decimal import Decimal
from uuid import uuid4

from django.test import TestCase

from apps.analytics import tests_workspace as fixtures
from apps.analytics.workspace_comparison import previous_period
from apps.businesses.models import BusinessMember, BusinessCapability, BusinessRole, RolePermission
from apps.accounts.models import User
from apps.payments.models import Payment
from apps.scheduling.models import Resource


class WorkspaceComparisonTests(TestCase):
    setUp = fixtures.AnalyticsWorkspaceTests.setUp
    appointment = fixtures.AnalyticsWorkspaceTests.appointment
    report = fixtures.AnalyticsWorkspaceTests.report

    def test_previous_period_calendar_length_leap_and_boundary(self):
        self.assertEqual(previous_period(date(2024, 3, 1), date(2024, 3, 2)), (date(2024, 2, 28), date(2024, 2, 29)))
        self.assertEqual(previous_period(date(2026, 1, 1), date(2026, 1, 1)), (date(2025, 12, 31), date(2025, 12, 31)))
        self.assertIsNone(previous_period(date(2, 1, 1), date(2, 1, 2)))

    def test_period_archive_scope_and_groups_match_standalone_report(self):
        for at, status in (("2026-09-17T00:00:00+05:00", "completed"),
                           ("2026-09-30T23:59:59+05:00", "no_show"),
                           ("2026-09-16T23:59:59+05:00", "cancelled"),
                           ("2026-10-01T00:00:00+05:00", "confirmed")):
            self.appointment(at=at, status=status, responsible_user=self.owner, is_archived=True)
        data = self.report(compare="previous").data
        previous = self.report(start="2026-09-17", end="2026-09-30").data
        comparison = data["comparison"]
        self.assertEqual(data["appointments"]["total"], 1)
        for key in ("appointments", "services", "record_sources"):
            self.assertEqual(comparison[key], previous[key])
        self.assertEqual(comparison["appointments"]["total"], 2)
        self.assertEqual(comparison["team"][0]["appointments"], 2)
        self.assertNotIn("current", comparison)
        self.assertNotIn("comparison", previous)

    def test_zero_and_missing_remain_distinct_and_invalid_mode_rejected(self):
        data = self.report(compare="previous").data["comparison"]
        self.assertEqual(data["appointments"]["total"], 0)
        self.assertIsNone(data["appointments"]["completion_rate"])
        self.assertIsNone(data["financial_changes"]["receipts"])
        BusinessCapability.objects.update_or_create(business=self.business, module_key="appointments", defaults={"is_enabled": False})
        self.assertIsNone(self.report(compare="previous").data["comparison"]["appointments"]["total"])
        self.assertEqual(self.report(compare="arbitrary").status_code, 400)

    def test_own_scope_and_tenant_are_preserved_in_previous_period(self):
        manager = User.objects.create_user(username="compare-manager", email="compare-manager@example.test")
        role = BusinessRole.objects.create(business=self.business, name="Own comparison")
        for resource in ("analytics", "appointments"):
            RolePermission.objects.create(business_role=role, resource=resource, action="view", scope="own")
        BusinessMember.objects.create(business=self.business, user=manager, role="manager", business_role=role)
        resource = Resource.objects.create(business=self.business, name="Own specialist", linked_user=manager)
        self.appointment(at="2026-09-25T10:00:00+05:00", responsible_user=manager, resource=resource)
        self.appointment(at="2026-09-25T12:00:00+05:00", responsible_user=self.owner)
        self.api.force_authenticate(manager)
        data = self.report(compare="previous").data["comparison"]
        self.assertEqual(data["appointments"]["total"], 1)
        self.assertEqual([row["id"] for row in data["team"]], [manager.pk])
        self.assertEqual(data["financial"]["reason"], "permission_denied")
        self.assertEqual(self.report(compare="previous", business=self.other_business.pk).status_code, 400)

    def test_manual_financial_delta_is_decimal_and_zero_is_valid(self):
        self.business.financial_source_mode = "manual"
        self.business.save(update_fields=["financial_source_mode"])
        from datetime import datetime
        for at, amount in (("2026-09-25T10:00:00+05:00", "0.10"), ("2026-10-05T10:00:00+05:00", "0.30")):
            Payment.objects.create(business=self.business, client=self.client, kind="receipt", amount=Decimal(amount),
                currency=self.business.currency, occurred_at=datetime.fromisoformat(at), method="cash",
                submission_id=uuid4(), request_hash="comparison-fixture", created_by=self.owner)
        data = self.report(compare="previous").data["comparison"]
        self.assertEqual(Decimal(data["financial_changes"]["receipts"]), Decimal("0.20"))
        self.assertEqual(Decimal(data["financial_changes"]["refunds"]), Decimal("0.00"))

    def test_unverified_or_incompatible_money_is_not_compared(self):
        from unittest.mock import patch
        self.business.financial_source_mode = "manual"
        self.business.save(update_fields=["financial_source_mode"])
        original = self.report(compare="previous").data["comparison"]["financial"]
        for override in ({"state": "stale"}, {"currency": "USD"},
                         {"source": {"provider": "other", "name": "Other source"}}):
            with self.subTest(override=override), patch(
                "apps.analytics.workspace_comparison.financial_report", return_value={**original, **override}
            ):
                changes = self.report(compare="previous").data["comparison"]["financial_changes"]
                self.assertTrue(all(value is None for value in changes.values()))
