from datetime import timedelta
from types import SimpleNamespace
from unittest.mock import patch

from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.activities.models import ActivityEvent
from apps.activities.taxonomy import ActivityEvents
from apps.businesses.models import Business, BusinessMember
from apps.clients.models import Client
from apps.scheduling.models import Appointment
from apps.scheduling.services import _appointment_follow_up_task_spec
from apps.services.models import Service
from apps.tasks.models import Task


class LocalizedTaskSearchTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(username="search-owner", email="search-owner@example.test")
        self.business = Business.objects.create(owner=self.owner, name="Search", slug="search")
        self.api = APIClient()
        self.api.force_authenticate(self.owner)
        self.client_record = Client.objects.create(business=self.business, full_name="Client")
        self.service = Service.objects.create(business=self.business, name="Service")

    def generated(self, status="cancelled", provenance=True):
        now = timezone.now()
        appointment = Appointment.objects.create(business=self.business, client=self.client_record,
            service=self.service, start_at=now, end_at=now+timedelta(hours=1), status=status)
        spec = _appointment_follow_up_task_spec(SimpleNamespace(id=appointment.pk, status=status))
        task = Task.objects.create(business=self.business, appointment=appointment,
            assignee=self.owner, title=spec["title"], description=spec["description"])
        if provenance:
            ActivityEvent.objects.create(business=self.business, entity_type="Task", entity_id=str(task.pk),
                event_type=ActivityEvents.TASK_CREATED,
                metadata={"appointment_id": appointment.pk, "appointment_status": status})
        return task

    def search(self, search, locale="ru", **extra):
        return self.api.get("/api/tasks/", {"business": self.business.pk, "search": search, "locale": locale, **extra})

    @patch("rest_framework.pagination.PageNumberPagination.page_size", 1)
    def test_displayed_titles_search_before_pagination_and_summary(self):
        tasks = [self.generated(status) for status in ("cancelled", "no_show", "completed")]
        for locale, term in [("ru", "Связаться"), ("ru", "связаться"), ("kk", "хабарласу"), ("en", "Follow up")]:
            response = self.search(term, locale, page_size=1)
            self.assertEqual(response.status_code, 200, response.data)
            self.assertEqual(response.data["count"], 3)
            self.assertEqual(len(response.data["results"]), 1)
            self.assertIsNotNone(response.data["next"])
            summary = self.api.get("/api/tasks/summary/", {"business": self.business.pk, "search": term, "locale": locale})
            self.assertEqual(summary.status_code, 200, summary.data)
            self.assertEqual(summary.data["active"], 3)
        first = tasks[0]
        exact = self.search(f"Связаться после отмены записи #{first.appointment_id}")
        self.assertEqual([row["id"] for row in exact.data["results"]], [first.pk])
        self.assertEqual(self.search("Связаться", "en").data["count"], 0)
        self.assertEqual(self.search("Follow up", "ru").data["count"], 3)

    def test_custom_edited_missing_and_mismatched_provenance_not_localized(self):
        task = self.generated()
        self.generated(provenance=False)
        edited = self.generated()
        edited.title = "Customer wording"
        edited.save()
        wrong = self.generated()
        ActivityEvent.objects.filter(entity_id=str(wrong.pk)).update(metadata={"appointment_id": 999999, "appointment_status": "cancelled"})
        self.assertEqual([row["id"] for row in self.search("Связаться").data["results"]], [task.pk])
        self.assertEqual(self.search("Customer wording").data["count"], 1)
        self.assertEqual(self.search("").data["count"], 4)
        self.assertEqual(self.search("no such title").data["count"], 0)
        ActivityEvent.objects.filter(entity_id=str(task.pk)).update(metadata={"appointment_id": str(task.appointment_id), "appointment_status": "cancelled"})
        self.assertEqual(self.search("Связаться").data["count"], 0)

    def test_foreign_business_search_remains_denied(self):
        self.generated()
        foreign = User.objects.create_user(username="foreign-search", email="foreign-search@example.test")
        Business.objects.create(owner=foreign, name="Other", slug="foreign-search")
        self.api.force_authenticate(foreign)
        response = self.search("Связаться")
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data["count"], 0)
        self.assertEqual(response.data["results"], [])

    def test_own_scope_is_not_expanded_by_localized_search(self):
        own, other = self.generated(), self.generated()
        operator = User.objects.create_user(username="search-operator", email="search-operator@example.test")
        BusinessMember.objects.create(business=self.business, user=operator, role="operator")
        own.assignee = operator
        own.save()
        self.api.force_authenticate(operator)
        response = self.search("Связаться")
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual([row["id"] for row in response.data["results"]], [own.pk])

    def test_search_templates_match_display_dictionaries(self):
        import re
        from pathlib import Path
        from django.conf import settings
        from apps.tasks.localized_search import FOLLOW_UP_TITLES
        for locale, templates in FOLLOW_UP_TITLES.items():
            source = (Path(settings.BASE_DIR) / f"frontend/src/lib/i18n/{locale}/tasks.ts").read_text(encoding="utf-8")
            for status, title in templates.items():
                match = re.search(r'"taskWorkspace.followUp\.' + status + r'\.title": "([^"]+)"', source)
                self.assertIsNotNone(match)
                self.assertEqual(match.group(1), title)
