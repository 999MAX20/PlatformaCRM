from datetime import time

from django.db import IntegrityError, connection, transaction
from django.db.migrations.executor import MigrationExecutor
from django.test import TestCase, TransactionTestCase
from rest_framework.exceptions import ValidationError
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.businesses.models import Business
from apps.scheduling.models import Resource, WorkingHours
from apps.scheduling.serializers import WorkingHoursSerializer


class WorkingHoursIntegrityTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(username="hours-owner", email="hours-owner@example.test", role="business_owner")
        self.business = Business.objects.create(owner=self.owner, name="Hours", slug="hours")
        self.values = dict(business=self.business, weekday=0, start_time=time(9), end_time=time(18))

    def test_database_rejects_duplicate_general_day(self):
        original = WorkingHours.objects.create(**self.values)
        with self.assertRaises(IntegrityError), transaction.atomic():
            WorkingHours.objects.create(**self.values)
        self.assertEqual(list(WorkingHours.objects.values_list("pk", flat=True)), [original.pk])

    def test_other_business_days_and_resource_remain_independent(self):
        other = Business.objects.create(owner=self.owner, name="Other", slug="other")
        resource = Resource.objects.create(business=self.business, name="Specialist")
        WorkingHours.objects.create(**self.values)
        WorkingHours.objects.create(**{**self.values, "business": other})
        WorkingHours.objects.create(**{**self.values, "weekday": 1})
        WorkingHours.objects.create(**self.values, resource=resource)
        with self.assertRaises(IntegrityError), transaction.atomic():
            WorkingHours.objects.create(**self.values, resource=resource)
        self.assertEqual(WorkingHours.objects.count(), 4)

    def test_stale_create_validation_returns_validation_error(self):
        payload = {**self.values, "business": self.business.pk}
        first = WorkingHoursSerializer(data=payload)
        second = WorkingHoursSerializer(data=payload)
        first.is_valid(raise_exception=True)
        second.is_valid(raise_exception=True)
        first.save()
        with self.assertRaises(ValidationError):
            second.save()
        self.assertEqual(WorkingHours.objects.count(), 1)

    def test_stale_update_rolls_back(self):
        row = WorkingHours.objects.create(**{**self.values, "weekday": 1})
        serializer = WorkingHoursSerializer(row, data={"weekday": 0}, partial=True)
        serializer.is_valid(raise_exception=True)
        WorkingHours.objects.create(**self.values)
        with self.assertRaises(ValidationError):
            serializer.save()
        row.refresh_from_db()
        self.assertEqual(row.weekday, 1)

    def test_api_rejects_duplicate_and_foreign_business(self):
        api = APIClient()
        api.force_authenticate(self.owner)
        payload = {"business": self.business.pk, "weekday": 0, "start_time": "09:00", "end_time": "18:00"}
        self.assertEqual(api.post("/api/working-hours/", payload).status_code, 201)
        self.assertEqual(api.post("/api/working-hours/", payload).status_code, 400)
        stranger = User.objects.create_user(username="hours-stranger", email="hours-stranger@example.test", role="business_owner")
        api.force_authenticate(stranger)
        self.assertIn(api.post("/api/working-hours/", {**payload, "weekday": 1}).status_code, (400, 403, 404))
        self.assertEqual(WorkingHours.objects.count(), 1)


class WorkingHoursMigrationTests(TransactionTestCase):
    def test_forward_preserves_rows_reverse_and_duplicate_failure_are_safe(self):
        previous = ("scheduling", "0011_visit_plans")
        current = ("scheduling", "0012_unique_business_working_hours")
        executor = MigrationExecutor(connection)
        leaves = executor.loader.graph.leaf_nodes()
        executor.migrate([previous])
        try:
            executor = MigrationExecutor(connection)
            state = executor.loader.project_state(list(executor.loader.applied_migrations)).apps
            owner = state.get_model("accounts", "User").objects.create(username="hours-migration")
            business = state.get_model("businesses", "Business").objects.create(owner=owner, name="Hours", slug="hours-migration")
            Hours = state.get_model("scheduling", "WorkingHours")
            values = dict(business_id=business.pk, weekday=0, start_time=time(9), end_time=time(18))
            original = Hours.objects.create(**values)
            duplicate = Hours.objects.create(**values)
            with self.assertRaises(IntegrityError):
                MigrationExecutor(connection).migrate([current])
            self.assertEqual(Hours.objects.count(), 2)
            duplicate.delete()
            MigrationExecutor(connection).migrate([current])
            self.assertEqual(Hours.objects.get().pk, original.pk)
            with self.assertRaises(IntegrityError), transaction.atomic():
                Hours.objects.create(**values)
            MigrationExecutor(connection).migrate([previous])
            self.assertEqual(Hours.objects.get().pk, original.pk)
        finally:
            MigrationExecutor(connection).migrate(leaves)
