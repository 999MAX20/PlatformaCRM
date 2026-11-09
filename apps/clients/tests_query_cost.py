from django.db import connection
from django.test import TestCase
from django.test.utils import CaptureQueriesContext
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.activities.models import Tag, TaggedObject
from apps.businesses.models import Business
from apps.clients.models import Client
from apps.clients.selectors import annotate_client_list_queryset, build_client_facets, build_client_summary
from apps.clients.views import ClientPaginator
from apps.tasks.models import Task


class ClientCountQueryTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(username="count-owner", email="count-owner@example.test")
        self.business = Business.objects.create(owner=self.owner, name="Counts", slug="counts")
        self.plain = Client.objects.create(business=self.business, full_name="Plain", source="manual")
        self.vip = Client.objects.create(business=self.business, full_name="VIP only", source="website")
        self.active = Client.objects.create(business=self.business, full_name="Active", source="website")
        tag = Tag.objects.create(business=self.business, name="VIP")
        TaggedObject.objects.create(business=self.business, tag=tag, entity_type="client", entity_id=str(self.vip.pk))
        Task.objects.create(business=self.business, client=self.active, title="Call", assignee=self.owner, created_by=self.owner)
        other = User.objects.create_user(username="count-other", email="count-other@example.test")
        foreign = Business.objects.create(owner=other, name="Foreign", slug="count-foreign")
        Client.objects.create(business=foreign, full_name="Foreign", source="website")

    def queryset(self):
        return annotate_client_list_queryset(Client.objects.filter(business=self.business)).distinct()

    def test_count_does_not_evaluate_display_annotations(self):
        queryset = self.queryset().order_by("manager_name", "pk")
        with CaptureQueriesContext(connection) as queries:
            self.assertEqual(ClientPaginator(queryset, 1).count, 3)
        self.assertEqual(len(queries), 1)
        self.assertNotIn('"next_step_title"', queries[0]["sql"])
        self.assertNotIn('"manager_name"', queries[0]["sql"])
        self.assertNotIn('"tasks_task"', queries[0]["sql"])

    def test_summary_and_facets_keep_distinct_activity_meanings(self):
        queryset = self.queryset()
        self.assertEqual(build_client_summary(queryset, user=self.owner), {
            "total": 3, "active": 2, "no_reply": 0, "repeat": 0, "new": 1, "vip": 1, "mine": 1,
        })
        with CaptureQueriesContext(connection) as queries:
            facets = build_client_facets(queryset)
        self.assertEqual(len(queries), 2)
        self.assertEqual(facets, {"source": {"manual": 1, "website": 2},
                                 "activity": {"active": 1, "vip": 1, "no_reply": 0, "repeat": 0}})
        for query in queries:
            self.assertNotIn('"next_step_title"', query["sql"])

    def test_api_pagination_and_empty_search_preserve_counts_and_rows(self):
        api = APIClient()
        api.force_authenticate(self.owner)
        first = api.get("/api/clients/", {"source": "website", "page_size": 1, "ordering": "manager_name"})
        second = api.get("/api/clients/", {"source": "website", "page_size": 1, "ordering": "manager_name", "page": 2})
        self.assertEqual(first.status_code, 200)
        self.assertEqual(second.status_code, 200)
        self.assertEqual(first.data["count"], 2)
        self.assertEqual(first.data["summary"]["total"], 2)
        self.assertEqual(first.data["summary"], second.data["summary"])
        self.assertEqual(first.data["facets"], second.data["facets"])
        self.assertEqual({first.data["results"][0]["id"], second.data["results"][0]["id"]}, {self.vip.pk, self.active.pk})
        self.assertIn("next_step_title", first.data["results"][0])
        empty = api.get("/api/clients/", {"q": "no matching client"})
        self.assertEqual(empty.status_code, 200)
        self.assertEqual(empty.data["count"], 0)
        self.assertTrue(all(value == 0 for value in empty.data["summary"].values()))
        self.assertEqual(empty.data["facets"]["source"], {})
